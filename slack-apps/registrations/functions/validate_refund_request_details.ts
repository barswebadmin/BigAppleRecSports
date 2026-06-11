import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { RefundRequestType } from "../types/refund_request.ts";
import type { ShopifyOrder } from "../lib/clients/shopify/types/orders.ts";

export const ValidateRefundRequestDetailsFunctionDefinition = DefineFunction({
    callback_id: "validate_refund_request_details",
    title: "Validate Refund Request Details",
    source_file: "functions/validate_refund_request_details.ts",
    input_parameters: {
        properties: {
            refund_request: { type: RefundRequestType },
            shopify_order_json: { type: Schema.types.string },
        },
        required: ["refund_request", "shopify_order_json"],
    },
    output_parameters: {
        properties: {
            email_matches: { type: Schema.types.boolean },
            order_is_not_cancelled: { type: Schema.types.boolean },
            order_is_not_refunded: { type: Schema.types.boolean },
        },
        required: ["email_matches", "order_is_not_cancelled", "order_is_not_refunded"],
    },
});

export default SlackFunction(ValidateRefundRequestDetailsFunctionDefinition, ({ inputs }) => {
    const order = JSON.parse(inputs.shopify_order_json) as ShopifyOrder;
    const req = inputs.refund_request;

    const emailMatches =
        (order.customer?.email ?? "").toLowerCase() === (req.email_address ?? "").toLowerCase();
    const orderIsNotCancelled = order.cancelledAt === null;
    const orderIsNotRefunded = !order.refunds || order.refunds.length === 0;

    return {
        outputs: {
            email_matches: emailMatches,
            order_is_not_cancelled: orderIsNotCancelled,
            order_is_not_refunded: orderIsNotRefunded,
        },
    };
});
