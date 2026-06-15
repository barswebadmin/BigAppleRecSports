import { DefineWorkflow, Schema } from "deno-slack-sdk/mod.ts";
import { GetLeagueWaitlistSelectionFunction } from "../functions/get_league_waitlist_selection.ts";
import { HandleWaitlistActionsFunction } from "../functions/handle_waitlist_actions.ts";

/**
 * Dry-run waitlist preview: identical fetch/render to the real processing
 * workflow, but `handle_waitlist_actions` runs in dry_run mode — it posts the
 * exact requests (URL, headers, body) that would be sent and executes nothing.
 * There is no spreadsheet step, so no sheet write happens either.
 */
const DryRunWaitlistWorkflow = DefineWorkflow({
    callback_id: "dry_run_waitlist_workflow",
    title: "Waitlist Dry Run (preview requests, no changes)",
    description: "Preview exactly what admit/remove would send, without making any changes",
    input_parameters: {
        properties: {
            interactivity: { type: Schema.slack.types.interactivity },
            channel_id: { type: Schema.slack.types.channel_id },
        },
        required: ["interactivity", "channel_id"],
    },
});

const selectionStep = DryRunWaitlistWorkflow.addStep(GetLeagueWaitlistSelectionFunction, {
    interactivity: DryRunWaitlistWorkflow.inputs.interactivity,
    channel_id: DryRunWaitlistWorkflow.inputs.channel_id,
});

DryRunWaitlistWorkflow.addStep(HandleWaitlistActionsFunction, {
    interactivity: selectionStep.outputs.interactivity,
    channel_id: DryRunWaitlistWorkflow.inputs.channel_id,
    selected_league: selectionStep.outputs.selected_league,
    dry_run: true,
});

export default DryRunWaitlistWorkflow;
