/**
 * Waitlist display helpers — pure domain formatting, no Slack or I/O imports.
 */

import type { League } from "../../types/league.ts";
import { parseLeagueKey } from "./league_key.ts";
import type { EmailLookupEntry, WaitlistEntry } from "./handlers/waitlist_entry_types.ts";
import { capitalize, formatDivisionLabel, formatLeagueLabelShort } from "../../utils/formatters.ts";
import { SLACK_LINK_TEXT, slackLink, tagSlackMember } from "../../config.ts";

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
    /** True only when a notification email was actually sent (the per-row box was ticked). */
    emailed: boolean;
    shopifyError?: string;
    emailError?: string;
    /** Links resolved during processing, used to build the channel message bullets. */
    customerAdminUrl?: string;
    productUrl?: string;
}

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

/**
 * Reformat a sheet timestamp (`M/D/YYYY H:MM:SS`, 24h) to `Mon D, h:mm AM/PM`
 * (e.g. `Jun 13, 11:45 PM`). Parsed by regex (not `Date`) to avoid timezone
 * shifts. Falls back to the raw string if it doesn't match.
 */
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

/** Bold name line for a waitlist entry: `#{position}: *First Last* (pronouns)`. */
export function formatEntryTitle(entry: WaitlistEntry): string {
    const pronouns = entry.pronouns ? ` (${entry.pronouns})` : "";
    return `#${entry.position}: *${entry.firstName} ${entry.lastName}*${pronouns}`;
}

/**
 * Small lines shown beneath an entry: submission time and any other waitlists
 * the same email appears on (from the byEmail lookup). Rendered as a context
 * block by the modal, so they read as de-emphasized footnotes.
 */
export function formatEntryContextLines(
    entry: WaitlistEntry,
    currentLeagueKey: string,
    byEmail: Record<string, EmailLookupEntry[]>,
): string[] {
    const lines = [`Submitted: ${formatSubmittedTimestamp(entry.createdAt)}`];

    const others = (byEmail[entry.emailAddress.toLowerCase()] ?? []).filter(
        (e) => e.leagueKey !== currentLeagueKey,
    );
    if (others.length > 0) {
        const otherLeagues = others
            .map((e) => {
                const league = parseLeagueKey(e.leagueKey);
                return `${
                    formatLeagueLabelShort(league as League)
                } (#${e.entry.position}/${e.total})`;
            })
            .join(", ");
        lines.push(`_*Note: also waitlisted for ${otherLeagues}*_`);
    }
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

/**
 * One bullet per processed player: name (linked to their Shopify customer when
 * known) plus a terse outcome. Intentionally minimal — the dry-run preview is
 * where full request detail belongs.
 */
export function formatActionBullet(r: ActionResult): string {
    const namePart = r.customerAdminUrl ? slackLink(r.name, r.customerAdminUrl) : `*${r.name}*`;
    if (!r.shopifyOk) {
        return `${namePart} — :x: Shopify update failed${
            r.shopifyError ? ` (${r.shopifyError})` : ""
        }; update the tag manually`;
    }
    if (r.type === "remove") return `${namePart} — removed from the waitlist`;
    const note = !r.emailOk
        ? "tagged, :warning: email failed"
        : r.emailed
        ? "emailed"
        : "tagged, no email";
    return `${namePart} — pulled off the waitlist _(${note})_`;
}

/**
 * Confirmation modal pushed when the reviewer clicks Submit. Lists only the
 * first/last names being admitted/removed so they can verify before the
 * (irreversible) run. One builder for both modes — only the title and a context
 * note differ; submitting runs the exact same downstream logic (dry-run preview
 * or real execution), so there's no separate confirm path to maintain.
 */
export function buildWaitlistConfirmModal(args: {
    callbackId: string;
    admitNames: string[];
    removeNames: string[];
    dry: boolean;
    metadata: string;
}): Record<string, unknown> {
    const blocks: Record<string, unknown>[] = [
        { type: "section", text: { type: "mrkdwn", text: "*Please confirm these changes:*" } },
    ];

    const group = (label: string, names: string[]) => {
        if (names.length === 0) return;
        const bullets = names.map((n) => `•  ${n}`).join("\n");
        blocks.push({
            type: "section",
            text: { type: "mrkdwn", text: `*${label}* (${names.length})\n${bullets}` },
        });
    };
    group("Admit", args.admitNames);
    group("Remove", args.removeNames);

    if (args.dry) {
        blocks.push({
            type: "context",
            elements: [{
                type: "mrkdwn",
                text:
                    ":test_tube: *DRY RUN* — nothing will be sent. Submitting posts a preview of the exact requests.",
            }],
        });
    }

    return {
        type: "modal",
        callback_id: args.callbackId,
        private_metadata: args.metadata,
        title: { type: "plain_text", text: args.dry ? "Confirm (DRY RUN)" : "Confirm changes" },
        submit: { type: "plain_text", text: "Confirm" },
        close: { type: "plain_text", text: "Cancel" },
        blocks,
    };
}

/**
 * One consolidated channel message for a real (non-dry-run) run. The workflow
 * handles a single league at a time, so the league link, processor, sheet link,
 * and remaining count appear once; each processed player is a bullet.
 */
export function buildWaitlistResultMessage(
    results: ActionResult[],
    opts: { processedBy?: string; remaining: number; sheetUrl: string },
): { text: string; blocks: Record<string, unknown>[] } {
    const lg = results[0]?.league;
    const leagueText = lg
        ? `${capitalize(lg.day)} ${capitalize(lg.sport)} (${formatDivisionLabel(lg.division)})`
        : "this league";
    const productUrl = results[0]?.productUrl;
    const leaguePart = productUrl ? slackLink(leagueText, productUrl) : `*${leagueText}*`;

    const headerLines = [`*Waitlist updated — ${leaguePart}*`];
    const meta: string[] = [];
    if (opts.processedBy) meta.push(tagSlackMember(opts.processedBy));
    meta.push(`${Math.max(0, opts.remaining)} still on the waitlist`);
    headerLines.push(meta.join("  ·  "));
    headerLines.push(slackLink(SLACK_LINK_TEXT.googleSheets, opts.sheetUrl));

    const bulletLines = results.map((r) => `•  ${formatActionBullet(r)}`);

    return {
        text: [...headerLines, "", ...bulletLines].join("\n"),
        blocks: [
            { type: "section", text: { type: "mrkdwn", text: headerLines.join("\n") } },
            { type: "section", text: { type: "mrkdwn", text: bulletLines.join("\n") } },
        ],
    };
}
