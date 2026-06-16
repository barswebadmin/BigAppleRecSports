import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { buildLeagueKey, parseLeagueKey } from "../lib/waitlists/league_key.ts";
import { compareWeekday, CURRENT_LEAGUES, slackLink } from "../config.ts";
import { capitalize, formatDivisionLabel } from "../utils/formatters.ts";
import { getDefaultLeagueForChannel } from "../config.ts";
import { waitlistSheetUrl } from "../lib/waitlists/sheet_service.ts";

const CALLBACK_ID = "league_waitlist_selection";

function buildLeagueOptions(): { text: string; value: string }[] {
    // Sort by sport (A→Z), then day of week (Mon→Sun, not alphabetical), then
    // division reverse-alphabetical (wtnb before open).
    return CURRENT_LEAGUES
        .slice()
        .sort((a, b) =>
            a.sport.localeCompare(b.sport) ||
            compareWeekday(a.day, b.day) ||
            b.division.localeCompare(a.division)
        )
        .map((lg) => ({
            text: `${capitalize(lg.sport)} - ${capitalize(lg.day)} - ${
                formatDivisionLabel(lg.division)
            } Division`,
            value: buildLeagueKey(lg.sport, lg.day, lg.division),
        }));
}

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
    const options = buildLeagueOptions().map((o) => ({
        text: { type: "plain_text" as const, text: o.text },
        value: o.value,
    }));

    const defaultValue = getDefaultLeagueForChannel(inputs.channel_id);
    const initialOption = defaultValue ? options.find((o) => o.value === defaultValue) : undefined;

    const selectElement: Record<string, unknown> = {
        type: "static_select",
        action_id: "league_select",
        placeholder: { type: "plain_text", text: "Select a league..." },
        options,
    };
    if (initialOption) selectElement.initial_option = initialOption;

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

    // deno-lint-ignore no-explicit-any
    const execId = (body as any).function_data?.execution_id;
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

handler.addViewClosedHandler(CALLBACK_ID, () => {});

export default handler;
