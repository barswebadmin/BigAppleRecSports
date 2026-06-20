/** League-picker modal used by the waitlist workflow's first step. Single
 *  source of truth for the league dropdown options and the block/action id
 *  contract — the handler scans submitted state via `leagueValueFromView`. */

import {
    context,
    input,
    type Option,
    section,
    staticSelect,
    toOptions,
} from "../../shared/slack/blocks.ts";
import { modal, type SlackView } from "../../shared/slack/message.ts";
import { hyperlink } from "../../shared/slack/mrkdwn.ts";
import { capitalize } from "../../shared/text/strings.ts";
import { compareWeekday, CURRENT_LEAGUES } from "../../domain/league/catalog.ts";
import { formatDivision } from "../../domain/league/format.ts";
import { buildLeagueKey } from "../../domain/league/identity.ts";

const LEAGUE_BLOCK_ID = "league_block";
const LEAGUE_ACTION_ID = "league_select";

/** Built once at module load — `CURRENT_LEAGUES` is static for the season.
 *  Sort: sport (A→Z) → weekday (Mon→Sun, not alphabetical) → division
 *  reverse-alphabetical (wtnb before open). */
const LEAGUE_OPTIONS: Option[] = toOptions(
    CURRENT_LEAGUES
        .slice()
        .sort((a, b) =>
            a.sport.localeCompare(b.sport) ||
            compareWeekday(a.day, b.day) ||
            b.division.localeCompare(a.division)
        )
        .map((lg) => ({
            label: `${capitalize(lg.sport)} - ${capitalize(lg.day)} - ${
                formatDivision(lg.division, "label")
            } Division`,
            value: buildLeagueKey(lg.sport, lg.day, lg.division),
        })),
);

/** Pre-select a league when the channel maps to one (per-channel league mapping
 *  in `catalog.ts`). Returns undefined when no mapping exists or the league
 *  value isn't in the current option list. */
export function findInitialLeagueOption(value: string | undefined): Option | undefined {
    return value ? LEAGUE_OPTIONS.find((o) => o.value === value) : undefined;
}

/** Read the selected league key from a submitted view's `state.values`. */
export function leagueValueFromView(
    values: Record<string, Record<string, { selected_option?: { value: string } }>>,
): string {
    return values[LEAGUE_BLOCK_ID]?.[LEAGUE_ACTION_ID]?.selected_option?.value ?? "";
}

export function buildLeagueSelectModal(args: {
    callbackId: string;
    sheetUrl: string;
    initial?: Option;
}): SlackView {
    return modal({
        callbackId: args.callbackId,
        title: "Select a league",
        submitLabel: "Next",
        closeLabel: "Cancel",
        blocks: [
            section(
                `Select from the dropdown to see waitlist for a league and click *Next* to fetch the ${
                    hyperlink("Google Sheet", args.sheetUrl)
                } and see the current waitlist for that league`,
            ),
            context(
                "(This workflow sets the Status column when processing, so this filters to rows where Status is empty)",
            ),
            input({
                blockId: LEAGUE_BLOCK_ID,
                label: "League",
                element: staticSelect({
                    actionId: LEAGUE_ACTION_ID,
                    placeholder: "Select a league...",
                    options: LEAGUE_OPTIONS,
                    initial: args.initial,
                }),
            }),
        ],
    });
}
