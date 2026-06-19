/**
 * Block Kit builder for the refund evaluation review message.
 * Pure function — no Slack API calls. Renders from the Lambda's
 * RefundEvaluationPayload (snake_case wire shape) plus an optional decision.
 */

import { toTitleCase } from "@std/text/unstable-to-title-case";
import { BARS_URLS } from "../../config/store.ts";
import type {
    RefundDecision,
    RefundEstimate,
    RefundEvaluationPayload,
} from "../../domain/refund/types.ts";
import { formatMoney } from "../../shared/text/strings.ts";
import { blockKitButton } from "../../shared/slack/block_kit_button.ts";
import {
    type Block,
    context,
    divider,
    header,
    mrkdwnField,
    section,
    validationSummaryBlocks,
} from "../../shared/slack/blocks.ts";

export const APPROVE_ACTION_ID = "approve_refund";
export const DENY_ACTION_ID = "deny_refund";
export const CONTACT_ACTION_ID = "contact_player";

function truncate(text: string, max: number): string {
    const t = text.trim();
    return t.length <= max ? t : `${t.slice(0, max - 1).trimEnd()}…`;
}

function numericId(gid: string | null): string | null {
    if (!gid) return null;
    return gid.split("/").pop() ?? null;
}

function titleCase(s: string): string {
    return toTitleCase(s.replace(/[_-]+/g, " "));
}

/** Bold titled Slack mrkdwn field; links `label` to admin UI when `id` is set. */
function adminUiLinkField(
    title: string,
    adminPathSegment: "orders" | "products",
    label: string,
    id: string | null,
): string {
    const head = `*${title}*\n`;
    return id
        ? `${head}<${BARS_URLS.admin_ui}/${adminPathSegment}/${id}|${label}>`
        : `${head}${label}`;
}

/** "#48957" linking to the Shopify admin order page. */
function orderField(p: RefundEvaluationPayload): string {
    const label = `#${p.order_number.replace(/^#/, "")}`;
    return adminUiLinkField("Order", "orders", label, numericId(p.order_id));
}

/** sport · day · division, linked to the product page. */
function leagueField(p: RefundEvaluationPayload): string {
    const label = [p.sport, p.day, p.division].filter(Boolean).join(" · ") || "—";
    return adminUiLinkField("League", "products", label, numericId(p.product_id));
}

/** Name + email (mailto) + optional SMS link. */
function playerField(p: RefundEvaluationPayload): string {
    const name = `${p.first_name} ${p.last_name}`.trim();
    const emailLink = `<mailto:${p.email}|${p.email}>`;
    const phoneLine = p.phone ? `\n<sms:${p.phone}|${p.phone}>` : "";
    return `*Player*\n${name} (${emailLink})${phoneLine}`;
}

function estimateLine(label: string, est: RefundEstimate | null): string {
    if (!est) return `*${label}*\n—`;
    const pct = est.percentage !== null ? ` (${est.percentage}%)` : "";
    const fee = est.has_processing_fee ? " _(incl. processing fee)_" : "";
    return `*${label}*\n${formatMoney(est.amount)}${pct}${fee}`;
}

/** Short-circuit card for "order not found" payloads. */
function buildNotFoundBlocks(p: RefundEvaluationPayload): Block[] {
    const blocks: Block[] = [
        header(`Refund Request — ${p.first_name} ${p.last_name}`),
        section(
            `:x: *Order not found* for \`${p.order_number}\`\n` +
                `Requested by ${p.email} (${titleCase(p.refund_to)})`,
        ),
    ];
    return p.error ? [...blocks, context(p.error)] : blocks;
}

export function buildRefundEvalBlocks(
    p: RefundEvaluationPayload,
    decision?: RefundDecision,
): Block[] {
    if (!p.order_found) return buildNotFoundBlocks(p);

    const seasonResolved = Boolean(p.season_start_date);
    const weekResolved = p.season_week_resolved ? ` · Submitted ${p.season_week_resolved}` : "";
    const reasoning = seasonResolved
        ? `Season start: ${p.season_start_date}${weekResolved}`
        : ":warning: Season dates not found on product";

    const totalRefunded = p.total_refunded ?? 0;

    return [
        header(`Refund Request — ${p.first_name} ${p.last_name}`),

        {
            type: "section",
            fields: [
                { type: "mrkdwn", text: playerField(p) },
                { type: "mrkdwn", text: leagueField(p) },
                mrkdwnField("Refund to", titleCase(p.refund_to)),
                { type: "mrkdwn", text: orderField(p) },
                mrkdwnField("Total Amount Paid", formatMoney(p.order_total)),
                ...(totalRefunded > 0
                    ? [mrkdwnField("Already Refunded", formatMoney(totalRefunded))]
                    : []),
            ],
        },

        ...(p.notes ? [section(`*Notes*\n${truncate(p.notes, 280)}`)] : []),
        divider(),

        section("*Estimated Refund Due*"),
        context(reasoning),
        ...(seasonResolved
            ? [
                {
                    type: "section",
                    fields: [
                        {
                            type: "mrkdwn",
                            text: estimateLine(
                                "Original form of payment",
                                p.estimated_refund_to_original,
                            ),
                        },
                        {
                            type: "mrkdwn",
                            text: estimateLine("Store credit", p.estimated_store_credit),
                        },
                    ],
                },
            ]
            : []),
        divider(),

        ...validationSummaryBlocks(p),

        ...(decision ? [context(decisionLine(decision))] : [
            {
                type: "actions",
                elements: [
                    blockKitButton({
                        actionId: APPROVE_ACTION_ID,
                        label: "Approve",
                        style: "primary",
                        value: p.order_number,
                    }),
                    blockKitButton({
                        actionId: CONTACT_ACTION_ID,
                        label: "Contact player",
                        url: `mailto:${p.email}`,
                    }),
                    blockKitButton({
                        actionId: DENY_ACTION_ID,
                        label: "Deny",
                        style: "danger",
                        value: p.order_number,
                    }),
                ],
            },
        ]),
    ];
}

const DECISION_LINE: Record<
    RefundDecision["status"],
    (d: RefundDecision) => string
> = {
    denied: (d) => `:no_entry: *Denied* by <@${d.by}>`,
    approved: (d) => {
        const amt = d.amount !== undefined ? ` ${formatMoney(d.amount)}` : "";
        const via = d.refundType ? ` via ${d.refundType}` : "";
        const where = d.dryRun ? "preview posted to test channel (dry run)" : "sent to Lambda";
        const mode = d.approveAction ? ` · ${d.approveAction.replace(/_/g, " ")}` : "";
        return `:white_check_mark: *Approved* by <@${d.by}> —${amt}${via}${mode} · ${where}`;
    },
};

function decisionLine(d: RefundDecision): string {
    return DECISION_LINE[d.status](d);
}
