import { TriggerContextData, TriggerTypes } from "deno-slack-api/mod.ts";
import type { Trigger } from "deno-slack-sdk/types.ts";
import CheckWaitlistWorkflow from "../workflows/check_waitlist.ts";

const trigger: Trigger<typeof CheckWaitlistWorkflow.definition> = {
    type: TriggerTypes.Shortcut,
    name: "Check current waitlist (read-only)",
    description: "Link trigger — view a league's waitlist without making changes",
    workflow: `#/workflows/${CheckWaitlistWorkflow.definition.callback_id}`,
    inputs: {
        interactivity: {
            value: TriggerContextData.Shortcut.interactivity,
        },
        channel_id: {
            value: TriggerContextData.Shortcut.channel_id,
        },
    },
};

export default trigger;
