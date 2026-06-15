import { DefineWorkflow, Schema } from "deno-slack-sdk/mod.ts";
import { PostRefundEvaluationFunction } from "../functions/post_refund_evaluation.ts";

const EvaluateRefundRequestWorkflow = DefineWorkflow({
    callback_id: "evaluate_refund_request",
    title: "Evaluate Refund Request",
    description: "Receives an enriched Lambda evaluation payload and posts the Slack review card",
    input_parameters: {
        properties: {
            evaluation_json: { type: Schema.types.string },
        },
        required: ["evaluation_json"],
    },
});

EvaluateRefundRequestWorkflow.addStep(PostRefundEvaluationFunction, {
    evaluation_json: EvaluateRefundRequestWorkflow.inputs.evaluation_json,
});

export default EvaluateRefundRequestWorkflow;
