import type { League } from "./types.ts";
import { ORG_DOMAIN } from "../../config/store.ts";
import { capitalize } from "../../shared/text/strings.ts";

const DIVISION_LABELS = {
    prose: { wtnb: "WTNB+ Division", open: "Open Division" },
    label: { wtnb: "WTNB+", open: "Open" },
    short: { wtnb: "WTNB", open: "Open" },
} as const;

export type DivisionStyle = keyof typeof DIVISION_LABELS;

/** Format a division string. `prose` = "WTNB+ Division" / "Open Division";
 *  `label` = "WTNB+" / "Open"; `short` = "WTNB" / "Open". */
export function formatDivision(division: string, style: DivisionStyle): string {
    return DIVISION_LABELS[style][division.toLowerCase() === "wtnb" ? "wtnb" : "open"];
}

export function formatProductHandle(league: League): string {
    return `${league.year}-${league.season}-${league.sport}-${league.day}-${league.division}div`;
}

export function formatSportLeadershipEmailAddress(league: League): string {
    return `${league.sport}.${league.day}.${league.division}@${ORG_DOMAIN}`;
}

export function formatLeagueLabelShort(league: League): string {
    return `${capitalize(league.day)} ${formatDivision(league.division, "short")} ${
        capitalize(league.sport)
    }`;
}
