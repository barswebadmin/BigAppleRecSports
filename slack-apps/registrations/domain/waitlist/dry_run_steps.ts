/** Build dry-run preview steps from a planned `RowProcessing`. Pure — each
 *  builder describes what *would* happen; nothing executes here. */

import type { EmailMessage } from "../../shared/google/email_message.ts";
import type { DryRunStep } from "../../shared/slack/dry_run.ts";
import { WAITLIST_TAB } from "./sheet.ts";
import type { RowProcessing } from "./row_planning.ts";

/** Render an HTML email body part as readable plain text for dry-run display. */
export function htmlToText(html: string): string {
    return html
        .replace(/<a\s+href="([^"]*)"[^>]*>(.*?)<\/a>/gi, "$2 ($1)")
        .replace(/<\/?(b|strong|i|em)>/gi, "")
        .replace(/<br\s*\/?>/gi, "\n")
        .replace(/&gt;/g, ">")
        .replace(/&lt;/g, "<")
        .replace(/&amp;/g, "&");
}

export function buildEmailCopy(m: EmailMessage): string {
    return m.htmlBodyParts.map(htmlToText).join("\n\n");
}

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
    return {
        kind: "shopify_customer",
        previousTags,
        request: null,
        note: p.notes[0],
    };
}

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
    const skip = p.notes.find((n) => n.startsWith("Email"));
    return skip ? { kind: "note", title: "Send email notification", note: skip } : null;
}

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
    const steps: DryRunStep[] = [];
    if (p.type === "admit") {
        steps.push(buildShopifyDryRunStep(p));
        const emailStep = buildEmailDryRunStep(p);
        if (emailStep) steps.push(emailStep);
    }
    steps.push(buildSheetDryRunStep(p, statusCol));
    return steps;
}

export function formatDryRunHeader(p: RowProcessing): string {
    const verb = p.type === "admit" ? "Admit" : "Remove";
    const email = p.result.email || "no email";
    const box = p.shouldEmail ? "ON" : "off";
    return `:test_tube: *DRY RUN* — would *${verb}* ${p.result.name} (${email}) · email box: ${box}`;
}

export function formatRowLabel(p: RowProcessing): string {
    return `${p.result.name} (${p.result.email || "no email"})`;
}
