import { DefineWorkflow, Schema } from "deno-slack-sdk/mod.ts";
import { GetLeagueWaitlistSelectionFunction } from "../functions/get_league_waitlist_selection.ts";
import { HandleWaitlistActionsFunction } from "../functions/handle_waitlist_actions.ts";
import { UpdateWaitlistSpreadsheetFunction } from "../functions/update_waitlist_spreadsheet.ts";

const ProcessWaitlistWorkflow = DefineWorkflow({
    callback_id: "process_waitlist",
    title: "Waitlist Processing (fetch, admit/remove entries)",
    description: "Review current waitlist signups and handle admissions or cancellations",
    input_parameters: {
        properties: {
            interactivity: { type: Schema.slack.types.interactivity },
            channel_id: { type: Schema.slack.types.channel_id },
            user_id: { type: Schema.slack.types.user_id },
        },
        required: ["interactivity", "channel_id", "user_id"],
    },
});

// Step 1: User picks a league
const selectionStep = ProcessWaitlistWorkflow.addStep(GetLeagueWaitlistSelectionFunction, {
    interactivity: ProcessWaitlistWorkflow.inputs.interactivity,
    channel_id: ProcessWaitlistWorkflow.inputs.channel_id,
});

// Step 2: Fetch waitlist data, show entries, handle the admit/remove actions,
// and post the result message. Emits actions_json for the sheet write below.
const actionsStep = ProcessWaitlistWorkflow.addStep(HandleWaitlistActionsFunction, {
    interactivity: selectionStep.outputs.interactivity,
    channel_id: ProcessWaitlistWorkflow.inputs.channel_id,
    selected_league: selectionStep.outputs.selected_league,
});

// Step 3: Persist the Status column. Kept as its own step (vs. folding into
// step 2) for the audit/retry/decoupling benefits of a discrete write stage.
// Its progress title ("Finishing up") reads truthfully whether the run admitted
// rows or was cancelled (no actions → the function no-ops), so it's never the
// misleading "Saving updates…" toast on cancel.
ProcessWaitlistWorkflow.addStep(UpdateWaitlistSpreadsheetFunction, {
    actions_json: actionsStep.outputs.actions_json,
});

export default ProcessWaitlistWorkflow;
