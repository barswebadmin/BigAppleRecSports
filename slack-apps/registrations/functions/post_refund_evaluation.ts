import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import type { SlackAPIClient } from "deno-slack-api/types.ts";
import type { RefundEvaluationPayload } from "../types/evaluation_payload.ts";
import {
    APPROVE_ACTION_ID,
    buildRefundEvalBlocks,
    DENY_ACTION_ID,
    type RefundDecision,
} from "../lib/slack/refund_eval_blocks.ts";
import {
    AMOUNT_ACTION_ID,
    AMOUNT_BLOCK_ID,
    APPROVE_MODAL_CALLBACK_ID,
    type ApproveModalMeta,
    buildApproveModal,
    TYPE_ACTION_ID,
    TYPE_BLOCK_ID,
} from "../lib/slack/refund_approve_modal.ts";
import { REFUND_DRY_RUN, REFUND_TEST_CHANNEL, resolveRefundChannel } from "../config.ts";
import {
    buildCancelOrderRequest,
    buildCreateRefundRequest,
    executeLambdaRequest,
    type RefundType,
} from "../lib/refunds/lambda_requests.ts";
import { postDryRunPreviews, requestStep } from "../lib/slack/dry_run.ts";

export const PostRefundEvaluationFunction = DefineFunction({
    callback_id: "post_refund_evaluation",
    title: "Post Refund Evaluation",
    description: "Receives the Lambda's refund evaluation payload and posts the review message",
    source_file: "functions/post_refund_evaluation.ts",
    input_parameters: {
        properties: {
            evaluation_json: {
                type: Schema.types.string,
                description: "JSON-serialised RefundEvaluationPayload from the Lambda",
            },
        },
        required: ["evaluation_json"],
    },
    output_parameters: {
        properties: {
            message_ts: { type: Schema.types.string },
            channel_id: { type: Schema.types.string },
        },
        required: ["message_ts", "channel_id"],
    },
});

function parsePayload(raw: unknown): RefundEvaluationPayload | null {
    try {
        return typeof raw === "string" ? JSON.parse(raw) : (raw as RefundEvaluationPayload);
    } catch {
        return null;
    }
}

/** Pick the estimate that matches the canonical `refund_type`. */
function pickEstimate(p: RefundEvaluationPayload): { amount: number; refundType: string } {
    const wantsCredit = p.refund_type === "store_credit";
    const est = wantsCredit ? p.estimated_store_credit : p.estimated_refund_to_original;
    return {
        amount: est?.amount ?? 0,
        refundType: p.refund_type,
    };
}

/** Main handler body — exported for in-process regression tests (Stage 8). */
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

    // Routing lives in Slack, not the Lambda payload (separation of concerns).
    const channel = resolveRefundChannel({ is_test: payload.is_test });

    const result = await client.chat.postMessage({
        channel,
        text:
            `Refund request from ${payload.first_name} ${payload.last_name} (${payload.order_number})`,
        blocks: buildRefundEvalBlocks(payload),
    });

    if (!result.ok) {
        return { error: `chat.postMessage failed: ${result.error}` };
    }

    // Stay open so we can handle the Approve/Deny buttons; we complete the
    // function from the button / modal-submission handlers below.
    return { completed: false };
}

