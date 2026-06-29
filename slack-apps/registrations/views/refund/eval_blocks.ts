/**
 * Block Kit builder for the refund evaluation review message.
 * Pure function — no Slack API calls. Renders from the FastAPI backend's
 * `RefundRequestEval` (camelCase wire shape; see Stage 2 § 2.b) plus an
 * optional reviewer decision.
 *
 * Consumes ONLY field paths under `refundEval.order.*`, `refundEval.product.*`,
 * `refundEval.estimate.*`, `refundEval.isValid`, and `refundEval.validationErrors`.
 * The legacy Lambda webhook flow has been retired; this renderer is the only
 * refund-card builder.
 */

import { BARS_URLS } from "../../config/store.ts";
import type {
  CancelOutcome,
  CreateRefundResponse,
  RefundDecision,
  RefundEvalProduct,
  RefundOutcome,
  RefundRequestEval,
  TierEstimate,
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

function numericId(gid: string | null): string | null {
  if (!gid) return null;
  return gid.split("/").pop() ?? null;
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
function orderField(refundEval: RefundRequestEval): string {
  const label = `#${refundEval.order.number.replace(/^#/, "")}`;
  return adminUiLinkField(
    "Order",
    "orders",
    label,
    numericId(refundEval.order.id),
  );
}

/** sport · day · division, linked to the product page. */
function leagueField(refundEval: RefundRequestEval): string {
  const product = refundEval.product;
  const label =
    [product.sport, product.day, product.division]
      .filter(Boolean)
      .join(" · ") || "—";
  return adminUiLinkField("League", "products", label, numericId(product.id));
}

/** Name + email (mailto). The new wire shape has no phone field; SMS link
 *  is dropped. */
function playerField(refundEval: RefundRequestEval): string {
  const name = refundEval.order.customerName.trim();
  const email = refundEval.order.email;
  const emailLink = `<mailto:${email}|${email}>`;
  return `*Player*\n${name} (${emailLink})`;
}

function estimateLine(label: string, est: TierEstimate): string {
  const fee = est.appliedProcessingFee > 0 ? " (incl. processing fee)" : "";
  const noPayment = est.notes.includes("no_payment_made")
    ? " (no payment on order)"
    : "";
  return `*${label}*\n${formatMoney(est.amount)} (${est.percentage}%)${fee}${noPayment}`;
}

/** Single-line context listing whichever week starts parsed. Returns null
 *  when none parsed — the backend owns the diagnostic via
 *  `validationErrors[]` (see § 4.c C5 note). */
function seasonScheduleContext(product: RefundEvalProduct): Block | null {
  const starts = [
    product.week1Start,
    product.week2Start,
    product.week3Start,
    product.week4Start,
    product.week5Start,
  ];
  const labels = starts
    .map((s, i) => (s ? `W${i + 1} ${s}` : null))
    .filter((s): s is string => s !== null);
  if (labels.length === 0) {
    return null;
  }
  return context(`Season schedule: ${labels.join(" · ")}`);
}

export function buildRefundEvalBlocks(
  refundEval: RefundRequestEval,
  decision?: RefundDecision,
): Block[] {
  const scheduleBlock = seasonScheduleContext(refundEval.product);

  // When `isValid` is false but no error strings were supplied, surface a
  // visible cue — degenerate state the backend should never produce, but
  // worth rendering rather than silently passing.
  const warnings = refundEval.validationErrors?.length
    ? refundEval.validationErrors
    : refundEval.isValid
      ? []
      : ["Validation failed"];

  return [
    header(`Refund Request — ${refundEval.order.customerName}`),

    {
      type: "section",
      fields: [
        { type: "mrkdwn", text: playerField(refundEval) },
        { type: "mrkdwn", text: leagueField(refundEval) },
        { type: "mrkdwn", text: orderField(refundEval) },
        mrkdwnField(
          "Total Amount Paid",
          formatMoney(refundEval.order.amountPaid),
        ),
      ],
    },

    divider(),

    section("*Estimated Refund Due*"),
    ...(scheduleBlock ? [scheduleBlock] : []),
    {
      type: "section",
      fields: [
        {
          type: "mrkdwn",
          text: estimateLine(
            "Original form of payment",
            refundEval.estimate.original,
          ),
        },
        {
          type: "mrkdwn",
          text: estimateLine("Store credit", refundEval.estimate.storeCredit),
        },
      ],
    },
    divider(),

    ...validationSummaryBlocks({
      validation_passed: refundEval.isValid,
      warnings,
    }),

    ...(decision
      ? [context(decisionLine(decision))]
      : [
          {
            type: "actions",
            elements: [
              blockKitButton({
                actionId: APPROVE_ACTION_ID,
                label: "Approve",
                style: "primary",
                value: refundEval.order.number,
              }),
              blockKitButton({
                actionId: CONTACT_ACTION_ID,
                label: "Contact player",
                url: `mailto:${refundEval.order.email}`,
              }),
              blockKitButton({
                actionId: DENY_ACTION_ID,
                label: "Deny",
                style: "danger",
                value: refundEval.order.number,
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
    const where = d.dryRun
      ? "preview posted to test channel (dry run)"
      : "sent to BARS API";
    const mode = d.approveAction
      ? ` · ${d.approveAction.replace(/_/g, " ")}`
      : "";
    return `:white_check_mark: *Approved* by <@${d.by}> —${amt}${via}${mode} · ${where}`;
  },
};

function decisionLine(d: RefundDecision): string {
  return DECISION_LINE[d.status](d);
}

// ════════════════════════════════════════════════════════════════════════════
// Post-execute / final-confirmation card (Stage 7)
// ════════════════════════════════════════════════════════════════════════════

/**
 * Build the final-confirmation card from a backend `CreateRefundResponse`
 * plus the operator's decision. Pure function; no Slack API calls. The
 * sheet-driven flow posts a fresh message with these blocks (no
 * pre-existing review-card to chat.update against).
 */
export function buildRefundResultBlocks(
  result: CreateRefundResponse,
  decision: RefundDecision,
): Block[] {
  const blocks: Block[] = [];

  blocks.push(headerBlock(decision));

  const errors = result.errors ?? [];
  if (!result.ok || errors.length > 0) {
    blocks.push(section(":warning: *Refund could not be completed*"));
    for (const err of errors) {
      const fieldHint = err.field
        ? ` (field: ${
            Array.isArray(err.field) ? err.field.join(".") : err.field
          })`
        : "";
      blocks.push(context(`• ${err.message}${fieldHint}`));
    }
    blocks.push(divider());
  }

  if (result.cancel) blocks.push(cancelOutcomeBlock(result.cancel));
  if (result.refund) blocks.push(refundOutcomeBlock(result.refund));

  if (!result.cancel && !result.refund && errors.length === 0) {
    blocks.push(
      context("(no action taken — neither cancel nor refund was requested)"),
    );
  }

  blocks.push(decisionMetaBlock(decision));
  return blocks;
}

function headerBlock(decision: RefundDecision): Block {
  if (decision.status === "approved") {
    return header(`Approved by @${decision.by}`);
  }
  return header(`Denied by @${decision.by}`);
}

function cancelOutcomeBlock(cancel: CancelOutcome): Block {
  const id = numericId(cancel.jobId);
  const status = cancel.jobDone ? "completed" : "in progress";
  const label = id ?? cancel.jobId;
  return section(
    `Order cancelled — Job <${BARS_URLS.admin_ui}/jobs/${id ?? ""}|${label}> · ${status}`,
  );
}

function refundOutcomeBlock(refund: RefundOutcome): Block {
  const via =
    refund.currency === "STORE_CREDIT"
      ? "store credit"
      : "original payment method";
  return section(
    `Refund issued — ${formatMoney(refund.amount)} via ${via} · created ${refund.createdAt}`,
  );
}

function decisionMetaBlock(decision: RefundDecision): Block {
  const parts: string[] = [];
  if (decision.amount !== undefined) {
    parts.push(`Approved: ${formatMoney(decision.amount)}`);
  }
  if (decision.refundType) parts.push(`via ${decision.refundType}`);
  if (decision.restock) parts.push(`restock to ${decision.restock}`);
  if (decision.sendNotification) parts.push("notify customer");
  if (decision.dryRun) parts.push("DRY RUN");
  return context(parts.join(" · ") || "No additional metadata");
}
