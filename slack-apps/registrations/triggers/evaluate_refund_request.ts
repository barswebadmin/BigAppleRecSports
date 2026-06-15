import type { Trigger } from "deno-slack-sdk/types.ts";
import { TriggerTypes } from "deno-slack-api/mod.ts";
import EvaluateRefundRequestWorkflow from "../workflows/evaluate_refund_request.ts";

/**
 * Webhook trigger — Lambda POSTs the serialised EvaluationPayload as:
 *   { "evaluation_json": "<JSON string>" }
 */
const trigger: Trigger<typeof EvaluateRefundRequestWorkflow.definition> = {
    type: TriggerTypes.Webhook,
    name: "Evaluate Refund Request (Webhook)",
    description: "Triggered by Lambda after enriching a refund request",
    workflow: `#/workflows/${EvaluateRefundRequestWorkflow.definition.callback_id}`,
    inputs: {
        evaluation_json: { value: "{{data.evaluation_json}}" },
    },
};

export default trigger;
