/**
 * Dry-run preview: turn planned actions into Slack blocks describing the exact
 * requests the real run would send (method/URL/headers with credentials masked,
 * bodies, decoded email/sheet details), plus a posting helper that ships one
 * channel message per preview. Domain-agnostic — any flow that builds a
 * `PreparedRequest` can preview it via `requestStep` before executing.
 */

import { maskHeaders, type PreparedRequest } from "../http/prepared_request.ts";
import type { SlackAPIClient } from "deno-slack-api/types.ts";
import { type Block, context, divider, header, section } from "./blocks.ts";
import type { SlackMessage } from "./message.ts";
import { formatDiagnostic } from "./diagnostics.ts";
import { titlecase } from "../text/strings.ts";

// Slack section text caps at 3000 chars; chunk long bodies under it. Cap the
// number of chunks per field so one request can't exceed Slack's 50-block /
// message-size limit (anything past the cap is truncated with a note).
const MAX_TEXT = 2900;
const MAX_CHUNKS = 8;

function codeBlocks(content: string): Block[] {
    const blocks: Block[] = [];
    const limit = MAX_TEXT * MAX_CHUNKS;
    const shown = content.length > limit ? content.slice(0, limit) : content;
    for (let i = 0; i < shown.length; i += MAX_TEXT) {
        blocks.push(section("```" + shown.slice(i, i + MAX_TEXT) + "```"));
    }
    if (content.length > limit) {
        blocks.push(context(
            `_…truncated for display (${content.length.toLocaleString()} chars total)._`,
        ));
    }
    return blocks;
}

/** The wire-level attributes of a request (headers are masked at render time). */
interface RequestAttrs {
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
    // Generic, domain-agnostic request preview. Any flow holding a PreparedRequest
    // can render it (see `requestStep`) — used by refunds to show the exact,
    // irreversible Shopify call before it's sent.
    | { kind: "request"; label: string; request: RequestAttrs; body?: string }
    | { kind: "note"; title?: string; note: string };

interface Bullet {
    label: string;
    value: string;
}

/**
 * Render a bulleted list as `• *Label:* \`value\``, with every value inline-code
 * formatted. Optional bold heading line above the bullets. Reusable across all
 * dry-run sections.
 */
function bulletList(bullets: Bullet[], headingLine?: string): string {
    const lines = headingLine ? [`*${headingLine}*`] : [];
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

/** Either the request triple (method/url/headers + body), the fallback note, or
 *  nothing — whichever is supplied. Extracted so `renderStep` doesn't nest an
 *  `if` inside the `shopify_customer` case body. */
function shopifyCustomerDetailBlocks(step: {
    request: RequestAttrs | null;
    body?: string;
    note?: string;
}): Block[] {
    if (step.request) {
        const body = step.body ? codeBlocks(step.body) : [];
        return [section(requestBullets(step.request)), section("*Body:*"), ...body];
    }
    return step.note ? [section(step.note)] : [];
}

function renderStep(blocks: Block[], step: DryRunStep): void {
    switch (step.kind) {
        case "shopify_customer": {
            blocks.push(header("Update Shopify Customer Profile"));
            blocks.push(section(
                `*Previous tags:* \`${
                    step.previousTags.length ? step.previousTags.join(", ") : "(none)"
                }\``,
            ));
            blocks.push(...shopifyCustomerDetailBlocks(step));
            break;
        }
        case "email": {
            blocks.push(
                header("Send email notification (decoded - http request sends raw bytes)"),
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
            blocks.push(header("Update row in waitlist spreadsheet"));
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
        case "request": {
            blocks.push(header(step.label));
            blocks.push(section(requestBullets(step.request)));
            blocks.push(section("*Body:*"));
            blocks.push(...(step.body ? codeBlocks(step.body) : []));
            break;
        }
        case "note": {
            blocks.push(...(step.title ? [header(step.title)] : []));
            blocks.push(section(step.note));
            break;
        }
    }
}

/** One channel message per row: header line followed by each step's details. */
function buildDryRunMessage(
    headerLine: string,
    steps: DryRunStep[],
): SlackMessage {
    const blocks: Block[] = [section(headerLine)];
    for (const step of steps) {
        blocks.push(divider());
        renderStep(blocks, step);
    }
    return { text: headerLine, blocks };
}

/** Adapt any PreparedRequest into a generic request step. Uses `displayBody` for
 * the shown body when present (e.g. a decoded email instead of a base64 blob);
 * the wire `body` is what the real executor sends. */
export function requestStep(req: PreparedRequest): DryRunStep {
    return {
        kind: "request",
        label: req.label,
        request: { method: req.method, url: req.url, headers: req.headers },
        body: req.displayBody ?? req.body,
    };
}

export interface DryRunPreview {
    /** Header line (markdown) shown as the first block of the message. */
    header: string;
    /** Short plain label used only in the failure fallback (e.g. who/what). */
    label?: string;
    steps: DryRunStep[];
}

/**
 * Post one channel message per preview — kept one-per-message so a multi-item
 * run can't exceed Slack's per-message block limit. On a post failure, ships a
 * terse fallback so the operator knows a preview was dropped, and invokes
 * `onError` for detailed logging. Returns false if any message failed.
 *
 * Sequential awaits (not Promise.all) preserve preview order in the channel
 * and stay within Slack's per-conversation rate limit budget.
 */
export async function postDryRunPreviews(
    client: SlackAPIClient,
    channel: string,
    previews: DryRunPreview[],
    onError?: (preview: DryRunPreview, error: string) => void,
): Promise<boolean> {
    const outcomes: boolean[] = [];
    for (const preview of previews) {
        const { text, blocks } = buildDryRunMessage(preview.header, preview.steps);
        const res = await client.chat.postMessage({ channel, text, blocks });
        if (res.ok) {
            outcomes.push(true);
            continue;
        }
        const error = String(res.error);
        onError?.(preview, error);
        const fallback = formatDiagnostic(
            "warn",
            `Dry-run preview${preview.label ? ` for ${preview.label}` : ""} couldn't be rendered`,
            `Error: \`${error}\`. Check the run logs.`,
        );
        await client.chat.postMessage({ channel, ...fallback });
        outcomes.push(false);
    }
    return outcomes.every((ok) => ok);
}
