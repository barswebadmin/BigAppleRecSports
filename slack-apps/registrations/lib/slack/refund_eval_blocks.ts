/**
 * Block Kit builder for the refund evaluation review message (POC).
 * Pure function — no Slack API calls. Renders from the Lambda's
 * RefundEvaluationPayload (snake_case wire shape).
 */

import { BARS_URLS } from "../../config.ts";
import type { RefundEstimate, RefundEvaluationPayload } from "../../types/evaluation_payload.ts";
import { formatMoney } from "../../utils/formatters.ts";
import { type Block, context, divider, header, plainText, section } from "./blocks.ts";

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

export function buildRefundEvalBlocks(
    p: RefundEvaluationPayload,
    decision?: RefundDecision,
): Block[] {
    const blocks: Block[] = [];

    blocks.push(header(`Refund Request — ${p.first_name} ${p.last_name}`));

    // Order not found → short-circuit card
    if (!p.order_found) {
        blocks.push(section(
            `:x: *Order not found* for \`${p.order_number}\`\n` +
                `Requested by ${p.email_address} (${p.refund_type})`,
        ));
        if (p.error) {
            blocks.push(context(p.error));
        }
        return blocks;
    }

    // Request + order facts. Leading "\n" puts a blank line above each label so
    // the two-column rows breathe instead of stacking tight.
    const field = (label: string, value: string): Block => ({
        type: "mrkdwn",
        text: `\n*${label}*\n${value}`,
    });
    blocks.push({
        type: "section",
        fields: [
            field("Order", orderLink(p)),
            field("Product", productLink(p)),
            field("League", formatLeague(p)),
            field("Requested", p.refund_type),
            field("Email", p.email_address),
            field("Order Total", formatMoney(p.order_total)),
            field("Refundable Balance", formatMoney(p.refundable_balance)),
            field("Already Refunded", formatMoney(p.total_refunded)),
        ],
    });

    if (p.notes) blocks.push(section(`*Notes*\n${truncate(p.notes, 280)}`));

    blocks.push(divider());

    // Validation / warnings
    if (p.validation_passed && p.warnings.length === 0) {
        blocks.push(section(":white_check_mark: *Validation passed* — no warnings"));
    } else {
        blocks.push(
            section(
                `:warning: *${p.warnings.length} warning${p.warnings.length === 1 ? "" : "s"}*`,
            ),
        );
        for (const w of p.warnings) blocks.push(section(`• ${w}`));
    }

    // Estimates
    blocks.push(divider());
    blocks.push({
        type: "section",
        fields: [
            {
                type: "mrkdwn",
                text: estimateLine("Refund to original", p.estimated_refund_to_original),
            },
            { type: "mrkdwn", text: estimateLine("Store credit", p.estimated_store_credit) },
        ],
    });

    // Timing diagnostics: season start + where the submission landed. Surfaces
    // *why* an estimate is 0% (legit past-window vs. unparseable season dates).
    const seasonStart = p.season_start_date
        ? `Season start: ${p.season_start_date}`
        : ":warning: Season dates not found on product";
    const weekResolved = p.season_week_resolved ? ` · Submitted ${p.season_week_resolved}` : "";
    blocks.push(context(`${seasonStart}${weekResolved}`));

    // Decision footer: once approved/denied, show the outcome and drop buttons.
    if (decision) {
        blocks.push(divider());
        blocks.push(context(decisionLine(decision)));
        return blocks;
    }

    // Otherwise render the reviewer action buttons.
    blocks.push(divider());
    blocks.push({
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
    });

    return blocks;
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
