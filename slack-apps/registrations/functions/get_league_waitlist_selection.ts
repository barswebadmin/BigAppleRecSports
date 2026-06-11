import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { CURRENT_LEAGUES } from "../config.ts";
import { capitalize } from "../utils/formatters.ts";
import { getDefaultLeagueForChannel } from "../config.ts";

const CALLBACK_ID = "league_waitlist_selection";

function formatDivisionLabel(div: string): string {
    return div === "wtnb" ? "WTNB+" : "Open";
}

function buildLeagueOptions(): { text: string; value: string }[] {
    const options = CURRENT_LEAGUES.map((lg) => ({
        text: `${capitalize(lg.sport)} - ${capitalize(lg.day)} - ${
            formatDivisionLabel(lg.division)
        } Division`,
        value: `${lg.sport}|${lg.day}|${lg.division}`,
    }));
    return options.sort((a, b) => a.text.localeCompare(b.text));
}

export const GetLeagueWaitlistSelectionFunction = DefineFunction({
    callback_id: "get_league_waitlist_selection",
    title: "Get League Waitlist Selection",
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
            title: { type: "plain_text", text: "Waitlist" },
            submit: { type: "plain_text", text: "Select League" },
            blocks: [
                {
                    type: "input",
                    block_id: "league_block",
                    label: { type: "plain_text", text: "Get current waitlist for" },
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

    console.log(`[league_selection] selected: ${leagueValue}`);

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
