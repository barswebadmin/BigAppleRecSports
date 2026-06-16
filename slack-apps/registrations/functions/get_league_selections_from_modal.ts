import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import {
    captureCheckboxes,
    currentDays,
    getInitialState,
    type LeagueSelectionState,
    parseMetadata,
    serializeMetadata,
    setSeason,
    setSport,
    setYear,
    stateToLeagues,
} from "../lib/leagues/selection_state.ts";
import { ALL_SEASONS, getDaysForSport } from "../config.ts";
import { capitalize } from "../utils/formatters.ts";
import { plainText } from "../lib/slack/blocks.ts";

const CALLBACK_ID = "shopify_orders_modal";
const SPORTS = ["bowling", "dodgeball", "kickball", "pickleball"];

interface Option {
    text: { type: "plain_text"; text: string };
    value: string;
}

const toOptions = (items: { label: string; value: string }[]): Option[] =>
    items.map((i) => ({ text: plainText(i.label), value: i.value }));

const select = (actionId: string, placeholder: string, options: Option[], initial?: Option) => ({
    type: "static_select" as const,
    action_id: actionId,
    placeholder: plainText(placeholder),
    options,
    ...(initial ? { initial_option: initial } : {}),
});

const checkboxes = (actionId: string, options: Option[], initial?: Option[]) => ({
    type: "checkboxes" as const,
    action_id: actionId,
    options,
    ...(initial?.length ? { initial_options: initial } : {}),
});

const YEAR_OPTIONS = toOptions(
    ["2022", "2023", "2024", "2025", "2026"].map((y) => ({ label: y, value: y })),
);
const SEASON_OPTIONS = toOptions(ALL_SEASONS.map((s) => ({ label: capitalize(s), value: s })));
const SPORT_OPTIONS = toOptions(SPORTS.map((s) => ({ label: capitalize(s), value: s })));

function dayOptionsFor(days: string[]): Option[] {
    return toOptions(days.map((d) => ({ label: capitalize(d), value: d })));
}

function buildView(state: LeagueSelectionState): Record<string, unknown> {
    const stored = currentDays(state);
    const available = getDaysForSport(state.sport);
    const wtnbOpts = dayOptionsFor(available.wtnb);
    const openOpts = dayOptionsFor(available.open);
    const wtnbInitial = wtnbOpts.filter((o) => (stored.wtnb as string[]).includes(o.value));
    const openInitial = openOpts.filter((o) => (stored.open as string[]).includes(o.value));
    const comboSuffix = `${state.year}_${state.season}_${state.sport}`;

    return {
        type: "modal",
        callback_id: CALLBACK_ID,
        title: plainText("Select league(s)"),
        submit: plainText("Done"),
        private_metadata: serializeMetadata(state),
        blocks: [
            {
                type: "input",
                block_id: "year_block",
                label: plainText("Year"),
                element: select(
                    "year_select",
                    "Year",
                    YEAR_OPTIONS,
                    YEAR_OPTIONS.find((o) => o.value === String(state.year)),
                ),
                dispatch_action: true,
            },
            {
                type: "input",
                block_id: "season_block",
                label: plainText("Season"),
                element: select(
                    "season_select",
                    "Season",
                    SEASON_OPTIONS,
                    SEASON_OPTIONS.find((o) => o.value === state.season),
                ),
                dispatch_action: true,
            },
            {
                type: "input",
                block_id: "sport_block",
                label: plainText("Sport"),
                element: select(
                    "sport_select",
                    "Sport",
                    SPORT_OPTIONS,
                    SPORT_OPTIONS.find((o) => o.value === state.sport),
                ),
                dispatch_action: true,
            },
            { type: "divider" },
            ...(wtnbOpts.length
                ? [
                    {
                        type: "input",
                        block_id: `wtnb_days_${comboSuffix}`,
                        label: plainText("WTNB Division"),
                        element: checkboxes(
                            "wtnb_days_select",
                            wtnbOpts,
                            wtnbInitial.length ? wtnbInitial : undefined,
                        ),
                        optional: true,
                    },
                ]
                : []),
            { type: "divider" },
            ...(openOpts.length
                ? [
                    {
                        type: "input",
                        block_id: `open_days_${comboSuffix}`,
                        label: plainText("Open Division"),
                        element: checkboxes(
                            "open_days_select",
                            openOpts,
                            openInitial.length ? openInitial : undefined,
                        ),
                        optional: true,
                    },
                ]
                : []),
        ],
    };
}

// ── Read current checkbox values from view.state.values ─────────────

interface ViewValues {
    [blockId: string]: {
        [actionId: string]: {
            selected_options?: { value: string }[];
        };
    };
}

function readCheckboxes(values: ViewValues): { wtnb: string[]; open: string[] } {
    const wtnbBlock = Object.keys(values).find((k) => k.startsWith("wtnb_days"));
    const openBlock = Object.keys(values).find((k) => k.startsWith("open_days"));
    return {
        wtnb: (wtnbBlock ? (values[wtnbBlock]?.wtnb_days_select?.selected_options ?? []) : []).map(
            (o) => o.value,
        ),
        open: (openBlock ? (values[openBlock]?.open_days_select?.selected_options ?? []) : []).map(
            (o) => o.value,
        ),
    };
}

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
        view: buildView(getInitialState()),
    });
    return { completed: false };
});

handler.addBlockActionsHandler("year_select", async ({ body, client }) => {
    const state = parseMetadata(body.view.private_metadata || "{}");
    const { wtnb, open } = readCheckboxes(body.view.state?.values ?? {});
    const saved = captureCheckboxes(state, wtnb, open);
    const year = parseInt(body.actions[0].selected_option.value, 10);
    await client.views.update({
        view_id: body.view.id,
        view: buildView(setYear(saved, year)),
    });
});

handler.addBlockActionsHandler("season_select", async ({ body, client }) => {
    const state = parseMetadata(body.view.private_metadata || "{}");
    const { wtnb, open } = readCheckboxes(body.view.state?.values ?? {});
    const saved = captureCheckboxes(state, wtnb, open);
    await client.views.update({
        view_id: body.view.id,
        view: buildView(setSeason(saved, body.actions[0].selected_option.value)),
    });
});

handler.addBlockActionsHandler("sport_select", async ({ body, client }) => {
    const state = parseMetadata(body.view.private_metadata || "{}");
    const { wtnb, open } = readCheckboxes(body.view.state?.values ?? {});
    const saved = captureCheckboxes(state, wtnb, open);
    await client.views.update({
        view_id: body.view.id,
        view: buildView(setSport(saved, body.actions[0].selected_option.value)),
    });
});

handler.addViewSubmissionHandler(CALLBACK_ID, async ({ body, view, client }) => {
    const state = parseMetadata(view.private_metadata || "{}");
    const { wtnb, open } = readCheckboxes(view.state?.values ?? {});
    const final = captureCheckboxes(state, wtnb, open);
    const leagues = stateToLeagues(final);
    console.log("[get_league_selections] submit:", JSON.stringify(leagues, null, 2));

    // deno-lint-ignore no-explicit-any
    const execId = (body as any).function_data?.execution_id;
    if (execId) {
        await client.functions.completeSuccess({
            function_execution_id: execId,
            outputs: { selected_leagues_json: JSON.stringify(leagues) },
        });
    }
});

export default handler;
