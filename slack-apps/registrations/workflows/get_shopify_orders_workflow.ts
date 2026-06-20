import { DefineWorkflow, Schema } from "deno-slack-sdk/mod.ts";
import { GetLeagueSelectionsFunction } from "../functions/get_league_selections_from_modal.ts";

const GetShopifyOrdersWorkflow = DefineWorkflow({
    callback_id: "shopify_order_workflow",
    title: "Registrations - fetch orders from Shopify",
    input_parameters: {
        properties: {
            interactivity: { type: Schema.slack.types.interactivity },
            channel_id: { type: Schema.slack.types.channel_id },
            user_id: { type: Schema.slack.types.user_id },
        },
        required: ["interactivity"],
    },
});

// Step 1: Call your function
GetShopifyOrdersWorkflow.addStep(GetLeagueSelectionsFunction, {
    interactivity: GetShopifyOrdersWorkflow.inputs.interactivity,
});

export default GetShopifyOrdersWorkflow;
