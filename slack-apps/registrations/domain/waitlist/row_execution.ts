/** Real-run phase: execute the writes that `row_planning.ts` prepared. Mutates
 *  the row's `ActionResult` in place — success flags and error notes are
 *  consumed by the channel summary builder. */

// TODO(shopify-error-differentiation): today every Shopify failure is treated
// as a per-row failure (surfaced individually; other rows still run).
// Differentiate by classification (see ShopifyClient.gqlClassified):
//   - Client/transport-level failures that recur for every row in this
//     execution — BAD_REQUEST (malformed input) or FORBIDDEN (bad auth/token)
//     — should ABORT the remaining admit→email steps when >1 person is being
//     processed, and report *why* (bad request vs. bad auth) once.
//   - Failures specific to a single row (e.g. customerCreate userErrors) should
//     NOT abort the batch; keep going and surface each one in the Slack summary.

import { shopifyCustomerAdminUrl } from "../../config/store.ts";
import { executeCustomerTag } from "../../legacy/shopify_client/customer_ops.ts";
import type { createShopifyClient } from "../../legacy/shopify_client/client.ts";
import { executeSendEmail } from "../../shared/google/gmail.ts";
import type { RowProcessing } from "./row_planning.ts";

async function executeShopifyForRow(
    shopify: ReturnType<typeof createShopifyClient>,
    p: RowProcessing,
): Promise<void> {
    if (!p.tagPlan) return;
    try {
        const res = await executeCustomerTag(shopify, p.tagPlan);
        if (!res.ok) {
            p.result.shopifyOk = false;
            p.result.shopifyError = res.error;
        } else if (res.customer?.id) {
            p.result.customerAdminUrl = shopifyCustomerAdminUrl(res.customer.id);
        }
    } catch (e) {
        p.result.shopifyOk = false;
        p.result.shopifyError = e instanceof Error ? e.message : String(e);
        console.error(`[shopify:${p.result.rowNumber}]`, e);
    }
}

/** Email only when the box was ticked AND Shopify succeeded — the login link
 *  is useless without the tag, so a Shopify failure cancels the email. */
async function executeEmailForRow(p: RowProcessing): Promise<void> {
    if (!p.emailRequest || !p.result.shopifyOk) return;
    try {
        const emailRes = await executeSendEmail(p.emailRequest);
        if (!emailRes.ok) {
            p.result.emailOk = false;
            p.result.emailError = emailRes.error;
        } else {
            p.result.emailed = true;
        }
    } catch (e) {
        p.result.emailOk = false;
        p.result.emailError = e instanceof Error ? e.message : String(e);
        console.error(`[email:${p.result.rowNumber}]`, e);
    }
}

export async function executeRowProcessing(
    shopify: ReturnType<typeof createShopifyClient>,
    p: RowProcessing,
): Promise<void> {
    if (p.type !== "admit" || !p.entry) return;
    await executeShopifyForRow(shopify, p);
    await executeEmailForRow(p);
}
