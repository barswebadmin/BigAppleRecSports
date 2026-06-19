/** UI text generators for dry-run notes. Map structured outcome data from the
 *  planner (`domain/waitlist/outcomes.ts`) into Slack mrkdwn copy. Pure — the
 *  planner emits no UI text at all. */

import type { EmailOutcome, ShopifyTagOutcome } from "../../domain/waitlist/outcomes.ts";

/** Shopify-side note shown in the dry-run preview when the planner emitted no
 *  request (no-op, no product, etc.). For real mutations, the dry-run renderer
 *  shows the full request bytes instead, and this note isn't displayed. */
export function formatShopifyDryRunNote(o: ShopifyTagOutcome): string {
    switch (o.kind) {
        case "no_product":
            return `:warning: Shopify: no product found for handle \`${o.expectedHandle}\` — check season/year config. No tag will be applied.`;
        case "noop":
            return `Shopify: customer already has \`${o.waitlistTag}\` — no mutation needed.`;
        case "update":
            return `Shopify: update existing customer \`${o.customerId}\` → tags become [${
                o.finalTags.join(", ")
            }].`;
        case "create":
            return `Shopify: no customer for ${o.emailAddress} → create with tag \`${o.waitlistTag}\`.`;
    }
}

/** Email-side note shown in the dry-run preview when no email request was
 *  built. Returns `null` for outcomes that produce no preview note. */
export function formatEmailDryRunNote(o: EmailOutcome): string | null {
    switch (o.kind) {
        case "send":
            return null;
        case "skip_unchecked":
            return "Email: box unticked → no email will be sent (tag only).";
        case "skip_no_address":
            return null;
    }
}

// ============================================================================

// ============================================================================

// No generic helpers — every generator here renders waitlist-specific outcome data.
