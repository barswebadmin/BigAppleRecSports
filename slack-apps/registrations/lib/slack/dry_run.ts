/**
 * Dry-run rendering: turn planned actions into Slack blocks that describe the
 * exact requests the real run would send (method/URL/headers with credentials
 * masked, request bodies, and decoded email/sheet details). No I/O.
 */

import { maskHeaders } from "../clients/prepared_request.ts";

type Block = Record<string, unknown>;

// Slack section text caps at 3000 chars; chunk long bodies under it. Cap the
// number of chunks per field so one request can't exceed Slack's 50-block /
// message-size limit (anything past the cap is truncated with a note).
const MAX_TEXT = 2900;
const MAX_CHUNKS = 8;

const section = (text: string): Block => ({ type: "section", text: { type: "mrkdwn", text } });
const heading = (text: string): Block => ({
    type: "header",
    text: { type: "plain_text", text: text.slice(0, 150), emoji: true },
});
const divider = (): Block => ({ type: "divider" });

function codeBlocks(content: string): Block[] {
    const blocks: Block[] = [];
    const limit = MAX_TEXT * MAX_CHUNKS;
    const shown = content.length > limit ? content.slice(0, limit) : content;
    for (let i = 0; i < shown.length; i += MAX_TEXT) {
        blocks.push(section("```" + shown.slice(i, i + MAX_TEXT) + "```"));
    }
    if (content.length > limit) {
        blocks.push({
            type: "context",
            elements: [{
                type: "mrkdwn",
                text: `_…truncated for display (${content.length.toLocaleString()} chars total)._`,
            }],
        });
    }
    return blocks;
}

/** The wire-level attributes of a request (headers are masked at render time). */
export interface RequestAttrs {
    method: string;
    url: string;
    headers: Record<string, string>;
}

export type DryRunStep =
    | {
        kind: "shopify_customer";
        previousTags: string[];
        request: RequestAttrs | null;
        body?: string;
        note?: string;
    }
    | {
        kind: "email";
        request: RequestAttrs;
        to: string;
        senderEmail: string;
        subject: string;
        replyTo?: string;
        cc?: string;
        copy: string;
    }
    | {
        kind: "sheet";
        sheetUrl: string;
        tabName: string;
        rowNumber: number;
        columnName: string;
        existingValue: string;
        insertedValue: string;
    }
    | { kind: "note"; title?: string; note: string };

function titlecase(s: string): string {
    return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

export interface Bullet {
    label: string;
    value: string;
}

/**
 * Render a bulleted list as `• *Label:* \`value\``, with every value inline-code
 * formatted. Optional bold heading line above the bullets. Reusable across all
 * dry-run sections.
 */
function bulletList(bullets: Bullet[], heading?: string): string {
    const lines = heading ? [`*${heading}*`] : [];
    for (const b of bullets) lines.push(`• *${b.label}:* \`${b.value}\``);
    return lines.join("\n");
}

/** "*Request*" heading + one bullet for method, URL, and each (masked) header. */
function requestBullets(req: RequestAttrs): string {
    return bulletList([
        { label: "Method", value: titlecase(req.method) },
        { label: "URL", value: req.url },
        ...Object.entries(maskHeaders(req.headers)).map(([k, v]) => ({ label: k, value: v })),
    ], "Request");
}

function renderStep(blocks: Block[], step: DryRunStep): void {
    switch (step.kind) {
        case "shopify_customer": {
            blocks.push(heading("Update Shopify Customer Profile"));
            blocks.push(section(
                `*Previous tags:* \`${
                    step.previousTags.length ? step.previousTags.join(", ") : "(none)"
                }\``,
            ));
            if (step.request) {
                blocks.push(section(requestBullets(step.request)));
                blocks.push(section("*Body:*"));
                if (step.body) blocks.push(...codeBlocks(step.body));
            } else if (step.note) {
                blocks.push(section(step.note));
            }
            break;
        }
        case "email": {
            blocks.push(
                heading("Send email notification (decoded - http request sends raw bytes)"),
            );
            blocks.push(section(requestBullets(step.request)));
            blocks.push(section(bulletList([
                { label: "To", value: step.to },
                { label: "Sender Email", value: step.senderEmail },
                { label: "Subject", value: step.subject },
                { label: "Reply-to", value: step.replyTo ?? "(none)" },
                { label: "CC", value: step.cc ?? "(none)" },
            ], "Email details")));
            blocks.push(section("*Email copy:*"));
            blocks.push(...codeBlocks(step.copy));
            break;
        }
        case "sheet": {
            blocks.push(heading("Update row in waitlist spreadsheet"));
            blocks.push(section(bulletList([
                { label: "Google sheets URL", value: step.sheetUrl },
                { label: "Tab name", value: step.tabName },
                { label: "Row number", value: String(step.rowNumber) },
                { label: "Column updated", value: step.columnName },
                { label: "Existing value in cell", value: step.existingValue },
                { label: "Value inserted", value: step.insertedValue },
            ])));
            break;
        }
        case "note": {
            if (step.title) blocks.push(heading(step.title));
            blocks.push(section(step.note));
            break;
        }
    }
}

/** One channel message per row: header line followed by each step's details. */
export function buildDryRunMessage(
    headerLine: string,
    steps: DryRunStep[],
): { text: string; blocks: Block[] } {
    const blocks: Block[] = [section(headerLine)];
    for (const step of steps) {
        blocks.push(divider());
        renderStep(blocks, step);
    }
    return { text: headerLine, blocks };
}
