/**
 * Block Kit builder for the refund evaluation review message (POC).
 * Pure function — no Slack API calls. Renders from the Lambda's
 * RefundEvaluationPayload (snake_case wire shape).
 */

import { BARS_URLS } from "../../config/store.ts";
import type { RefundEstimate, RefundEvaluationPayload } from "./types.ts";
import { formatMoney } from "../../shared/text/strings.ts";
import {
    type Block,
    context,
    divider,
    header,
    plainText,
    section,
} from "../../shared/slack/blocks.ts";

/** Final reviewer decision; when present the card renders a status line and
 * drops the action buttons (used after Approve/Deny). */
export interface RefundDecision {
    status: "approved" | "denied";
    by: string; // Slack user id
    amount?: number;
    refundType?: string;
    /** True when the approval only previewed payloads (didn't send to the Lambda). */
    dryRun?: boolean;
}

export const APPROVE_ACTION_ID = "approve_refund";
export const DENY_ACTION_ID = "deny_refund";

function truncate(text: string, max: number): string {
    const t = text.trim();
    return t.length <= max ? t : `${t.slice(0, max - 1).trimEnd()}…`;
}

function numericId(gid: string | null): string | null {
    if (!gid) return null;
    return gid.split("/").pop() ?? null;
}

function orderLink(p: RefundEvaluationPayload): string {
    const id = numericId(p.order_id);
    if (!id) return p.order_number;
    return `<${BARS_URLS.admin_ui}/orders/${id}|${p.order_number}>`;
}

function productLink(p: RefundEvaluationPayload): string {
    if (!p.product_title) return "—";
    const id = numericId(p.product_id);
    if (!id) return p.product_title;
    return `<${BARS_URLS.admin_ui}/products/${id}|${p.product_title}>`;
}

function formatLeague(p: RefundEvaluationPayload): string {
    const parts = [p.sport, p.season, p.day, p.division].filter(Boolean);
    return parts.length ? parts.join(" · ") : "—";
}

function estimateLine(label: string, est: RefundEstimate | null): string {
    if (!est) return `*${label}*\n—`;
    const pct = est.percentage !== null ? ` (${est.percentage}%)` : "";
    const fee = est.has_processing_fee ? " _(incl. processing fee)_" : "";
    return `*${label}*\n${formatMoney(est.amount)}${pct}${fee}`;
}

/** Two-column mrkdwn field for the order/customer facts grid. Leading "\n"
 *  puts a blank line above each label so rows breathe instead of stacking tight. */
const mrkdwnField = (label: string, value: string): Block => ({
    type: "mrkdwn",
    text: `\n*${label}*\n${value}`,
});

/** Short-circuit card for "order not found" payloads. */
function buildNotFoundBlocks(p: RefundEvaluationPayload): Block[] {
    const blocks: Block[] = [
        header(`Refund Request — ${p.first_name} ${p.last_name}`),
        section(
            `:x: *Order not found* for \`${p.order_number}\`\n` +
                `Requested by ${p.email} (${p.refund_to})`,
        ),
    ];
    return p.error ? [...blocks, context(p.error)] : blocks;
}

/** Validation summary: either green check, or the warning header followed by
 *  one section per warning bullet (flat — no nested loops). */
function buildValidationBlocks(p: RefundEvaluationPayload): Block[] {
    if (p.validation_passed && p.warnings.length === 0) {
        return [section(":white_check_mark: *Validation passed* — no warnings")];
    }
    const plural = p.warnings.length === 1 ? "" : "s";
    return [
        section(`:warning: *${p.warnings.length} warning${plural}*`),
        ...p.warnings.map((w) => section(`• ${w}`)),
    ];
}

export function buildRefundEvalBlocks(
    p: RefundEvaluationPayload,
    decision?: RefundDecision,
): Block[] {
    if (!p.order_found) return buildNotFoundBlocks(p);

    const seasonStart = p.season_start_date
        ? `Season start: ${p.season_start_date}`
        : ":warning: Season dates not found on product";
    const weekResolved = p.season_week_resolved ? ` · Submitted ${p.season_week_resolved}` : "";

    return [
        header(`Refund Request — ${p.first_name} ${p.last_name}`),
        {
            type: "section",
            fields: [
                mrkdwnField("Order", orderLink(p)),
                mrkdwnField("Product", productLink(p)),
                mrkdwnField("League", formatLeague(p)),
                mrkdwnField("Requested", p.refund_to),
                mrkdwnField("Email", p.email),
                mrkdwnField("Order Total", formatMoney(p.order_total)),
                mrkdwnField("Refundable Balance", formatMoney(p.refundable_balance)),
                mrkdwnField("Already Refunded", formatMoney(p.total_refunded)),
            ],
        },
        ...(p.notes ? [section(`*Notes*\n${truncate(p.notes, 280)}`)] : []),
        divider(),
        ...buildValidationBlocks(p),
        divider(),
        {
            type: "section",
            fields: [
                {
                    type: "mrkdwn",
                    text: estimateLine("Refund to original", p.estimated_refund_to_original),
                },
                { type: "mrkdwn", text: estimateLine("Store credit", p.estimated_store_credit) },
            ],
        },
        // Timing diagnostics: season start + where the submission landed.
        // Surfaces *why* an estimate is 0% (legit past-window vs. unparseable
        // season dates).
        context(`${seasonStart}${weekResolved}`),
        divider(),
        ...(decision ? [context(decisionLine(decision))] : [{
            type: "actions",
            elements: [
                {
                    type: "button",
                    action_id: APPROVE_ACTION_ID,
                    style: "primary",
                    text: plainText("Approve"),
                    value: p.order_number,
                },
                {
                    type: "button",
                    action_id: DENY_ACTION_ID,
                    style: "danger",
                    text: plainText("Deny"),
                    value: p.order_number,
                },
            ],
        }]),
    ];
}

function decisionLine(d: RefundDecision): string {
    if (d.status === "denied") {
        return `:no_entry: *Denied* by <@${d.by}>`;
    }
    const amt = d.amount !== undefined ? ` ${formatMoney(d.amount)}` : "";
    const via = d.refundType ? ` via ${d.refundType}` : "";
    const where = d.dryRun ? "preview posted to test channel (dry run)" : "sent to Lambda";
    return `:white_check_mark: *Approved* by <@${d.by}> —${amt}${via} · ${where}`;
}
