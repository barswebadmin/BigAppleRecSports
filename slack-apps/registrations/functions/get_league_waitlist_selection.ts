import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { buildLeagueKey, parseLeagueKey } from "../domain/league/key.ts";
import {
    compareWeekday,
    CURRENT_LEAGUES,
    getDefaultLeagueForChannel,
} from "../domain/league/catalog.ts";
import { slackLink } from "../config/slack.ts";
import { formatDivisionLabel } from "../domain/league/format.ts";
import { capitalize } from "../shared/text/strings.ts";
import { executionId } from "../shared/slack/workflow.ts";
import { waitlistSheetUrl } from "../domain/waitlist/sheet.ts";

const CALLBACK_ID = "league_waitlist_selection";

/** League dropdown options sorted by sport (A→Z), then weekday (Mon→Sun, not
 *  alphabetical), then division reverse-alphabetical (wtnb before open). Built
 *  once at module load — `CURRENT_LEAGUES` is static for the season. */
const LEAGUE_OPTIONS: { text: { type: "plain_text"; text: string }; value: string }[] =
    CURRENT_LEAGUES
        .slice()
        .sort((a, b) =>
            a.sport.localeCompare(b.sport) ||
            compareWeekday(a.day, b.day) ||
            b.division.localeCompare(a.division)
        )
        .map((lg) => ({
            text: {
                type: "plain_text" as const,
                text: `${capitalize(lg.sport)} - ${capitalize(lg.day)} - ${
                    formatDivisionLabel(lg.division)
                } Division`,
            },
            value: buildLeagueKey(lg.sport, lg.day, lg.division),
        }));

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
    const defaultValue = getDefaultLeagueForChannel(inputs.channel_id);
    const initialOption = defaultValue
        ? LEAGUE_OPTIONS.find((o) => o.value === defaultValue)
        : undefined;

    const selectElement = {
        type: "static_select",
        action_id: "league_select",
        placeholder: { type: "plain_text", text: "Select a league..." },
        options: LEAGUE_OPTIONS,
        ...(initialOption ? { initial_option: initialOption } : {}),
    };

    const openRes = await client.views.open({
        interactivity_pointer: inputs.interactivity.interactivity_pointer,
        view: {
            type: "modal",
            callback_id: CALLBACK_ID,
            // Slack caps modal titles at 24 chars; the full "…to get waitlist" intent
            // lives in the body sentence + the Next button.
            title: { type: "plain_text", text: "Select a league" },
            submit: { type: "plain_text", text: "Next" },
            close: { type: "plain_text", text: "Cancel" },
            blocks: [
                {
                    type: "section",
                    text: {
                        type: "mrkdwn",
                        text:
                            `Select from the dropdown to see waitlist for a league and click *Next* to fetch the ${
                                slackLink("Google Sheet", waitlistSheetUrl())
                            } and see the current waitlist for that league`,
                    },
                },
                {
                    type: "context",
                    elements: [{
                        type: "mrkdwn",
                        text:
                            "(This workflow sets the Status column when processing, so this filters to rows where Status is empty)",
                    }],
                },
                {
                    type: "input",
                    block_id: "league_block",
                    label: { type: "plain_text", text: "League" },
                    element: selectElement,
                },
            ],
        },
    });

    if (!openRes.ok) return { error: `Failed to open modal: ${openRes.error}` };
    return { completed: false };
});

handler.addViewSubmissionHandler(CALLBACK_ID, async ({ body, view, client }) => {
    const leagueValue = view.state?.values?.league_block?.league_select?.selected_option?.value ??
        "";

    const { sport, day, division: div } = parseLeagueKey(leagueValue);
    const display = leagueValue
        ? `${capitalize(sport)} - ${capitalize(day)} - ${formatDivisionLabel(div)}`
        : "(none)";
    console.log(`[${CALLBACK_ID}] selected: ${display}`);

    const execId = executionId(body);
    if (execId) {
        await client.functions.completeSuccess({
            function_execution_id: execId,
            outputs: {
                interactivity: body.interactivity,
                selected_league: leagueValue,
            },
        });
    }
});

export default handler;