export default SlackFunction(
    PostRefundEvaluationFunction,
    async ({ inputs, client }) => await runPostRefundEvaluation(inputs, client),
)
    // Approve → open the editable amount/type modal.
    .addBlockActionsHandler(APPROVE_ACTION_ID, async ({ inputs, body, client }) => {
        const payload = parsePayload(inputs.evaluation_json);
        if (!payload) return;

        const est = pickEstimate(payload);
        const meta: ApproveModalMeta = {
            channel: body.container.channel_id,
            message_ts: body.container.message_ts,
        };

        await client.views.open({
            interactivity_pointer: body.interactivity.interactivity_pointer,
            view: buildApproveModal({
                orderNumber: payload.order_number,
                estimatedAmount: est.amount,
                refundType: est.refundType,
                refundable: payload.refundable_balance,
                meta,
            }),
        });
    })
    // Don't send → update the message, no Lambda call.
    .addBlockActionsHandler(DENY_ACTION_ID, async ({ inputs, body, client }) => {
        const payload = parsePayload(inputs.evaluation_json);
        if (!payload) return;

        const decision: RefundDecision = { status: "denied", by: body.user.id };
        await client.chat.update({
            channel: body.container.channel_id,
            ts: body.container.message_ts,
            text: `Refund request marked do-not-send (${payload.order_number})`,
            blocks: buildRefundEvalBlocks(payload, decision),
        });

        await client.functions.completeSuccess({
            function_execution_id: body.function_data.execution_id,
            outputs: {
                message_ts: body.container.message_ts,
                channel_id: body.container.channel_id,
            },
        });
    })
    // Modal submit → POST to Lambda, finalize the message.
    .addViewSubmissionHandler(APPROVE_MODAL_CALLBACK_ID, async ({ inputs, body, view, client }) => {
        const payload = parsePayload(inputs.evaluation_json);
        if (!payload) return;

        const meta = JSON.parse(view.private_metadata || "{}") as ApproveModalMeta;
        const values = view.state.values;
        const rawAmount = values[AMOUNT_BLOCK_ID]?.[AMOUNT_ACTION_ID]?.value ?? "";
        const refundType = values[TYPE_BLOCK_ID]?.[TYPE_ACTION_ID]?.selected_option?.value ??
            "refund_to_original";

        const amount = Number.parseFloat(rawAmount);
        if (!Number.isFinite(amount) || amount < 0) {
            return {
                response_action: "errors",
                errors: { [AMOUNT_BLOCK_ID]: "Enter a valid non-negative dollar amount" },
            };
        }
        if (!payload.order_id) {
            return {
                response_action: "errors",
                errors: {
                    [AMOUNT_BLOCK_ID]: "Evaluation is missing the order id — cannot process",
                },
            };
        }

        // Two separate, independently-routable Lambda actions: cancel the order
        // and refund the money. The Lambda owns the Shopify mutations; these
        // payloads just route + carry the ids/transactions it needs.
        const orderRef = {
            orderId: payload.order_id,
            orderNumber: payload.order_number,
            approvedBy: body.user.id,
            isTest: payload.is_test === true,
        };
        const requests = [
            buildCancelOrderRequest(orderRef),
            buildCreateRefundRequest(orderRef, {
                refundType: refundType as RefundType,
                amount,
                transactions: payload.transactions,
            }),
        ];

        if (REFUND_DRY_RUN) {
            // Preview the exact payloads to the test channel. Flip REFUND_DRY_RUN
            // to false to POST these same payloads to the Lambda for real.
            await postDryRunPreviews(
                client,
                REFUND_TEST_CHANNEL,
                requests.map((r) => ({
                    header:
                        `:test_tube: *DRY RUN* — would POST to ShopifyRefundHandler: *${r.label}*`,
                    label: `${payload.order_number} (${payload.first_name} ${payload.last_name})`,
                    steps: [requestStep(r)],
                })),
            );
        } else {
            for (const r of requests) {
                const res = await executeLambdaRequest(r);
                if (!res.ok) {
                    console.error(`[refund] ${r.label} failed: ${res.status} ${res.body}`);
                }
            }
        }

        const decision: RefundDecision = {
            status: "approved",
            by: body.user.id,
            amount,
            refundType,
            dryRun: REFUND_DRY_RUN,
        };
        await client.chat.update({
            channel: meta.channel,
            ts: meta.message_ts,
            text: `Refund approved (${payload.order_number})`,
            blocks: buildRefundEvalBlocks(payload, decision),
        });

        await client.functions.completeSuccess({
            function_execution_id: body.function_data.execution_id,
            outputs: { message_ts: meta.message_ts, channel_id: meta.channel },
        });
    });
