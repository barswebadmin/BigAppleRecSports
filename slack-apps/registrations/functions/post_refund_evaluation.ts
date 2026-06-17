/** Workflow boundary for the refund-evaluation review flow. Thin SDK wiring;
 *  every concern lives in `domain/refund/`. */

import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";

import {
    AMOUNT_ACTION_ID,
    AMOUNT_BLOCK_ID,
    APPROVE_MODAL_CALLBACK_ID,
    type ApproveModalMeta,
    TYPE_ACTION_ID,
    TYPE_BLOCK_ID,
} from "../domain/refund/approve_modal.ts";
import { APPROVE_ACTION_ID, DENY_ACTION_ID } from "../domain/refund/eval_blocks.ts";
import {
    handleApproveButton,
    handleApproveModalSubmit,
    handleDenyButton,
    parsePayload,
    runPostRefundEvaluation,
} from "../domain/refund/orchestrator.ts";

// Re-exported for in-process regression tests — keeps the previous public
// surface the tests reach for; the orchestrator is the implementation.
export { runPostRefundEvaluation } from "../domain/refund/orchestrator.ts";

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

export default SlackFunction(
    PostRefundEvaluationFunction,
    ({ inputs, client }) => runPostRefundEvaluation(inputs, client),
)
    .addBlockActionsHandler(APPROVE_ACTION_ID, async ({ inputs, body, client }) => {
        const payload = parsePayload(inputs.evaluation_json);
        if (!payload) return;
        await handleApproveButton(payload, {
            channel: body.container.channel_id,
            messageTs: body.container.message_ts,
            interactivityPointer: body.interactivity.interactivity_pointer,
        }, client);
    })
    .addBlockActionsHandler(DENY_ACTION_ID, async ({ inputs, body, client }) => {
        const payload = parsePayload(inputs.evaluation_json);
        if (!payload) return;
        await handleDenyButton(payload, {
            userId: body.user.id,
            channel: body.container.channel_id,
            messageTs: body.container.message_ts,
            executionId: body.function_data.execution_id,
        }, client);
    })
    .addViewSubmissionHandler(APPROVE_MODAL_CALLBACK_ID, async ({ inputs, body, view, client }) => {
        const payload = parsePayload(inputs.evaluation_json);
        if (!payload) return;
        const meta = JSON.parse(view.private_metadata || "{}") as ApproveModalMeta;
        const values = view.state.values;
        return await handleApproveModalSubmit(payload, {
            userId: body.user.id,
            executionId: body.function_data.execution_id,
            meta,
            rawAmount: values[AMOUNT_BLOCK_ID]?.[AMOUNT_ACTION_ID]?.value ?? "",
            rawType: values[TYPE_BLOCK_ID]?.[TYPE_ACTION_ID]?.selected_option?.value,
            amountBlockId: AMOUNT_BLOCK_ID,
        }, client);
    });
