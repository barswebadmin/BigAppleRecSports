/** Orchestration for the refund-evaluation review flow. The SDK handler in
 *  `functions/post_refund_evaluation.ts` is thin wiring around these:
 *    - `runPostRefundEvaluation` posts the initial review card
 *    - `handleApproveButton` opens the approval modal
 *    - `handleDenyButton` finalizes a deny without touching the Lambda
 *    - `handleApproveModalBlockAction` re-renders the modal on action/amount change
 *    - `handleApproveModalSubmit` validates inputs, previews-or-POSTs to the
 *      Lambda, and updates the card. */

import type { SlackAPIClient } from "deno-slack-api/types.ts";
import { ENV, isRefundPrivilegedSlackUser, readEnv } from "../../config/store.ts";
import { getStaticChannels } from "../../config/workflows.ts";
import type { PreparedRequest } from "../../shared/http/prepared_request.ts";
import { resolveChannel } from "../../shared/slack/channel.ts";
import { postDryRunPreviews, requestStep } from "../../shared/slack/dry_run.ts";
import {
    ACTION_ACTION_ID,
    ACTION_BLOCK_ID,
    AMOUNT_ACTION_ID,
    AMOUNT_BLOCK_ID,
    type ApproveAction,
    type ApproveModalMeta,
    buildApproveModal,
    extractApproveModalValues,
    NOTIFY_ACTION_ID,
    NOTIFY_BLOCK_ID,
    RESTOCK_ACTION_ID,
    RESTOCK_BLOCK_ID,
    type RestockAction,
} from "../../views/refund/approve_modal.ts";
import { buildRefundEvalBlocks } from "../../views/refund/eval_blocks.ts";
import type { RefundDecision } from "./types.ts";
import {
    buildCancelOrderRequest,
    buildCreateRefundRequest,
    executeActionRequest,
} from "./action_requests.ts";
import type { RefundEvaluationPayload, RefundType } from "./types.ts";

/** Refund-specific safety gate: in non-prod, the approval modal previews the
 *  exact Lambda requests to the test channel instead of firing them. Operator
 *  override: `REFUND_DRY_RUN=true|false`. */
const REFUND_DRY_RUN = (readEnv("REFUND_DRY_RUN") ?? String(ENV !== "prod")) === "true";

const REFUND_CHANNELS = getStaticChannels("refund");

// deno-lint-ignore no-explicit-any
type ViewStateValues = Record<string, Record<string, any>>;

function defaultRefundAmountString(payload: RefundEvaluationPayload): string {
    const est = payload.refund_to === "store_credit"
        ? payload.estimated_store_credit
        : payload.estimated_refund_to_original;
    return (est?.amount ?? 0).toFixed(2);
}

function readModalRebuildState(
    payload: RefundEvaluationPayload,
    values: ViewStateValues,
    userId: string,
    meta: ApproveModalMeta,
): Parameters<typeof buildApproveModal>[0] {
    const action = (values[ACTION_BLOCK_ID]?.[ACTION_ACTION_ID]?.selected_option?.value ??
        "cancel_refund") as ApproveAction;
    const rawAmt = values[AMOUNT_BLOCK_ID]?.[AMOUNT_ACTION_ID]?.value as string | undefined;
    const defaultAmt = defaultRefundAmountString(payload);
    const currentAmount = rawAmt !== undefined && rawAmt !== "" ? rawAmt : defaultAmt;
    const restock = (values[RESTOCK_BLOCK_ID]?.[RESTOCK_ACTION_ID]?.selected_option?.value ??
        "none") as RestockAction;
    const notifyOpts = values[NOTIFY_BLOCK_ID]?.[NOTIFY_ACTION_ID]?.selected_options as
        | { value: string }[]
        | undefined;
    const selectedNotifyValues = notifyOpts === undefined
        ? undefined
        : notifyOpts.map((o) => o.value);

    return {
        orderNumber: payload.order_number,
        refundable: payload.refundable_balance,
        totalPaid: payload.order_total ?? 0,
        estimatedOriginal: payload.estimated_refund_to_original?.amount ?? 0,
        estimatedCredit: payload.estimated_store_credit?.amount ?? 0,
        refundTo: payload.refund_to,
        action,
        currentAmount: action === "cancel_only" ? defaultAmt : currentAmount,
        restock,
        selectedNotifyValues,
        isPrivileged: isRefundPrivilegedSlackUser(userId),
        meta,
    };
}

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

    const channel = resolveChannel(REFUND_CHANNELS, { is_test: payload.is_test });

    const result = await client.chat.postMessage({
        channel,
        text:
            `Refund request from ${payload.first_name} ${payload.last_name} (${payload.order_number})`,
        blocks: buildRefundEvalBlocks(payload),
    });

    if (!result.ok) return { error: `chat.postMessage failed: ${result.error}` };

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
        userId: string;
    },
    client: SlackAPIClient,
): Promise<void> {
    const defaultAmt = defaultRefundAmountString(payload);
    await client.views.open({
        interactivity_pointer: args.interactivityPointer,
        view: buildApproveModal({
            orderNumber: payload.order_number,
            refundable: payload.refundable_balance,
            totalPaid: payload.order_total ?? 0,
            estimatedOriginal: payload.estimated_refund_to_original?.amount ?? 0,
            estimatedCredit: payload.estimated_store_credit?.amount ?? 0,
            refundTo: payload.refund_to,
            action: "cancel_refund",
            currentAmount: defaultAmt,
            restock: "none",
            selectedNotifyValues: undefined,
            isPrivileged: isRefundPrivilegedSlackUser(args.userId),
            meta: { channel: args.channel, message_ts: args.messageTs },
        }),
    });
}

