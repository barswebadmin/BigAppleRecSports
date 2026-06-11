import { DefineWorkflow, Schema } from "deno-slack-sdk/mod.ts";
import { GetLeagueWaitlistSelectionFunction } from "../functions/get_league_waitlist_selection.ts";
import { CheckWaitlistFunction } from "../functions/check_waitlist.ts";

const CheckWaitlistWorkflow = DefineWorkflow({
    callback_id: "check_waitlist_workflow",
    title: "Check Waitlist (read-only)",
    description: "View the current waitlist for a league without making changes",
    input_parameters: {
        properties: {
            interactivity: { type: Schema.slack.types.interactivity },
            channel_id: { type: Schema.slack.types.channel_id },
        },
        required: ["interactivity", "channel_id"],
    },
});

const selectionStep = CheckWaitlistWorkflow.addStep(GetLeagueWaitlistSelectionFunction, {
    interactivity: CheckWaitlistWorkflow.inputs.interactivity,
    channel_id: CheckWaitlistWorkflow.inputs.channel_id,
});

CheckWaitlistWorkflow.addStep(CheckWaitlistFunction, {
    interactivity: selectionStep.outputs.interactivity,
    selected_league: selectionStep.outputs.selected_league,
});

export default CheckWaitlistWorkflow;
