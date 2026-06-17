/** Orchestration for the refund-evaluation review flow. The SDK handler in
 *  `functions/post_refund_evaluation.ts` is thin wiring around these:
 *    - `runPostRefundEvaluation` posts the initial review card
 *    - `handleApproveButton` opens the amount/type modal
 *    - `handleDenyButton` finalizes a deny without touching the Lambda
 *    - `handleApproveModalSubmit` validates inputs, previews-or-POSTs to the
 *      Lambda, and updates the card. */

import type { SlackAPIClient } from "deno-slack-api/types.ts";
import { REFUND_DRY_RUN, REFUND_TEST_CHANNEL, resolveRefundChannel } from "../../config/refunds.ts";
import type { PreparedRequest } from "../../shared/http/prepared_request.ts";
import { postDryRunPreviews, requestStep } from "../../shared/slack/dry_run.ts";
import { type ApproveModalMeta, buildApproveModal } from "./approve_modal.ts";
import { buildRefundEvalBlocks, type RefundDecision } from "./eval_blocks.ts";
import {
    buildCancelOrderRequest,
    buildCreateRefundRequest,
    executeLambdaRequest,
    type RefundType,
} from "./lambda_requests.ts";
import type { RefundEvaluationPayload } from "./types.ts";

// ────────────────────────────────────────────────────────────────────────────
// Payload helpers
// ────────────────────────────────────────────────────────────────────────────

export function parsePayload(raw: unknown): RefundEvaluationPayload | null {
    try {
        return typeof raw === "string" ? JSON.parse(raw) : (raw as RefundEvaluationPayload);
    } catch {
        return null;
    }
}

/** Pick the estimate that matches the canonical `refund_to`. */
function pickEstimate(p: RefundEvaluationPayload): { amount: number; refundType: string } {
    const est = p.refund_to === "store_credit"
        ? p.estimated_store_credit
        : p.estimated_refund_to_original;
    return { amount: est?.amount ?? 0, refundType: p.refund_to };
}

// ────────────────────────────────────────────────────────────────────────────
// Phase 1: Initial review-card post
// ────────────────────────────────────────────────────────────────────────────

/** Post the initial refund review card. Routes via the test/review channel
 *  resolver — channel routing lives in Slack, not in the Lambda payload. */
export async function runPostRefundEvaluation(
    inputs: { evaluation_json: string },
    client: SlackAPIClient,
): Promise<{ completed: false } | { error: string }> {
    const payload = parsePayload(inputs.evaluation_json);
    if (!payload) {
        return {
            error: `Invalid evaluation_json: could not parse JSON. Received (${typeof inputs
                .evaluation_json}): ${String(inputs.evaluation_json).slice(0, 500)}`,
        };
    }

    const channel = resolveRefundChannel({ is_test: payload.is_test });

    const result = await client.chat.postMessage({
        channel,
        text:
            `Refund request from ${payload.first_name} ${payload.last_name} (${payload.order_number})`,
        blocks: buildRefundEvalBlocks(payload),
    });

    if (!result.ok) return { error: `chat.postMessage failed: ${result.error}` };

    // Stay open so we can handle the Approve/Deny buttons; the function completes
    // from the button / modal-submission handlers below.
    return { completed: false };
}

// ────────────────────────────────────────────────────────────────────────────
// Phase 2: Approve button → open editable modal
// ────────────────────────────────────────────────────────────────────────────

export async function handleApproveButton(
    payload: RefundEvaluationPayload,
    args: {
        channel: string;
        messageTs: string;
        interactivityPointer: string;
    },
    client: SlackAPIClient,
): Promise<void> {
    const est = pickEstimate(payload);
    const meta: ApproveModalMeta = { channel: args.channel, message_ts: args.messageTs };

    await client.views.open({
        interactivity_pointer: args.interactivityPointer,
        view: buildApproveModal({
            orderNumber: payload.order_number,
            estimatedAmount: est.amount,
            refundType: est.refundType,
            refundable: payload.refundable_balance,
            meta,
        }),
    });
}

// ────────────────────────────────────────────────────────────────────────────
// Phase 3: Deny button → update card, complete function (no Lambda call)
// ────────────────────────────────────────────────────────────────────────────

