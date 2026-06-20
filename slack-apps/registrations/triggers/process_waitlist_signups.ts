import { TriggerContextData, TriggerTypes } from "deno-slack-api/mod.ts";
import type { Trigger } from "deno-slack-sdk/types.ts";
import ProcessWaitlistSignupsWorkflow from "../workflows/process_waitlist_signups.ts";

const trigger: Trigger<typeof ProcessWaitlistSignupsWorkflow.definition> = {
    type: TriggerTypes.Shortcut,
    name: "See current waitlist and process (admit someone or cancel/remove)",
    description: "Link trigger — paste into any channel to start the waitlist workflow",
    workflow: `#/workflows/${ProcessWaitlistSignupsWorkflow.definition.callback_id}`,
    inputs: {
        interactivity: {
            value: TriggerContextData.Shortcut.interactivity,
        },
        channel_id: {
            value: TriggerContextData.Shortcut.channel_id,
        },
        user_id: {
            value: TriggerContextData.Shortcut.user_id,
        },
    },
};

export default trigger;
