/**
 * Approval modal for the refund review flow. A reviewer clicks "Approve" on the
 * evaluation card, edits/confirms the amount + refund type here, and submitting
 * POSTs the decision to the Lambda. Pure view builder — no Slack API calls.
 */

import { formatMoney } from "../../shared/text/strings.ts";
import { context, plainText } from "../../shared/slack/blocks.ts";

export const APPROVE_MODAL_CALLBACK_ID = "approve_refund_modal";
export const AMOUNT_BLOCK_ID = "amount_block";
export const AMOUNT_ACTION_ID = "amount_input";
export const TYPE_BLOCK_ID = "type_block";
export const TYPE_ACTION_ID = "type_select";

export const REFUND_TYPE_OPTIONS = [
    { label: "Refund to original payment", value: "original_method" },
    { label: "Store credit", value: "store_credit" },
];

/** Carried through the modal so the submission handler can update the original
 * message and post to the Lambda without re-deriving context. */
export interface ApproveModalMeta {
    channel: string;
    message_ts: string;
}

export function buildApproveModal(args: {
    orderNumber: string;
    estimatedAmount: number;
    refundType: string; // "original_method" | "store_credit"
    refundable: number | null;
    meta: ApproveModalMeta;
}): Record<string, unknown> {
    const initialType = REFUND_TYPE_OPTIONS.find((o) => o.value === args.refundType) ??
        REFUND_TYPE_OPTIONS[0];

    const refundableNote = args.refundable !== null
        ? `Refundable balance: ${formatMoney(args.refundable)}`
        : "Refundable balance unknown";

    return {
        type: "modal",
        callback_id: APPROVE_MODAL_CALLBACK_ID,
        private_metadata: JSON.stringify(args.meta),
        title: plainText("Approve Refund"),
        submit: plainText("Confirm & Process"),
        close: plainText("Cancel"),
        blocks: [
            context(`Order *${args.orderNumber}* · ${refundableNote}`),
            {
                type: "input",
                block_id: AMOUNT_BLOCK_ID,
                label: plainText("Amount (USD)"),
                element: {
                    type: "plain_text_input",
                    action_id: AMOUNT_ACTION_ID,
                    initial_value: args.estimatedAmount.toFixed(2),
                },
            },
            {
                type: "input",
                block_id: TYPE_BLOCK_ID,
                label: plainText("Refund type"),
                element: {
                    type: "static_select",
                    action_id: TYPE_ACTION_ID,
                    initial_option: {
                        text: plainText(initialType.label),
                        value: initialType.value,
                    },
                    options: REFUND_TYPE_OPTIONS.map((o) => ({
                        text: plainText(o.label),
                        value: o.value,
                    })),
                },
            },
        ],
    };
}