export async function handleDenyButton(
    payload: RefundEvaluationPayload,
    args: {
        userId: string;
        channel: string;
        messageTs: string;
        executionId: string;
    },
    client: SlackAPIClient,
): Promise<void> {
    const decision: RefundDecision = { status: "denied", by: args.userId };
    await client.chat.update({
        channel: args.channel,
        ts: args.messageTs,
        text: `Refund request marked do-not-send (${payload.order_number})`,
        blocks: buildRefundEvalBlocks(payload, decision),
    });

    await client.functions.completeSuccess({
        function_execution_id: args.executionId,
        outputs: { message_ts: args.messageTs, channel_id: args.channel },
    });
}

// ────────────────────────────────────────────────────────────────────────────
// Phase 4: Modal submit → validate, dry-run-or-POST, finalize card
// ────────────────────────────────────────────────────────────────────────────

/** Errors response for the modal submission handler when input validation fails. */
type ModalSubmitErrors = {
    response_action: "errors";
    errors: Record<string, string>;
};

/** Validate the modal's amount + type. Returns the parsed values or a structured
 *  Slack-format error response (for the SDK handler to return as-is). Pure leaf:
 *  no I/O, no SDK calls — every input failure produces a structured Slack reply. */
function validateModalInputs(
    rawAmount: string,
    rawType: string | undefined,
    payload: RefundEvaluationPayload,
    amountBlockId: string,
): { amount: number; refundType: RefundType } | ModalSubmitErrors {
    const amount = Number.parseFloat(rawAmount);
    if (!Number.isFinite(amount) || amount < 0) {
        return {
            response_action: "errors",
            errors: { [amountBlockId]: "Enter a valid non-negative dollar amount" },
        };
    }
    if (!payload.order_id) {
        return {
            response_action: "errors",
            errors: { [amountBlockId]: "Evaluation is missing the order id — cannot process" },
        };
    }
    const refundType: RefundType = rawType === "store_credit" ? "store_credit" : "original_method";
    return { amount, refundType };
}

/** Build the two-step (cancel + refund) Lambda request batch for an approval.
 *  Pure leaf: payload + approver context in, request batch out. */
function buildApprovalRequests(
    payload: RefundEvaluationPayload,
    approvedBy: string,
    amount: number,
    refundType: RefundType,
): PreparedRequest[] {
    const orderRef = {
        orderId: payload.order_id as string,
        orderNumber: payload.order_number,
        approvedBy,
        isTest: payload.is_test === true,
    };
    return [
        buildCancelOrderRequest(orderRef),
        buildCreateRefundRequest(orderRef, {
            refundType,
            amount,
            transactions: payload.transactions,
        }),
    ];
}

export async function handleApproveModalSubmit(
    payload: RefundEvaluationPayload,
    args: {
        userId: string;
        executionId: string;
        meta: ApproveModalMeta;
        rawAmount: string;
        rawType: string | undefined;
        amountBlockId: string;
    },
    client: SlackAPIClient,
): Promise<ModalSubmitErrors | void> {
    const validated = validateModalInputs(
        args.rawAmount,
        args.rawType,
        payload,
        args.amountBlockId,
    );
    if ("response_action" in validated) return validated;

    const { amount, refundType } = validated;
    const requests = buildApprovalRequests(payload, args.userId, amount, refundType);

    if (REFUND_DRY_RUN) {
        await postDryRunPreviews(
            client,
            REFUND_TEST_CHANNEL,
            requests.map((r) => ({
                header: `:test_tube: *DRY RUN* — would POST to ShopifyRefundHandler: *${r.label}*`,
                label: `${payload.order_number} (${payload.first_name} ${payload.last_name})`,
                steps: [requestStep(r)],
            })),
        );
    } else {
        // Concurrent dispatch with per-request failure log — one failed request
        // doesn't strand the others in the batch.
        const results = await Promise.all(
            requests.map(async (r) => ({ req: r, res: await executeLambdaRequest(r) })),
        );
        results
            .filter(({ res }) => !res.ok)
            .forEach(({ req, res }) =>
                console.error(`[refund] ${req.label} failed: ${res.status} ${res.body}`)
            );
    }

    const decision: RefundDecision = {
        status: "approved",
        by: args.userId,
        amount,
        refundType,
        dryRun: REFUND_DRY_RUN,
    };
    await client.chat.update({
        channel: args.meta.channel,
        ts: args.meta.message_ts,
        text: `Refund approved (${payload.order_number})`,
        blocks: buildRefundEvalBlocks(payload, decision),
    });

    await client.functions.completeSuccess({
        function_execution_id: args.executionId,
        outputs: { message_ts: args.meta.message_ts, channel_id: args.meta.channel },
    });
}
