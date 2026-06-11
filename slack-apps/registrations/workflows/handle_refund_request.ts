import { DefineWorkflow } from "deno-slack-sdk/mod.ts";
import { FetchShopifyOrderFunction } from "../functions/fetch_shopify_order.ts";
import { ValidateRefundRequestDetailsFunctionDefinition } from "../functions/validate_refund_request_details.ts";
import { HandleRefundRequestFunctionDefinition } from "../functions/handle_refund_request.ts";
import { RefundRequestType } from "../types/refund_request.ts";

const HandleRefundRequestWorkflow = DefineWorkflow({
    callback_id: "refund_request_workflow",
    title: "Handle Refund Request",
    description:
        "Receives a refund request via webhook, fetches the Shopify order, validates, and processes it",
    input_parameters: {
        properties: {
            refund_request: { type: RefundRequestType },
        },
        required: ["refund_request"],
    },
});

const fetchStep = HandleRefundRequestWorkflow.addStep(FetchShopifyOrderFunction, {
    order_number: HandleRefundRequestWorkflow.inputs.refund_request.order_number,
});

const validateStep = HandleRefundRequestWorkflow.addStep(
    ValidateRefundRequestDetailsFunctionDefinition,
    {
        refund_request: HandleRefundRequestWorkflow.inputs.refund_request,
        shopify_order_json: fetchStep.outputs.shopify_order_json,
    },
);

HandleRefundRequestWorkflow.addStep(HandleRefundRequestFunctionDefinition, {
    refund_request: HandleRefundRequestWorkflow.inputs.refund_request,
    shopify_order_json: fetchStep.outputs.shopify_order_json,
    email_matches: validateStep.outputs.email_matches,
    order_is_not_cancelled: validateStep.outputs.order_is_not_cancelled,
    order_is_not_refunded: validateStep.outputs.order_is_not_refunded,
});

export default HandleRefundRequestWorkflow;
