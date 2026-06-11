import type { Trigger } from "deno-slack-sdk/types.ts";
import { TriggerTypes } from "deno-slack-api/mod.ts";
import HandleRefundRequestWorkflow from "../workflows/handle_refund_request.ts";

const trigger: Trigger<typeof HandleRefundRequestWorkflow.definition> = {
    type: TriggerTypes.Webhook,
    name: "Handle Refund Request (Webhook)",
    description: "POST a refund request payload to process it",
    workflow: `#/workflows/${HandleRefundRequestWorkflow.definition.callback_id}`,
    inputs: {
        refund_request: { value: "{{data.refund_request}}" },
    },
    // ── Flat field implementation (revert to this if typed object doesn't work) ──
    // inputs: {
    //     created_at: { value: "{{data.created_at}}" },
    //     order_number: { value: "{{data.order_number}}" },
    //     first_name: { value: "{{data.first_name}}" },
    //     last_name: { value: "{{data.last_name}}" },
    //     email_address: { value: "{{data.email_address}}" },
    //     refund_type: { value: "{{data.refund_type}}" },
    //     notes: { value: "{{data.notes}}" },
    // },
};

export default trigger;
