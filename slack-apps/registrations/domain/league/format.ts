/** League-shaped formatters: division labels, product handle, tags, sport
 *  leadership email, league display labels. Three division formatters by
 *  intent — see each JSDoc. */

import type { League } from "./types.ts";
import { BARS_URLS, ORG_DOMAIN } from "../../config/store.ts";
import { capitalize } from "../../shared/text/strings.ts";

export function buildLoginUrl(productHandle: string): string {
    return `${BARS_URLS.website}/customer_authentication/login?return_to=%2Fproducts%2F${productHandle}`;
}

/** Full division phrase for prose (email bodies). `WTNB+ Division` / `Open Division`. */
export function formatDivision(division: string): string {
    return division.toLowerCase() === "wtnb" ? "WTNB+ Division" : "Open Division";
}

/** Medium label for Slack mrkdwn (modal titles, list rows). `WTNB+` / `Open`. */
export function formatDivisionLabel(division: string): string {
    return division.toLowerCase() === "wtnb" ? "WTNB+" : "Open";
}

/** Short label for compact UI (short league labels, table cells). `WTNB` / `Open`. */
export function formatDivisionShort(division: string): string {
    return division.toLowerCase() === "wtnb" ? "WTNB" : "Open";
}

export function formatProductHandle(league: League): string {
    return `${league.year}-${league.season}-${league.sport}-${league.day}-${league.division}div`;
}

export function formatSportLeadershipEmailAddress(league: League): string {
    return `${league.sport}.${league.day}.${league.division}@${ORG_DOMAIN}`;
}

export function formatSportLeadershipEmailSenderName(league: League): string {
    return `Big Apple ${capitalize(league.sport)}`;
}

export function formatLeagueLabelShort(league: League): string {
    return `${capitalize(league.day)} ${formatDivisionShort(league.division)} ${
        capitalize(league.sport)
    }`;
}
