import { TriggerContextData, TriggerTypes } from "deno-slack-api/mod.ts";
import type { Trigger } from "deno-slack-sdk/types.ts";
import DryRunWaitlistWorkflow from "../workflows/dry_run_waitlist.ts";

const trigger: Trigger<typeof DryRunWaitlistWorkflow.definition> = {
    type: TriggerTypes.Shortcut,
    name: "Waitlist DRY RUN — preview admit/remove requests (no changes)",
    description: "Link trigger — same flow as processing, but only previews the requests",
    workflow: `#/workflows/${DryRunWaitlistWorkflow.definition.callback_id}`,
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
