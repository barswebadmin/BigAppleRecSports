import { Manifest } from "deno-slack-sdk/mod.ts";
import ProcessWaitlistSignupsWorkflow from "./workflows/process_waitlist_signups.ts";
import ReceiveWaitlistOrderWorkflow from "./workflows/receive_waitlist_signup.ts";
import GetShopifyOrdersWorkflow from "./workflows/get_shopify_orders_workflow.ts";
import DryRunWaitlistWorkflow from "./workflows/dry_run_waitlist.ts";
import EvaluateRefundRequestWorkflow from "./workflows/evaluate_refund_request.ts";
import { barsApiDomain, REFUND_PROCESS_DOMAIN, STORE_MYSHOPIFY_DOMAIN } from "./config/store.ts";

/** Every external host the app calls. Slack blocks any fetch to a host not
 *  listed here, so each integration contributes its host(s) directly. */
const barsApiHost = barsApiDomain();
const OUTGOING_DOMAINS = [
    "www.googleapis.com",
    "sheets.googleapis.com",
    "gmail.googleapis.com",
    "oauth2.googleapis.com",
    STORE_MYSHOPIFY_DOMAIN,
    REFUND_PROCESS_DOMAIN,
    ...(barsApiHost && barsApiHost !== REFUND_PROCESS_DOMAIN ? [barsApiHost] : []),
];

export default Manifest({
    name: "Registrations",
    description: "Registration management — waitlists, cancellations, refunds",
    icon: "assets/registrations.png",
    workflows: [
        ProcessWaitlistSignupsWorkflow,
        ReceiveWaitlistOrderWorkflow,
        GetShopifyOrdersWorkflow,
        DryRunWaitlistWorkflow,
        EvaluateRefundRequestWorkflow,
    ],
    outgoingDomains: OUTGOING_DOMAINS,
    botScopes: ["commands", "chat:write", "chat:write.public"],
});