// ────────────────────────────────────────────────────────────────────────────
// Phase 2b: Modal block actions → views.update (amount visibility + submit label)
// ────────────────────────────────────────────────────────────────────────────

export async function handleApproveModalBlockAction(
    payload: RefundEvaluationPayload,
    args: {
        userId: string;
        viewId: string;
        values: ViewStateValues;
        meta: ApproveModalMeta;
    },
    client: SlackAPIClient,
): Promise<void> {
    const viewArgs = readModalRebuildState(payload, args.values, args.userId, args.meta);
    await client.views.update({
        view_id: args.viewId,
        view: buildApproveModal(viewArgs),
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

export async function handleApproveModalSubmit(
    payload: RefundEvaluationPayload,
    args: {
        userId: string;
        executionId: string;
        meta: ApproveModalMeta;
        stateValues: ViewStateValues;
    },
    client: SlackAPIClient,
): Promise<ModalSubmitErrors | void> {
    const modalVals = extractApproveModalValues(args.stateValues);
    const needsCancel = modalVals.action === "cancel_refund" || modalVals.action === "cancel_only";
    const needsRefund = modalVals.action === "cancel_refund" || modalVals.action === "refund_only";
    const totalPaid = payload.order_total ?? 0;

    if (!payload.order_id && (needsCancel || needsRefund)) {
        return {
            response_action: "errors",
            errors: {
                [AMOUNT_BLOCK_ID]: "Evaluation is missing the order id — cannot process",
            },
        };
    }

    if (needsRefund) {
        const amount = modalVals.amount;
        if (amount === null || !Number.isFinite(amount) || amount < 0) {
            return {
                response_action: "errors",
                errors: { [AMOUNT_BLOCK_ID]: "Enter a valid non-negative dollar amount" },
            };
        }
        if (amount > totalPaid) {
            return {
                response_action: "errors",
                errors: {
                    [AMOUNT_BLOCK_ID]: `Amount cannot exceed total paid (${
                        totalPaid.toFixed(2)
                    } USD)`,
                },
            };
        }
    }

    const refundType: RefundType = payload.refund_to === "store_credit"
        ? "store_credit"
        : "original_method";

    const orderRef = {
        orderId: payload.order_id!,
        orderNumber: payload.order_number,
        approvedBy: args.userId,
        isTest: payload.is_test === true,
    };

    const requests: PreparedRequest[] = [];
    if (needsCancel) requests.push(buildCancelOrderRequest(orderRef));
    if (needsRefund) {
        requests.push(
            buildCreateRefundRequest(orderRef, {
                refundType,
                amount: modalVals.amount!,
                transactions: payload.transactions,
            }),
        );
    }

    if (REFUND_DRY_RUN) {
        await postDryRunPreviews(
            client,
            REFUND_CHANNELS.test,
            requests.map((r) => ({
                header: `:test_tube: *DRY RUN* — would POST to ShopifyRefundHandler: *${r.label}*`,
                label: `${payload.order_number} (${payload.first_name} ${payload.last_name})`,
                steps: [requestStep(r)],
            })),
        );
    } else {
        const results = await Promise.all(
            requests.map(async (r) => ({ req: r, res: await executeActionRequest(r) })),
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
        amount: needsRefund ? modalVals.amount! : undefined,
        refundType: needsRefund ? refundType : undefined,
        dryRun: REFUND_DRY_RUN,
        approveAction: modalVals.action,
        restock: modalVals.restock,
        sendNotification: modalVals.sendNotification,
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
