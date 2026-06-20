/** League catalog: derived query API over the raw league config.
 *  Single source of truth for channel → league mapping and product/variant ids. */

import { LEAGUE_ROWS } from "../../config/leagues.ts";
import type { LeagueRow } from "../../config/leagues.ts";
import type { LeagueConfig } from "./types.ts";
import { buildLeagueKey } from "./identity.ts";

export type { LeagueConfig } from "./types.ts";

// ── Weekday ordering ────────────────────────────────────────────────

const WEEKDAY_ORDER = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
];

export function compareWeekday(a: string, b: string): number {
    return WEEKDAY_ORDER.indexOf(a.toLowerCase()) - WEEKDAY_ORDER.indexOf(b.toLowerCase());
}

// ── Catalog ──────────────────────────────────────────────────────────

function rowToLeague(
    [channelId, sport, day, division, product_id, veteran, early, general, waitlist]: LeagueRow,
): LeagueConfig {
    return {
        channelId,
        sport,
        day,
        division,
        product_id,
        variant_ids: { veteran, early, general, waitlist },
    };
}

const LEAGUE_DATA: LeagueConfig[] = LEAGUE_ROWS.map(rowToLeague);

export const CURRENT_LEAGUES: LeagueConfig[] = LEAGUE_DATA;

export const SPORTS: string[] = [...new Set(LEAGUE_DATA.map((lg) => lg.sport))]
    .sort((a, b) => a.localeCompare(b));

const CHANNEL_TO_LEAGUE = new Map(
    LEAGUE_DATA.map((lg) => [lg.channelId, buildLeagueKey(lg.sport, lg.day, lg.division)]),
);

export function getDefaultLeagueForChannel(channelId: string): string | undefined {
    return CHANNEL_TO_LEAGUE.get(channelId);
}

export function getDaysForSport(sport: string): { wtnb: string[]; open: string[] } {
    const inSport = LEAGUE_DATA.filter((lg) => lg.sport === sport);
    const dedupedDays = (predicate: (lg: LeagueConfig) => boolean): string[] => [
        ...new Set(inSport.filter(predicate).map((lg) => lg.day)),
    ];
    return {
        wtnb: dedupedDays((lg) => lg.division === "wtnb"),
        open: dedupedDays((lg) => lg.division !== "wtnb"),
    };
}
