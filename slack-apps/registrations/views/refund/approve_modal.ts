/**
 * Approval modal for the refund review flow. A reviewer clicks "Approve" on the
 * evaluation card, picks cancel/refund/both, optional restock + notify, and
 * submits. `dispatch_action` on action + amount drives `views.update` so the
 * amount block and submit label stay in sync (see `handleApproveModalBlockAction`
 * in the orchestrator).
 */

import { modal, type SlackView } from "../../shared/slack/message.ts";
import { formatMoney } from "../../shared/text/strings.ts";
import {
    checkboxes,
    context,
    divider,
    input,
    radioButtons,
    toOption,
    toOptions,
} from "../../shared/slack/blocks.ts";

// ─── block / action IDs ────────────────────────────────────────────────────

export const APPROVE_MODAL_CALLBACK_ID = "approve_refund_modal";

export const ACTION_BLOCK_ID = "action_block";
export const ACTION_ACTION_ID = "action_input";

export const AMOUNT_BLOCK_ID = "amount_block";
export const AMOUNT_ACTION_ID = "amount_input";

export const RESTOCK_BLOCK_ID = "restock_block";
export const RESTOCK_ACTION_ID = "restock_input";

export const NOTIFY_BLOCK_ID = "notify_block";
export const NOTIFY_ACTION_ID = "notify_input";

// ─── option sets ──────────────────────────────────────────────────────────

export const ACTION_OPTIONS = [
    { label: "Cancel + Refund", value: "cancel_refund" },
    { label: "Cancel Only", value: "cancel_only" },
    { label: "Refund Only", value: "refund_only" },
] as const;

export type ApproveAction = (typeof ACTION_OPTIONS)[number]["value"];

export const RESTOCK_OPTIONS = [
    { label: "None", value: "none" },
    { label: "Full restock", value: "full" },
    { label: "To waitlist", value: "waitlist" },
    { label: "Admin hold", value: "admin_hold" },
    { label: "Do not restock", value: "no_restock" },
] as const;

export type RestockAction = (typeof RESTOCK_OPTIONS)[number]["value"];

export const NOTIFY_OPTION = {
    label: "Send notification email to player via Shopify",
    value: "notify",
};

// ─── modal metadata ────────────────────────────────────────────────────────

/** Carried through the modal so the submission handler can update the original
 *  message and post to the Lambda without re-deriving context. */
export interface ApproveModalMeta {
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
    /**
     * Estimated refund to original form of payment.
     * Used as the default amount and as part of soft-cap messaging.
     */
    estimatedOriginal: number;
    /** Estimated store credit amount (informational in context line). */
    estimatedCredit: number;
    /**
     * Customer-requested ladder from the form (`original_method` | `store_credit`).
     * Drives which estimate is used for the soft cap vs. privileged override.
     */
    refundTo: string;
    /** Current action selection — controls whether the amount block renders. */
    action: ApproveAction;
    /** Current amount value as a string (pre-filled from estimate on first open). */
    currentAmount: string;
    /** Current restock selection. */
    restock: RestockAction;
    /**
     * When set, restores notify checkbox state after `views.update`. When
     * omitted, defaults to checked.
     */
    selectedNotifyValues?: string[];
    /**
     * Whether the submitting user has elevated privileges.
     * Non-privileged users hitting the soft cap get "Send to Exec for Approval".
     */
    isPrivileged: boolean;
    meta: ApproveModalMeta;
}

