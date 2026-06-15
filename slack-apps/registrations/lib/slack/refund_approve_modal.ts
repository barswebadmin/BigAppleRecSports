/**
 * Approval modal for the refund review flow. A reviewer clicks "Approve" on the
 * evaluation card, edits/confirms the amount + refund type here, and submitting
 * POSTs the decision to the Lambda. Pure view builder — no Slack API calls.
 */

export const APPROVE_MODAL_CALLBACK_ID = "approve_refund_modal";
export const AMOUNT_BLOCK_ID = "amount_block";
export const AMOUNT_ACTION_ID = "amount_input";
export const TYPE_BLOCK_ID = "type_block";
export const TYPE_ACTION_ID = "type_select";

export const REFUND_TYPE_OPTIONS = [
    { label: "Refund to original payment", value: "refund_to_original" },
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
    refundType: string; // "refund_to_original" | "store_credit"
    refundable: number | null;
    meta: ApproveModalMeta;
}): Record<string, unknown> {
    const initialType = REFUND_TYPE_OPTIONS.find((o) => o.value === args.refundType) ??
        REFUND_TYPE_OPTIONS[0];

    const refundableNote = args.refundable !== null
        ? `Refundable balance: $${args.refundable.toFixed(2)}`
        : "Refundable balance unknown";

    return {
        type: "modal",
        callback_id: APPROVE_MODAL_CALLBACK_ID,
        private_metadata: JSON.stringify(args.meta),
        title: { type: "plain_text", text: "Approve Refund" },
        submit: { type: "plain_text", text: "Confirm & Process" },
        close: { type: "plain_text", text: "Cancel" },
        blocks: [
            {
                type: "context",
                elements: [{
                    type: "mrkdwn",
                    text: `Order *${args.orderNumber}* · ${refundableNote}`,
                }],
            },
            {
                type: "input",
                block_id: AMOUNT_BLOCK_ID,
                label: { type: "plain_text", text: "Amount (USD)" },
                element: {
                    type: "plain_text_input",
                    action_id: AMOUNT_ACTION_ID,
                    initial_value: args.estimatedAmount.toFixed(2),
                },
            },
            {
                type: "input",
                block_id: TYPE_BLOCK_ID,
                label: { type: "plain_text", text: "Refund type" },
                element: {
                    type: "static_select",
                    action_id: TYPE_ACTION_ID,
                    initial_option: {
                        text: { type: "plain_text", text: initialType.label },
                        value: initialType.value,
                    },
                    options: REFUND_TYPE_OPTIONS.map((o) => ({
                        text: { type: "plain_text", text: o.label },
                        value: o.value,
                    })),
                },
            },
        ],
    };
}
