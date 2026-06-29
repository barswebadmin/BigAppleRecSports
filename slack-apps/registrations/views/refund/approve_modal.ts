/**
 * Refund-flavored approval modal — thin caller around the generic
 * `views/_shared/approve_modal.ts`. All refund-specific labels, options, and
 * defaults are passed in here; the generic builder has zero refund domain
 * knowledge.
 *
 * Stage-1 changes:
 *   - Constant rename: `APPROVE_MODAL_CALLBACK_ID = "approve_refund_modal"` →
 *     `REFUND_APPROVAL_MODAL_CALLBACK_ID = "refund_approval_modal"` (the
 *     rename happens in this thin caller, not the generic builder).
 *   - Block / action ids continue to be re-exported from this module so
 *     downstream importers (the Stage 5 submission handler that POSTs to
 *     `/refunds/create`) can keep their handler bindings unchanged.
 */

import type { SlackView } from "../../shared/slack/message.ts";
import { context } from "../../shared/slack/blocks.ts";
import { formatMoney } from "../../shared/text/strings.ts";
import {
  APPROVE_MODAL_ACTION_ACTION_ID,
  APPROVE_MODAL_ACTION_BLOCK_ID,
  APPROVE_MODAL_AMOUNT_ACTION_ID,
  APPROVE_MODAL_AMOUNT_BLOCK_ID,
  APPROVE_MODAL_NOTIFY_ACTION_ID,
  APPROVE_MODAL_NOTIFY_BLOCK_ID,
  APPROVE_MODAL_RESTOCK_ACTION_ID,
  APPROVE_MODAL_RESTOCK_BLOCK_ID,
  approveModal,
} from "../_shared/approve_modal.ts";

// ─── callback id (Stage 1 rename) ──────────────────────────────────────────

export const REFUND_APPROVAL_MODAL_CALLBACK_ID = "refund_approval_modal";

// ─── block / action IDs (re-exported for handler bindings) ─────────────────

export const ACTION_BLOCK_ID = APPROVE_MODAL_ACTION_BLOCK_ID;
export const ACTION_ACTION_ID = APPROVE_MODAL_ACTION_ACTION_ID;

export const AMOUNT_BLOCK_ID = APPROVE_MODAL_AMOUNT_BLOCK_ID;
export const AMOUNT_ACTION_ID = APPROVE_MODAL_AMOUNT_ACTION_ID;

export const RESTOCK_BLOCK_ID = APPROVE_MODAL_RESTOCK_BLOCK_ID;
export const RESTOCK_ACTION_ID = APPROVE_MODAL_RESTOCK_ACTION_ID;

export const NOTIFY_BLOCK_ID = APPROVE_MODAL_NOTIFY_BLOCK_ID;
export const NOTIFY_ACTION_ID = APPROVE_MODAL_NOTIFY_ACTION_ID;

// ─── option sets ──────────────────────────────────────────────────────────

export const ACTION_OPTIONS = [
  { label: "Cancel + Refund", value: "cancel_refund" },
  { label: "Cancel Only", value: "cancel_only" },
  { label: "Refund Only", value: "refund_only" },
] as const;

export type ApproveAction = (typeof ACTION_OPTIONS)[number]["value"];

export const RESTOCK_OPTIONS = [
  { label: "Veteran lane", value: "veteran" },
  { label: "Early lane", value: "early" },
  { label: "General lane", value: "general" },
  { label: "Waitlist", value: "waitlist" },
] as const;

export type RestockAction = (typeof RESTOCK_OPTIONS)[number]["value"];

export const NOTIFY_OPTION = {
  label: "Send notification email to player via Shopify",
  value: "notify",
};

// ─── modal metadata ────────────────────────────────────────────────────────

/** Carried through the modal so the submission handler can update the original
 *  message and POST `/refunds/create` without re-deriving context. */
export interface ApproveModalMeta extends Record<string, unknown> {
  channel: string;
  message_ts: string;
}

// ─── builder args ─────────────────────────────────────────────────────────

export interface BuildApproveModalArgs {
  orderNumber: string;
  /** Refundable balance shown in context line. */
  refundable: number | null;
  /** Hard cap — enforced for all users; shown as error context when exceeded. */
  totalPaid: number;
  /** Estimated refund to original form of payment. Used as default amount and
   *  as part of soft-cap messaging. */
  estimatedOriginal: number;
  /** Estimated store credit amount (informational in context line). */
  estimatedCredit: number;
  /** Customer-requested ladder from the form (`original_method` | `store_credit`).
   *  Drives which estimate is used for the soft cap vs. privileged override. */
  refundTo: string;
  /** Current action selection — controls whether the amount block renders. */
  action: ApproveAction;
  /** Current amount value as a string (pre-filled from estimate on first open). */
  currentAmount: string;
  /** Current restock selection. `undefined` when no lane is pre-selected
   *  (operator picks on the modal). */
  restock: RestockAction | undefined;
  /** When set, restores notify checkbox state after `views.update`. When
   *  omitted, defaults to checked. */
  selectedNotifyValues?: string[];
  /** Whether the submitting user has elevated privileges. Non-privileged users
   *  hitting the soft cap get "Send to Exec for Approval". */
  isPrivileged: boolean;
  meta: ApproveModalMeta;
}

function softCapEstimate(args: BuildApproveModalArgs): number {
  return args.refundTo === "store_credit"
    ? args.estimatedCredit
    : args.estimatedOriginal;
}

function resolveSubmitLabel(args: BuildApproveModalArgs): string {
  if (args.action === "cancel_only") return "Confirm & Process";
  const amt = Number.parseFloat(args.currentAmount) || 0;
  const est = softCapEstimate(args);
  if (!args.isPrivileged && amt > est && amt <= args.totalPaid) {
    return "Send to Exec for Approval";
  }
  return "Confirm & Process";
}