function softCapEstimate(args: BuildApproveModalArgs): number {
    return args.refundTo === "store_credit" ? args.estimatedCredit : args.estimatedOriginal;
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
    const exceedsEstimate = showAmountInput && !isPrivileged && amt > estTotal && !exceedsTotalPaid;

    const initialAction = ACTION_OPTIONS.find((o) => o.value === action) ?? ACTION_OPTIONS[0];
    const initialRestock = RESTOCK_OPTIONS.find((o) => o.value === restock) ?? RESTOCK_OPTIONS[0];

    const refundableLine = refundable !== null && refundable !== undefined
        ? formatMoney(refundable)
        : "unknown";

    const notifyInitial: { label: string; value: string }[] | undefined =
        selectedNotifyValues === undefined
            ? [NOTIFY_OPTION]
            : selectedNotifyValues.includes(NOTIFY_OPTION.value)
            ? [NOTIFY_OPTION]
            : undefined;

    return modal({
        callbackId: APPROVE_MODAL_CALLBACK_ID,
        title: "Approve Refund",
        submitLabel: resolveSubmitLabel(args),
        closeLabel: "Cancel",
        metadata: JSON.stringify(meta),
        blocks: [
            context(
                `Order *${orderNumber}* · Refundable: ${refundableLine} · ` +
                    `Original est. ${formatMoney(estimatedOriginal)} · ` +
                    `Store credit est. ${formatMoney(estimatedCredit)} · ` +
                    `Requested: ${refundTo}`,
            ),

            divider(),

            input({
                blockId: ACTION_BLOCK_ID,
                label: "Action",
                dispatchAction: true,
                element: radioButtons({
                    actionId: ACTION_ACTION_ID,
                    options: toOptions([...ACTION_OPTIONS]),
                    initial: toOption(initialAction),
                }),
            }),

            ...(showAmountInput
                ? [
                    input({
                        blockId: AMOUNT_BLOCK_ID,
                        label: "Amount (USD)",
                        hint: isPrivileged
                            ? `Hard cap: ${formatMoney(totalPaid)}. You may exceed the estimate.`
                            : `Hard cap: ${formatMoney(totalPaid)}. Exceeding the estimate (${
                                formatMoney(estTotal)
                            }) routes to exec.`,
                        dispatchAction: true,
                        element: {
                            type: "plain_text_input",
                            action_id: AMOUNT_ACTION_ID,
                            initial_value: currentAmount,
                        },
                    }),
                    ...(exceedsTotalPaid
                        ? [
                            context(
                                `:no_entry: Amount exceeds total amount paid (${
                                    formatMoney(totalPaid)
                                }) — reduce before submitting.`,
                            ),
                        ]
                        : []),
                    ...(exceedsEstimate
                        ? [
                            context(
                                `:warning: Amount exceeds estimated refund (${
                                    formatMoney(estTotal)
                                }) — submitting will route to exec for approval.`,
                            ),
                        ]
                        : []),
                ]
                : []),

            divider(),

            input({
                blockId: RESTOCK_BLOCK_ID,
                label: "Restock?",
                element: radioButtons({
                    actionId: RESTOCK_ACTION_ID,
                    options: toOptions([...RESTOCK_OPTIONS]),
                    initial: toOption(initialRestock),
                }),
            }),

            divider(),

            input({
                blockId: NOTIFY_BLOCK_ID,
                label: "Notifications",
                optional: true,
                element: checkboxes({
                    actionId: NOTIFY_ACTION_ID,
                    options: [toOption(NOTIFY_OPTION)],
                    initial: notifyInitial ? toOptions(notifyInitial) : undefined,
                }),
            }),
        ],
    });
}

// ─── submission value extractor ───────────────────────────────────────────

export interface ApproveModalValues {
    action: ApproveAction;
    amount: number | null;
    restock: RestockAction;
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
    const action = (stateValues[ACTION_BLOCK_ID]?.[ACTION_ACTION_ID]?.selected_option?.value ??
        "cancel_refund") as ApproveAction;
    const rawAmt = stateValues[AMOUNT_BLOCK_ID]?.[AMOUNT_ACTION_ID]?.value;
    const restock = (stateValues[RESTOCK_BLOCK_ID]?.[RESTOCK_ACTION_ID]?.selected_option?.value ??
        "none") as RestockAction;
    const notifyOpts = stateValues[NOTIFY_BLOCK_ID]?.[NOTIFY_ACTION_ID]?.selected_options ?? [];

    return {
        action,
        amount: action !== "cancel_only" && rawAmt !== undefined && rawAmt !== ""
            ? Number.parseFloat(rawAmt)
            : null,
        restock,
        sendNotification: notifyOpts.some((o) => o.value === NOTIFY_OPTION.value),
    };
}
