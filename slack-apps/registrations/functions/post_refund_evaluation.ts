import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
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
import { REFUND_PROCESS_URL, resolveRefundChannel } from "../config.ts";

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

/** Pick the estimate + default type that matches the requested refund/credit. */
function pickEstimate(p: RefundEvaluationPayload): { amount: number; refundType: string } {
    const wantsCredit = p.refund_or_credit.trim().toLowerCase().includes("credit");
    const est = wantsCredit ? p.estimated_store_credit : p.estimated_refund_to_original;
    return {
        amount: est?.amount ?? 0,
        refundType: wantsCredit ? "store_credit" : "refund_to_original",
    };
}

export default SlackFunction(
    PostRefundEvaluationFunction,
    async ({ inputs, client }) => {
        const payload = parsePayload(inputs.evaluation_json);
        if (!payload) {
            return {
                error: `Invalid evaluation_json: could not parse JSON. Received (${typeof inputs
                    .evaluation_json}): ${String(inputs.evaluation_json).slice(0, 500)}`,
            };
        }

        // Routing lives in Slack, not the Lambda payload (separation of concerns).
        const channel = resolveRefundChannel({ isTest: payload.isTest });

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
    },
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

        // Send the approval up to the Lambda for processing.
        await fetch(REFUND_PROCESS_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                action: "process_refund",
                order_id: payload.order_id,
                order_number: payload.order_number,
                email_address: payload.email_address,
                refund_type: refundType,
                amount,
                approved_by: body.user.id,
            }),
        });

        const decision: RefundDecision = {
            status: "approved",
            by: body.user.id,
            amount,
            refundType,
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
