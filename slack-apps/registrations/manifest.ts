import { Manifest } from "deno-slack-sdk/mod.ts";
import ProcessWaitlistSignupsWorkflow from "./workflows/process_waitlist_signups.ts";
import ReceiveWaitlistOrderWorkflow from "./workflows/receive_waitlist_signup.ts";
import GetShopifyOrdersWorkflow from "./workflows/get_shopify_orders_workflow.ts";
import DryRunWaitlistWorkflow from "./workflows/dry_run_waitlist.ts";
import EvaluateRefundRequestWorkflow from "./workflows/evaluate_refund_request.ts";
import { OUTGOING_DOMAINS } from "./config/refunds.ts";

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
