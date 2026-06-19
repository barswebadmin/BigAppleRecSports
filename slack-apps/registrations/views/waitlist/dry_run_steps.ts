/** Build dry-run preview `DryRunStep`s for a planned `RowProcessing`. Pure UI
 *  — reads the planner's structured outcome data (no embedded UI text) and
 *  shapes it into renderer-ready steps. */

import type { EmailMessage } from "../../shared/google/email_message.ts";
import type { DryRunStep } from "../../shared/slack/dry_run.ts";
import type { RowProcessing } from "../../domain/waitlist/row_planning.ts";
import { WAITLIST_TAB } from "../../domain/waitlist/sheet.ts";
import { formatEmailDryRunNote, formatShopifyDryRunNote } from "./dry_run_text.ts";

/** Shopify step from a row's plan: full request bytes when the planner built
 *  one, otherwise a fallback note describing why no mutation will happen. */
export function buildShopifyDryRunStep(p: RowProcessing): DryRunStep {
    const previousTags = p.tagPlan?.existing?.tags ?? [];
    const req = p.tagPlan?.request;
    if (req) {
        return {
            kind: "shopify_customer",
            previousTags,
            request: { method: req.method, url: req.url, headers: req.headers },
            body: req.body,
        };
    }
    const note = p.shopifyOutcome ? formatShopifyDryRunNote(p.shopifyOutcome) : "";
    return { kind: "shopify_customer", previousTags, request: null, note };
}

/** Email step: full request bytes when an email is going out, a brief note
 *  when the planner skipped it, or `null` when the skip needs no display. */
export function buildEmailDryRunStep(p: RowProcessing): DryRunStep | null {
    if (p.emailRequest && p.emailMessage) {
        const m = p.emailMessage;
        return {
            kind: "email",
            request: {
                method: p.emailRequest.method,
                url: p.emailRequest.url,
                headers: p.emailRequest.headers,
            },
            to: m.to,
            senderEmail: m.sendAs.emailAddress,
            subject: m.subject,
            replyTo: m.replyTo,
            cc: m.cc,
            copy: buildEmailCopy(m),
        };
    }
    const note = p.emailOutcome ? formatEmailDryRunNote(p.emailOutcome) : null;
    return note ? { kind: "note", title: "Send email notification", note } : null;
}

/** Sheet step: the row write the downstream `UpdateWaitlistSpreadsheet` step
 *  would perform. */
export function buildSheetDryRunStep(p: RowProcessing, statusCol: string): DryRunStep {
    return {
        kind: "sheet",
        sheetUrl: p.sheetUrl,
        tabName: WAITLIST_TAB.name,
        rowNumber: p.result.rowNumber,
        columnName: `Status (${statusCol}${p.result.rowNumber})`,
        existingValue: p.entry?.status?.trim() || "(empty)",
        insertedValue: p.insertedStatus,
    };
}

/** Compose all dry-run steps for a single row in display order. */
export function toDryRunSteps(p: RowProcessing, statusCol: string): DryRunStep[] {
    const admitSteps = p.type === "admit"
        ? [buildShopifyDryRunStep(p), buildEmailDryRunStep(p)].filter(
            (s): s is DryRunStep => s !== null,
        )
        : [];
    return [...admitSteps, buildSheetDryRunStep(p, statusCol)];
}

/** Per-row header line for the dry-run preview message. */
export function formatDryRunHeader(p: RowProcessing): string {
    const verb = p.type === "admit" ? "Admit" : "Remove";
    const email = p.result.email || "no email";
    const box = p.shouldEmail ? "ON" : "off";
    return `:test_tube: *DRY RUN* — would *${verb}* ${p.result.name} (${email}) · email box: ${box}`;
}

/** Fallback label for a preview row when the primary message can't render. */
export function formatRowLabel(p: RowProcessing): string {
    return `${p.result.name} (${p.result.email || "no email"})`;
}

// ============================================================================

// ============================================================================

/** Render an HTML email body part as readable plain text for dry-run display. */
function htmlToText(html: string): string {
    return html
        .replace(/<a\s+href="([^"]*)"[^>]*>(.*?)<\/a>/gi, "$2 ($1)")
        .replace(/<\/?(b|strong|i|em)>/gi, "")
        .replace(/<br\s*\/?>/gi, "\n")
        .replace(/&gt;/g, ">")
        .replace(/&lt;/g, "<")
        .replace(/&amp;/g, "&");
}

/** Concatenate an email message's HTML body parts as plain text for display. */
function buildEmailCopy(m: EmailMessage): string {
    return m.htmlBodyParts.map(htmlToText).join("\n\n");
}
