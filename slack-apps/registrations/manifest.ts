import { Manifest } from "deno-slack-sdk/mod.ts";
import ProcessWaitlistSignupsWorkflow from "./workflows/process_waitlist_signups.ts";
import ReceiveWaitlistOrderWorkflow from "./workflows/receive_waitlist_signup.ts";
import HandleRefundRequestWorkflow from "./workflows/handle_refund_request.ts";
import GetShopifyOrdersWorkflow from "./workflows/get_shopify_orders_workflow.ts";
import CheckWaitlistWorkflow from "./workflows/check_waitlist.ts";
import { RefundRequestType } from "./types/refund_request.ts";

export default Manifest({
    name: "Registrations",
    description: "Registration management — waitlists, cancellations, refunds",
    icon: "assets/registrations.png",
    workflows: [
        ProcessWaitlistSignupsWorkflow,
        ReceiveWaitlistOrderWorkflow,
        HandleRefundRequestWorkflow,
        GetShopifyOrdersWorkflow,
        CheckWaitlistWorkflow,
    ],
    outgoingDomains: [
        "www.googleapis.com",
        "sheets.googleapis.com",
        "gmail.googleapis.com",
        "oauth2.googleapis.com",
        "09fe59-3.myshopify.com",
    ],
    types: [RefundRequestType],
    botScopes: ["commands", "chat:write", "chat:write.public"],
});
