/** Workflow boundary for the orders-export league picker. Thin SDK wiring;
 *  modal shape + option catalogs + state-machine glue live in
 *  `domain/league/orders_export_modal.ts` and `selection_state.ts`. */

import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";

import {
    buildOrdersExportModal,
    CALLBACK_ID,
    readCheckboxes,
    SEASON_ACTION_ID,
    SPORT_ACTION_ID,
    YEAR_ACTION_ID,
} from "../views/league/orders_export_modal.ts";
import {
    captureCheckboxes,
    getInitialState,
    type LeagueSelectionState,
    parseMetadata,
    setSeason,
    setSport,
    setYear,
    stateToLeagues,
} from "../views/league/selection_state.ts";
import type { Season } from "../domain/league/types.ts";
import { CURRENT_SEASON, CURRENT_YEAR } from "../config/season.ts";
import { executionId } from "../shared/slack/workflow.ts";

export const GetLeagueSelectionsFunction = DefineFunction({
    callback_id: "get_league_selections",
    title: "Get League Selections",
    source_file: "functions/get_league_selections_from_modal.ts",
    input_parameters: {
        properties: {
            interactivity: { type: Schema.slack.types.interactivity },
        },
        required: ["interactivity"],
    },
    output_parameters: {
        properties: {
            selected_leagues_json: { type: Schema.types.string },
        },
        required: ["selected_leagues_json"],
    },
});

const handler = SlackFunction(GetLeagueSelectionsFunction, async ({ inputs, client }) => {
    await client.views.open({
        interactivity_pointer: inputs.interactivity.interactivity_pointer,
        view: buildOrdersExportModal(getInitialState(CURRENT_YEAR, CURRENT_SEASON)),
    });
    return { completed: false };
});

/** One row per driver dropdown: the action id the SDK fires, and the state
 *  mutation to apply with the raw selected value. The handler below is a single
 *  registration that table-dispatches on `action_id`. */
const DRIVER_MUTATORS: Record<
    string,
    (state: LeagueSelectionState, raw: string) => LeagueSelectionState
> = {
    [YEAR_ACTION_ID]: (state, raw) => setYear(state, parseInt(raw, 10)),
    [SEASON_ACTION_ID]: (state, raw) => setSeason(state, raw as Season),
    [SPORT_ACTION_ID]: (state, raw) => setSport(state, raw),
};

handler.addBlockActionsHandler(
    new RegExp(`^(${Object.keys(DRIVER_MUTATORS).join("|")})$`),
    async ({ action, body, client }) => {
        const mutate = DRIVER_MUTATORS[action.action_id];
        if (!mutate) return;
        // Snapshot the visible page's checkbox ticks into the persisted state,
        // apply the driver's mutation, then re-render the modal in place.
        const state = parseMetadata(body.view.private_metadata || "{}");
        const { wtnb, open } = readCheckboxes(body.view.state?.values ?? {});
        const saved = captureCheckboxes(state, wtnb, open);
        const raw = body.actions[0].selected_option.value;
        await client.views.update({
            view_id: body.view.id,
            view: buildOrdersExportModal(mutate(saved, raw)),
        });
    },
);

handler.addViewSubmissionHandler(CALLBACK_ID, async ({ body, view, client }) => {
    const state = parseMetadata(view.private_metadata || "{}");
    const { wtnb, open } = readCheckboxes(view.state?.values ?? {});
    const final = captureCheckboxes(state, wtnb, open);
    const leagues = stateToLeagues(final);
    console.log("[get_league_selections] submit:", JSON.stringify(leagues, null, 2));

    const execId = executionId(body);
    if (execId) {
        await client.functions.completeSuccess({
            function_execution_id: execId,
            outputs: { selected_leagues_json: JSON.stringify(leagues) },
        });
    }
});

export default handler;
