/** Waitlist text formatters and action-result rendering.
 *
 *  TOP: waitlist-specific text composition (entry titles, context lines,
 *  outcome bullet — pure string output, no UI building, no I/O).
 *  BOTTOM: generic helpers (date reformatter) used by the top but not tied
 *  to waitlist semantics. */

import type { ActionResult } from "../../domain/waitlist/action_result.ts";
import type { EmailLookupEntry, WaitlistEntry } from "../../domain/waitlist/types.ts";
import { otherWaitlistsFor } from "../../domain/waitlist/lookups.ts";
import { formatLeagueLabelShort } from "../../domain/league/format.ts";
import { hyperlink } from "../../shared/slack/mrkdwn.ts";

type AdmitNote = "emailed" | "email_failed" | "tag_only";

type WaitlistActionOutcome =
    | { kind: "shopify_failed"; error?: string }
    | { kind: "removed" }
    | { kind: "admitted"; note: AdmitNote };

function classifyWaitlistAction(r: ActionResult): WaitlistActionOutcome {
    if (!r.shopifyOk) return { kind: "shopify_failed", error: r.shopifyError };
    if (r.type === "remove") return { kind: "removed" };
    if (!r.emailOk) return { kind: "admitted", note: "email_failed" };
    if (r.emailed) return { kind: "admitted", note: "emailed" };
    return { kind: "admitted", note: "tag_only" };
}

/** Suffix shown for each admitted player, keyed by the email outcome. */
const ADMIT_NOTE: Record<AdmitNote, string> = {
    emailed: "emailed",
    email_failed: "tagged, :warning: email failed",
    tag_only: "tagged, no email",
};

/** Bold name line for a waitlist entry: `#{position}: *First Last* (pronouns)`. */
export function formatEntryTitle(entry: WaitlistEntry): string {
    const pronouns = entry.pronouns ? ` (${entry.pronouns})` : "";
    return `#${entry.position}: *${entry.firstName} ${entry.lastName}*${pronouns}`;
}

/** "Also waitlisted for X, Y, Z" footnote built from the lookup result. */
function formatOtherWaitlistsLine(others: EmailLookupEntry[]): string {
    const parts = others.map((e) =>
        `${formatLeagueLabelShort(e.entry.league)} (#${e.entry.position}/${e.total})`
    );
    return `_*Note: also waitlisted for ${parts.join(", ")}*_`;
}

/** Small lines shown beneath an entry: submission time and any other waitlists
 *  the same email appears on. Domain query (`otherWaitlistsFor`) returns the
 *  structured list; this function shapes it into context lines. */
export function formatEntryContextLines(
    entry: WaitlistEntry,
    currentLeagueKey: string,
    byEmail: Record<string, EmailLookupEntry[]>,
): string[] {
    const lines = [`Submitted: ${formatSubmittedTimestamp(entry.createdAt)}`];
    const others = otherWaitlistsFor(entry.emailAddress, currentLeagueKey, byEmail);
    if (others.length > 0) lines.push(formatOtherWaitlistsLine(others));
    return lines;
}

/** Read-only label for an already-contacted entry (no dropdown shown). */
export function formatReadOnlyEntry(
    entry: WaitlistEntry,
    currentLeagueKey: string,
    byEmail: Record<string, EmailLookupEntry[]>,
): string {
    const lines = [
        formatEntryTitle(entry),
        ...formatEntryContextLines(entry, currentLeagueKey, byEmail),
    ];
    if (entry.status) lines.push(`:white_check_mark: _${entry.status}_`);
    return lines.join("\n");
}

/** One bullet per processed player: name (linked to their Shopify customer when
 *  known) plus a terse outcome. Classification lives in
 *  `domain/waitlist/outcomes.ts`; this function only renders the classified
 *  outcome via a dispatch on the discriminant. */
export function formatActionBullet(r: ActionResult): string {
    const namePart = r.customerAdminUrl ? hyperlink(r.name, r.customerAdminUrl) : `*${r.name}*`;
    const outcome = classifyWaitlistAction(r);
    switch (outcome.kind) {
        case "shopify_failed":
            return `${namePart} — :x: Shopify update failed${
                outcome.error ? ` (${outcome.error})` : ""
            }; update the tag manually`;
        case "removed":
            return `${namePart} — removed from the waitlist`;
        case "admitted":
            return `${namePart} — pulled off the waitlist _(${ADMIT_NOTE[outcome.note]})_`;
    }
}

// ============================================================================

// ============================================================================

const SHORT_MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
];

/** Reformat a sheet timestamp (`M/D/YYYY H:MM:SS`, 24h) to `Mon D, h:mm AM/PM`
 *  (e.g. `Jun 13, 11:45 PM`). Parsed by regex (not `Date`) to avoid timezone
 *  shifts. Falls back to the raw string if it doesn't match. */
export function formatSubmittedTimestamp(raw: string): string {
    const m = /^(\d{1,2})\/(\d{1,2})\/\d{2,4}\s+(\d{1,2}):(\d{2})/.exec(raw.trim());
    if (!m) return raw;
    const month = SHORT_MONTHS[Number(m[1]) - 1] ?? m[1];
    const day = Number(m[2]);
    const hour24 = Number(m[3]);
    const minute = m[4];
    const ampm = hour24 >= 12 ? "PM" : "AM";
    const hour12 = hour24 % 12 || 12;
    return `${month} ${day}, ${hour12}:${minute} ${ampm}`;
}
