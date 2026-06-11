/**
 * Waitlist display helpers — pure domain formatting, no Slack or I/O imports.
 */

import type { League } from "../../types/league.ts";
import type { EmailLookupEntry, WaitlistEntry } from "./handlers/waitlist_entry_types.ts";
import {
    buildLoginUrl,
    capitalize,
    formatDivision,
    formatProductHandle,
    normalizePhone,
} from "../../utils/formatters.ts";

/** Tracks per-entry success/failure across processing steps. Posted as the summary message. */
export interface ActionResult {
    rowNumber: number;
    type: "admit" | "remove";
    name: string;
    firstName: string;
    email: string;
    phone?: string;
    league?: League;
    shopifyOk: boolean;
    emailOk: boolean;
    shopifyError?: string;
    emailError?: string;
}

/**
 * Modal label for a waitlist entry: name, gender/pronouns, submission date,
 * status, and positions on any other league waitlists (from the byEmail lookup).
 */
export function formatEntryLabel(
    entry: WaitlistEntry,
    currentLeagueKey: string,
    byEmail: Record<string, EmailLookupEntry[]>,
): string {
    const gp = [entry.gender, entry.pronouns].filter(Boolean).join(", ");
    const nameLine = `:bust_in_silhouette: *${entry.firstName} ${entry.lastName}*${
        gp ? ` (${gp})` : ""
    }`;
    const lines = [nameLine, `Submitted on ${entry.createdAt}`];
    if (entry.status) lines.push(`Status: ${entry.status}`);

    const others = (byEmail[entry.emailAddress.toLowerCase()] ?? []).filter(
        (e) => e.leagueKey !== currentLeagueKey,
    );
    if (others.length > 0) {
        const otherLeagues = others
            .map((e) => {
                const [sport, day, div] = e.leagueKey.split("|");
                const label = `${capitalize(day)} ${div === "wtnb" ? "WTNB+" : "Open"} ${
                    capitalize(sport)
                }`;
                return `${label} (#${e.entry.position}/${e.total})`;
            })
            .join(", ");
        lines.push(`:information_source: Also on other waitlists: ${otherLeagues}`);
    }
    return lines.join("\n");
}

/** One line of the channel summary message, with failure warnings and an SMS suggestion. */
export function formatActionResult(r: ActionResult): string {
    const verb = r.type === "admit" ? "Admitted" : "Removed";
    const allOk = r.shopifyOk && r.emailOk;
    const icon = allOk ? "\u2705" : "\u26A0\uFE0F";
    let line = `${icon} ${verb} *${r.name}* (${r.email})`;

    if (r.type === "admit" && r.emailOk) {
        line += ` \u2014 emailed`;
        const smsPhone = r.phone ? normalizePhone(r.phone) : null;
        if (smsPhone && r.league) {
            const lg = r.league;
            const leagueLabel = `${capitalize(lg.day)} ${capitalize(lg.sport)} (${
                formatDivision(lg.division)
            })`;
            const loginUrl = buildLoginUrl(formatProductHandle(lg));
            const smsBody = encodeURIComponent(
                `Hi ${r.firstName}, we had a spot open up in ${leagueLabel}. Attaching a link to login and register directly (also sent to your email). If you're no longer interested, let us know so we can offer it to someone else! ${loginUrl}`,
            );
            line +=
                ` (Phone Number was provided - consider <sms://${smsPhone}?&body=${smsBody}|texting them as well for faster processing>)`;
        }
    }

    if (!r.shopifyOk) {
        line +=
            `\n\u274C Shopify tag update could not be completed. Please update manually and reach out to the player.`;
    }
    if (!r.emailOk && r.shopifyOk) {
        line += `\n\u26A0\uFE0F Email could not be sent${
            r.emailError ? `: ${r.emailError}` : ""
        }. Please reach out manually.`;
    }
    return line;
}
