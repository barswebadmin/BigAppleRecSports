/** Structured outcome data for waitlist row processing. The planner and
 *  executor only produce these — UI text generation (mrkdwn notes, bullet
 *  copy) lives in `views/waitlist/` and consumes the kind+payload. */

// ── Shopify-tag planning outcome ──────────────────────────────────────────

export type ShopifyTagOutcome =
    | { kind: "no_product"; expectedHandle: string }
    | { kind: "noop"; waitlistTag: string }
    | { kind: "update"; customerId: string; finalTags: string[] }
    | { kind: "create"; emailAddress: string; waitlistTag: string };

// ── Email planning outcome ────────────────────────────────────────────────

export type EmailOutcome =
    | { kind: "send" }
    | { kind: "skip_unchecked" }
    | { kind: "skip_no_address" };

// ── Per-row executed outcome (drives the channel summary bullet) ──────────
