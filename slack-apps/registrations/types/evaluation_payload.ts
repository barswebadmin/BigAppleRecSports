/**
 * Wire contract for the payload the ShopifyRefundHandler Lambda POSTs to the
 * Deno evaluation webhook.
 *
 * Field names are snake_case to mirror the Lambda's `RefundResponse.to_json()`
 * output verbatim (see aws/lambda/functions/ShopifyRefundHandler/handler.py).
 * The Lambda only needs to echo the requester fields it received — no other
 * reshaping, and no channel (Slack owns routing).
 */

/** Mirror of `_estimate_payload()` in handler.py. */
export interface RefundEstimate {
    success: boolean;
    amount: number;
    percentage: number | null;
    penalty: number | null;
    timing: string | null;
    has_processing_fee: boolean;
    no_payment: boolean;
    message: string | null;
}

/** Mirror of `RefundResponse.to_json()` + echoed request fields. */
export interface RefundEvaluationPayload {
    // When true, the review message routes to the test channel instead of the
    // league channel. Lets the Lambda (or a manual post) exercise the flow safely.
    isTest?: boolean;

    // ── Echoed from the original request (Lambda adds these) ───────────────
    email_address: string;
    first_name: string;
    last_name: string;
    refund_or_credit: string; // "refund" | "credit"
    notes?: string | null;

    // ── League (Lambda resolves from the order's product) ────────────────--
    sport: string | null;
    day: string | null;
    division: string | null;

    // ── Product (Lambda echoes the order's first line-item product) ────────-
    // product_id is the Shopify GID (gid://shopify/Product/<n>); Deno builds the
    // admin URL from it. product_title is the link text.
    product_id: string | null;
    product_title: string | null;

    // ── Order facts ────────────────────────────────────────────────────────
    order_number: string;
    order_id: string | null;
    order_found: boolean;
    order_total: number | null;
    total_refunded: number | null;
    refundable_balance: number | null;
    is_cancelled: boolean | null;

    // ── Validation ───────────────────────────────────────────────────────--
    validation_passed: boolean;
    warnings: string[];
    email_matched_against?: string | null;
    first_name_matched_against?: string | null;
    last_name_matched_against?: string | null;

    // ── Refund-timing diagnostics ────────────────────────────────────────--
    // What the Lambda parsed as the season start (null = unparseable from the
    // product description) and where the submission landed in the week ladder.
    season_start_date: string | null;
    season_week_resolved: string | null;

    // ── Estimates (both ladders) ─────────────────────────────────────────--
    estimated_refund_to_original: RefundEstimate | null;
    estimated_store_credit: RefundEstimate | null;

    error?: string | null;
}
