/** League-picker modal for the orders-export workflow. The state machine lives
 *  in `domain/league/selection_state.ts`; this file owns the modal view shape,
 *  the option catalogs, and the block/action id contract — the handler reads
 *  submitted state via `readCheckboxes`. */

import {
    checkboxes,
    divider,
    input,
    type Option,
    staticSelect,
    toOptions,
} from "../../shared/slack/blocks.ts";
import { modal, type SlackView } from "../../shared/slack/message.ts";
import { capitalize } from "../../shared/text/strings.ts";
import { ALL_SEASONS } from "../../domain/league/types.ts";
import { getDaysForSport, SPORTS } from "../../domain/league/catalog.ts";
import { currentDays, type LeagueSelectionState, serializeMetadata } from "./selection_state.ts";

// ── Block/action id contract ──────────────────────────────────────────────

export const CALLBACK_ID = "shopify_orders_modal";

const YEAR_BLOCK_ID = "year_block";
const SEASON_BLOCK_ID = "season_block";
const SPORT_BLOCK_ID = "sport_block";

export const YEAR_ACTION_ID = "year_select";
export const SEASON_ACTION_ID = "season_select";
export const SPORT_ACTION_ID = "sport_select";

const WTNB_DAYS_BLOCK_PREFIX = "wtnb_days_";
const OPEN_DAYS_BLOCK_PREFIX = "open_days_";
const WTNB_DAYS_ACTION_ID = "wtnb_days_select";
const OPEN_DAYS_ACTION_ID = "open_days_select";

// ── Static option catalogs + lookups ──────────────────────────────────────

const YEAR_OPTIONS: Option[] = toOptions(
    ["2022", "2023", "2024", "2025", "2026"].map((y) => ({ label: y, value: y })),
);
const SEASON_OPTIONS: Option[] = toOptions(
    ALL_SEASONS.map((s) => ({ label: capitalize(s), value: s })),
);
const SPORT_OPTIONS: Option[] = toOptions(SPORTS.map((s) => ({ label: capitalize(s), value: s })));

// Built once at module load — every `initial:` lookup is `MAP.get(value)` instead
// of a linear `.find` per render.
const YEAR_BY_VALUE = new Map(YEAR_OPTIONS.map((o) => [o.value, o]));
const SEASON_BY_VALUE = new Map(SEASON_OPTIONS.map((o) => [o.value, o]));
const SPORT_BY_VALUE = new Map(SPORT_OPTIONS.map((o) => [o.value, o]));

function dayOptions(days: string[]): Option[] {
    return toOptions(days.map((d) => ({ label: capitalize(d), value: d })));
}

// ── View-state readers ────────────────────────────────────────────────────

type ViewValues = Record<
    string,
    Record<string, { selected_options?: { value: string }[] }>
>;

/** Pull the visible page's wtnb/open day ticks out of `view.state.values`.
 *  Block ids embed the current year|season|sport combo (so the keys change
 *  every render); the action id is stable, so we prefix-match on the block id. */
function pickDays(values: ViewValues, blockPrefix: string, actionId: string): string[] {
    const blockId = Object.keys(values).find((k) => k.startsWith(blockPrefix));
    return (blockId ? (values[blockId]?.[actionId]?.selected_options ?? []) : []).map(
        (o) => o.value,
    );
}

export function readCheckboxes(values: ViewValues): { wtnb: string[]; open: string[] } {
    return {
        wtnb: pickDays(values, WTNB_DAYS_BLOCK_PREFIX, WTNB_DAYS_ACTION_ID),
        open: pickDays(values, OPEN_DAYS_BLOCK_PREFIX, OPEN_DAYS_ACTION_ID),
    };
}

// ── Modal builder ─────────────────────────────────────────────────────────

export function buildOrdersExportModal(state: LeagueSelectionState): SlackView {
    const stored = currentDays(state);
    const available = getDaysForSport(state.sport);
    const wtnbOpts = dayOptions(available.wtnb);
    const openOpts = dayOptions(available.open);
    const wtnbSelected = new Set(stored.wtnb);
    const openSelected = new Set(stored.open);
    const wtnbInitial = wtnbOpts.filter((o) => wtnbSelected.has(o.value as never));
    const openInitial = openOpts.filter((o) => openSelected.has(o.value as never));
    const comboSuffix = `${state.year}_${state.season}_${state.sport}`;

    return modal({
        callbackId: CALLBACK_ID,
        title: "Select league(s)",
        submitLabel: "Done",
        metadata: serializeMetadata(state),
        blocks: [
            input({
                blockId: YEAR_BLOCK_ID,
                label: "Year",
                dispatchAction: true,
                element: staticSelect({
                    actionId: YEAR_ACTION_ID,
                    placeholder: "Year",
                    options: YEAR_OPTIONS,
                    initial: YEAR_BY_VALUE.get(String(state.year)),
                }),
            }),
            input({
                blockId: SEASON_BLOCK_ID,
                label: "Season",
                dispatchAction: true,
                element: staticSelect({
                    actionId: SEASON_ACTION_ID,
                    placeholder: "Season",
                    options: SEASON_OPTIONS,
                    initial: SEASON_BY_VALUE.get(state.season),
                }),
            }),
            input({
                blockId: SPORT_BLOCK_ID,
                label: "Sport",
                dispatchAction: true,
                element: staticSelect({
                    actionId: SPORT_ACTION_ID,
                    placeholder: "Sport",
                    options: SPORT_OPTIONS,
                    initial: SPORT_BY_VALUE.get(state.sport),
                }),
            }),
            divider(),
            ...(wtnbOpts.length
                ? [input({
                    blockId: `${WTNB_DAYS_BLOCK_PREFIX}${comboSuffix}`,
                    label: "WTNB Division",
                    optional: true,
                    element: checkboxes({
                        actionId: WTNB_DAYS_ACTION_ID,
                        options: wtnbOpts,
                        initial: wtnbInitial.length ? wtnbInitial : undefined,
                    }),
                })]
                : []),
            divider(),
            ...(openOpts.length
                ? [input({
                    blockId: `${OPEN_DAYS_BLOCK_PREFIX}${comboSuffix}`,
                    label: "Open Division",
                    optional: true,
                    element: checkboxes({
                        actionId: OPEN_DAYS_ACTION_ID,
                        options: openOpts,
                        initial: openInitial.length ? openInitial : undefined,
                    }),
                })]
                : []),
        ],
    });
}
