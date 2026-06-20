/** Workflow step: open the league-picker modal, complete with the selected key.
 *  Modal shape + dropdown options + block-id contract live in
 *  `domain/league/waitlist_select_modal.ts`; this file is SDK wiring only. */

import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { getDefaultLeagueForChannel } from "../domain/league/catalog.ts";
import { formatDivision } from "../domain/league/format.ts";
import { parseLeagueKey } from "../domain/league/identity.ts";
import {
    buildLeagueSelectModal,
    findInitialLeagueOption,
    leagueValueFromView,
} from "../views/league/waitlist_select_modal.ts";
import { waitlistSheetUrl } from "../domain/waitlist/sheet.ts";
import { capitalize } from "../shared/text/strings.ts";
import { executionId } from "../shared/slack/workflow.ts";

const CALLBACK_ID = "league_waitlist_selection";

export const GetLeagueWaitlistSelectionFunction = DefineFunction({
    callback_id: "get_league_waitlist_selection",
    title: "Choosing a league",
    source_file: "functions/get_league_waitlist_selection.ts",
    input_parameters: {
        properties: {
            interactivity: { type: Schema.slack.types.interactivity },
            channel_id: { type: Schema.slack.types.channel_id },
        },
        required: ["interactivity", "channel_id"],
    },
    output_parameters: {
        properties: {
            interactivity: { type: Schema.slack.types.interactivity },
            selected_league: { type: Schema.types.string },
        },
        required: ["selected_league"],
    },
});

const handler = SlackFunction(GetLeagueWaitlistSelectionFunction, async ({ inputs, client }) => {
    const openRes = await client.views.open({
        interactivity_pointer: inputs.interactivity.interactivity_pointer,
        view: buildLeagueSelectModal({
            callbackId: CALLBACK_ID,
            sheetUrl: waitlistSheetUrl(),
            initial: findInitialLeagueOption(getDefaultLeagueForChannel(inputs.channel_id)),
        }),
    });
    if (!openRes.ok) return { error: `Failed to open modal: ${openRes.error}` };
    return { completed: false };
});

handler.addViewSubmissionHandler(CALLBACK_ID, async ({ body, view, client }) => {
    const leagueValue = leagueValueFromView(view.state?.values ?? {});
    const { sport, day, division } = parseLeagueKey(leagueValue);
    const display = leagueValue
        ? `${capitalize(sport)} - ${capitalize(day)} - ${formatDivision(division, "label")}`
        : "(none)";
    console.log(`[${CALLBACK_ID}] selected: ${display}`);

    const execId = executionId(body);
    if (execId) {
        await client.functions.completeSuccess({
            function_execution_id: execId,
            outputs: { interactivity: body.interactivity, selected_league: leagueValue },
        });
    }
});

export default handler;
