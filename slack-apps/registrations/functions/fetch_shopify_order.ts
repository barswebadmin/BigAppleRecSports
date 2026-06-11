import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { createShopifyClient } from "../lib/clients/shopify/client.ts";
import { findOrderByName } from "../lib/clients/shopify/order_ops.ts";

export const FetchShopifyOrderFunction = DefineFunction({
    callback_id: "fetch_shopify_order",
    title: "Fetch Shopify Order",
    source_file: "functions/fetch_shopify_order.ts",
    input_parameters: {
        properties: {
            order_number: { type: Schema.types.string },
        },
        required: ["order_number"],
    },
    output_parameters: {
        properties: {
            shopify_order_json: { type: Schema.types.string },
            found: { type: Schema.types.boolean },
            error: { type: Schema.types.string },
        },
        required: ["found"],
    },
});

export default SlackFunction(FetchShopifyOrderFunction, async ({ inputs, env }) => {
    try {
        const client = createShopifyClient(env);
        const result = await findOrderByName(client, inputs.order_number);

        if (!result.ok || !result.order) {
            return { outputs: { found: false, error: result.error ?? "Order not found" } };
        }

        return { outputs: { shopify_order_json: JSON.stringify(result.order), found: true } };
    } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[fetch_order] ${msg}`);
        return { outputs: { found: false, error: msg } };
    }
});
