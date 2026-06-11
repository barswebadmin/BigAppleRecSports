import type { Trigger } from "deno-slack-sdk/types.ts";
import { TriggerContextData, TriggerTypes } from "deno-slack-api/mod.ts";
import GetShopifyOrdersWorkflow from "../workflows/get_shopify_orders_workflow.ts";

const trigger: Trigger<typeof GetShopifyOrdersWorkflow.definition> = {
    type: TriggerTypes.Shortcut,
    name: "Registrations - fetch orders from Shopify",
    description: "Select a season and league to fetch order data from Shopify",
    workflow: `#/workflows/${GetShopifyOrdersWorkflow.definition.callback_id}`,
    inputs: {
        interactivity: {
            value: TriggerContextData.Shortcut.interactivity,
        },
        channel_id: {
            value: TriggerContextData.Shortcut.channel_id,
        },
        user_id: {
            value: TriggerContextData.Shortcut.user_id,
        },
    },
};

export default trigger;
