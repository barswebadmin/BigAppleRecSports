/**
 * League-selection state machine for the orders-export modal.
 * Tracks per-(year|season|sport) day checkboxes so selections survive
 * dropdown changes, and flattens to a league list on submit.
 */

import { CURRENT_SEASON, CURRENT_YEAR } from "../../config.ts";
import type { Season } from "../../config.ts";

type Day = "sunday" | "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday";
type Division = "wtnb" | "open";
type DivisionDays = Record<Division, Day[]>;

export interface LeagueSelectionState {
    year: number;
    season: Season;
    sport: string;
    selections: Record<string, DivisionDays>;
}

export const selectionKey = (state: LeagueSelectionState): string =>
    `${state.year}|${state.season}|${state.sport}`;

export const currentDays = (state: LeagueSelectionState): DivisionDays =>
    state.selections[selectionKey(state)] ?? { wtnb: [], open: [] };

export const getInitialState = (): LeagueSelectionState => ({
    year: CURRENT_YEAR,
    season: CURRENT_SEASON as Season,
    sport: "kickball",
    selections: {},
});

/** Merge the currently visible checkboxes into selections for the active combo. */
export function captureCheckboxes(
    state: LeagueSelectionState,
    wtnbDays: string[],
    openDays: string[],
): LeagueSelectionState {
    const key = selectionKey(state);
    return {
        ...state,
        selections: {
            ...state.selections,
            [key]: { wtnb: wtnbDays as Day[], open: openDays as Day[] },
        },
    };
}

export const setSport = (state: LeagueSelectionState, sport: string): LeagueSelectionState => ({
    ...state,
    sport,
});

export const setYear = (state: LeagueSelectionState, year: number): LeagueSelectionState => ({
    ...state,
    year,
});

export const setSeason = (state: LeagueSelectionState, season: Season): LeagueSelectionState => ({
    ...state,
    season,
});

export const parseMetadata = (raw: string): LeagueSelectionState =>
    JSON.parse(raw) as LeagueSelectionState;

export const serializeMetadata = (state: LeagueSelectionState): string => JSON.stringify(state);

export interface LeagueSelection {
    year: number;
    season: string;
    sport: string;
    day: string;
    division: string;
}

export function stateToLeagues(state: LeagueSelectionState): LeagueSelection[] {
    const leagues: LeagueSelection[] = [];
    for (const [key, days] of Object.entries(state.selections)) {
        const [yearStr, season, sport] = key.split("|");
        for (const division of ["wtnb", "open"] as Division[]) {
            for (const day of days[division]) {
                leagues.push({ year: parseInt(yearStr, 10), season, sport, day, division });
            }
        }
    }
    return leagues;
}
