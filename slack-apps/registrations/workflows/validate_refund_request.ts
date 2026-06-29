/**
 * Workflow that backs the `/eval-refund-request` slash command. Wires the
 * Shortcut trigger (`start_refund_eval.ts`) into the orchestrator function
 * (`send_request_for_eval.ts`).
 */

import { DefineWorkflow, Schema } from "deno-slack-sdk/mod.ts";
import { SendRequestForEvalFunction } from "../functions/send_request_for_eval.ts";

const ValidateRefundRequestWorkflow = DefineWorkflow({
    callback_id: "validate_refund_request",
    title: "Evaluate Refund Request",
    input_parameters: {
        properties: {
            interactivity: { type: Schema.slack.types.interactivity },
            channel_id: { type: Schema.slack.types.channel_id },
            slack_channel: { type: Schema.types.string },
        },
        required: ["interactivity", "channel_id"],
    },
});

ValidateRefundRequestWorkflow.addStep(SendRequestForEvalFunction, {
    interactivity: ValidateRefundRequestWorkflow.inputs.interactivity,
    channel_id: ValidateRefundRequestWorkflow.inputs.channel_id,
    slack_channel: ValidateRefundRequestWorkflow.inputs.slack_channel,
});

export default ValidateRefundRequestWorkflow;