export function buildApproveModal(args: BuildApproveModalArgs): SlackView {
  const {
    orderNumber,
    refundable,
    totalPaid,
    estimatedOriginal,
    estimatedCredit,
    refundTo,
    action,
    currentAmount,
    restock,
    selectedNotifyValues,
    isPrivileged,
    meta,
  } = args;

  const showAmountInput = action !== "cancel_only";
  const amt = Number.parseFloat(currentAmount) || 0;
  const estTotal = softCapEstimate(args);
  const exceedsTotalPaid = showAmountInput && amt > totalPaid;
  const exceedsEstimate =
    showAmountInput && !isPrivileged && amt > estTotal && !exceedsTotalPaid;

  const refundableLine =
    refundable !== null && refundable !== undefined
      ? formatMoney(refundable)
      : "unknown";

  const view = approveModal<ApproveModalMeta>({
    callbackId: REFUND_APPROVAL_MODAL_CALLBACK_ID,
    title: "Approve Refund",
    submitLabel: resolveSubmitLabel(args),
    closeLabel: "Cancel",
    headerBlocks: [
      context(
        `Order *${orderNumber}* · Refundable: ${refundableLine} · ` +
          `Original est. ${formatMoney(estimatedOriginal)} · ` +
          `Store credit est. ${formatMoney(estimatedCredit)} · ` +
          `Requested: ${refundTo}`,
      ),
    ],
    actionOptions: ACTION_OPTIONS.map((o) => ({
      value: o.value,
      label: o.label,
    })),
    initialActionValue: action,
    amountInput: showAmountInput
      ? {
          default: Number.parseFloat(currentAmount) || 0,
          min: 0,
          max: totalPaid,
          required: true,
          hint: isPrivileged
            ? `Hard cap: ${formatMoney(totalPaid)}. You may exceed the estimate.`
            : `Hard cap: ${formatMoney(totalPaid)}. Exceeding the estimate (${formatMoney(
                estTotal,
              )}) routes to exec.`,
        }
      : undefined,
    restockOptions: RESTOCK_OPTIONS.map((o) => ({
      value: o.value,
      label: o.label,
    })),
    initialRestockValue: restock,
    notifyToggle: {
      default:
        selectedNotifyValues === undefined
          ? true
          : selectedNotifyValues.includes(NOTIFY_OPTION.value),
      label: NOTIFY_OPTION.label,
      value: NOTIFY_OPTION.value,
    },
    metadata: meta,
  });

  // The generic builder uses a fixed initial-amount value (numeric default
  // formatted as `N.toFixed(2)`); the refund flow drives the amount input
  // via a free-form string (`currentAmount`) so users can type partial
  // values like "12." mid-edit. Patch the initial_value into the rendered
  // amount block so we keep that behavior without leaking string-vs-number
  // semantics into the generic builder.
  if (showAmountInput) {
    for (const block of view.blocks) {
      const blockId = (block as { block_id?: string }).block_id;
      if (blockId !== AMOUNT_BLOCK_ID) continue;
      const element = (block as { element?: Record<string, unknown> }).element;
      if (element && typeof element === "object") {
        element.initial_value = currentAmount;
      }
    }
  }

  // Optional inline warnings — inserted after the amount input.
  if (exceedsTotalPaid || exceedsEstimate) {
    const idx = view.blocks.findIndex(
      (b) => (b as { block_id?: string }).block_id === AMOUNT_BLOCK_ID,
    );
    if (idx !== -1) {
      const warnings = [];
      if (exceedsTotalPaid) {
        warnings.push(
          context(
            `:no_entry: Amount exceeds total amount paid (${formatMoney(
              totalPaid,
            )}) — reduce before submitting.`,
          ),
        );
      }
      if (exceedsEstimate) {
        warnings.push(
          context(
            `:warning: Amount exceeds estimated refund (${formatMoney(
              estTotal,
            )}) — submitting will route to exec for approval.`,
          ),
        );
      }
      view.blocks.splice(idx + 1, 0, ...warnings);
    }
  }

  return view;
}

// ─── submission value extractor ───────────────────────────────────────────

export interface ApproveModalValues {
  action: ApproveAction;
  amount: number | null;
  /** `undefined` when the operator did not pick a restock lane (no
   *  default — see § 5.k.2 of the Stage 5 design). The Slack handler
   *  omits `restockTo` from the wire body when this is `undefined`. */
  restock: RestockAction | undefined;
  sendNotification: boolean;
}

type StateCell = {
  value?: string;
  selected_option?: { value: string };
  selected_options?: { value: string }[];
};

/** Extract typed values from `view.state.values` on view_submission. */
export function extractApproveModalValues(
  stateValues: Record<string, Record<string, StateCell>>,
): ApproveModalValues {
  const action = (stateValues[ACTION_BLOCK_ID]?.[ACTION_ACTION_ID]
    ?.selected_option?.value ?? "cancel_refund") as ApproveAction;
  const rawAmt = stateValues[AMOUNT_BLOCK_ID]?.[AMOUNT_ACTION_ID]?.value;
  const restock = stateValues[RESTOCK_BLOCK_ID]?.[RESTOCK_ACTION_ID]
    ?.selected_option?.value as RestockAction | undefined;
  const notifyOpts =
    stateValues[NOTIFY_BLOCK_ID]?.[NOTIFY_ACTION_ID]?.selected_options ?? [];

  return {
    action,
    amount:
      action !== "cancel_only" && rawAmt !== undefined && rawAmt !== ""
        ? Number.parseFloat(rawAmt)
        : null,
    restock,
    sendNotification: notifyOpts.some((o) => o.value === NOTIFY_OPTION.value),
  };
}
