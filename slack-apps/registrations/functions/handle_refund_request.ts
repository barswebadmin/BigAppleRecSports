import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { RefundRequestType } from "../types/refund_request.ts";
import type { ShopifyOrder } from "../lib/clients/shopify/types/orders.ts";
import { getCustomAttribute } from "../lib/clients/shopify/order_ops.ts";

export const HandleRefundRequestFunctionDefinition = DefineFunction({
    callback_id: "handle_refund_request",
    title: "Handle Refund Request",
    source_file: "functions/handle_refund_request.ts",
    input_parameters: {
        properties: {
            refund_request: { type: RefundRequestType },
            shopify_order_json: { type: Schema.types.string },
            email_matches: { type: Schema.types.boolean },
            order_is_not_cancelled: { type: Schema.types.boolean },
            order_is_not_refunded: { type: Schema.types.boolean },
        },
        required: ["refund_request"],
    },
    output_parameters: { properties: {}, required: [] },
});

export default SlackFunction(HandleRefundRequestFunctionDefinition, ({ inputs }) => {
    const req = inputs.refund_request;
    console.log("[refund_request] request:", JSON.stringify(req, null, 2));

    if (!inputs.shopify_order_json) {
        console.log("[refund_request] no order found");
        return { outputs: {} };
    }

    const order = JSON.parse(inputs.shopify_order_json) as ShopifyOrder;

    const firstItem = order.lineItems.edges[0]?.node;
    if (firstItem?.customAttributes?.length) {
        const attrs = firstItem.customAttributes;
        console.log(
            "[refund_request] custom attributes:",
            JSON.stringify(
                {
                    preferred_first_name: getCustomAttribute(attrs, "preferred first name"),
                    last_name: getCustomAttribute(attrs, "last name"),
                    contact_email: getCustomAttribute(attrs, "best contact email address"),
                },
                null,
                2,
            ),
        );
    }

    if (!inputs.email_matches) {
        const formEmail = firstItem?.customAttributes?.length
            ? getCustomAttribute(firstItem.customAttributes, "best contact email address")
            : undefined;
        console.log(
            `[refund_request] ❌ email mismatch: request="${req.email_address}" order.customer.email="${order.customer?.email}" form_email="${
                formEmail ?? "N/A"
            }"`,
        );
    }

    if (!inputs.order_is_not_cancelled) {
        console.log(`[refund_request] ❌ order was cancelled at ${order.cancelledAt}`);
    }

    if (!inputs.order_is_not_refunded) {
        console.log("[refund_request] ❌ order has existing refunds:");
        for (const refund of order.refunds) {
            console.log(`  refund ${refund.id} created ${refund.createdAt}`);
            if (refund.transactions.nodes.length > 0) {
                for (const tx of refund.transactions.nodes) {
                    console.log(
                        `    transaction: ${tx.kind} ${tx.status} $${tx.amountSet.shopMoney.amount} via ${tx.gateway}`,
                    );
                }
            }
            if (refund.refundLineItems.nodes.length > 0) {
                for (const li of refund.refundLineItems.nodes) {
                    console.log(
                        `    line item: "${li.lineItem.title}" qty=${li.quantity} $${li.priceSet.shopMoney.amount}`,
                    );
                }
            }
        }
    }

    if (inputs.email_matches && inputs.order_is_not_cancelled && inputs.order_is_not_refunded) {
        console.log("[refund_request] ✅ all validations passed");
    }

    return { outputs: {} };
});
