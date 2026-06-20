import { TriggerTypes } from "deno-slack-api/mod.ts";
import type { Trigger } from "deno-slack-sdk/types.ts";
import ReceiveWaitlistOrderWorkflow from "../workflows/receive_waitlist_signup.ts";

const trigger: Trigger<typeof ReceiveWaitlistOrderWorkflow.definition> = {
    type: TriggerTypes.Webhook,
    name: "Receive Waitlist Order (Webhook)",
    description: "POST a waitlist order payload to update the spreadsheet",
    workflow: `#/workflows/${ReceiveWaitlistOrderWorkflow.definition.callback_id}`,
    inputs: {
        body: { value: "{{data.body}}" },
    },
};

export default trigger;
