import { CURRENT_SEASON, CURRENT_YEAR } from "../../config/season.ts";
import type { League } from "./types.ts";

// Key is sport|day|division only — season/year live in CURRENT_SEASON/CURRENT_YEAR.
export function buildLeagueKey(sport: string, day: string, division: string): string {
    const div = division.trim().slice(0, 4).toLowerCase();
    return `${sport.trim().toLowerCase()}|${day.trim().toLowerCase()}|${div}`;
}

export function formatLeagueKey(league: League): string {
    return buildLeagueKey(league.sport, league.day, league.division);
}

export function parseLeagueKey(key: string): { sport: string; day: string; division: string } {
    const [sport, day, division] = key.split("|");
    return { sport, day, division };
}

export function leagueFromKey(key: string): League {
    const { sport, day, division } = parseLeagueKey(key);
    return { year: CURRENT_YEAR, season: CURRENT_SEASON, sport, day, division };
}
