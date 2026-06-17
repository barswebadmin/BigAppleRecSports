/** Refund routing: channels, lambda URL, dry-run switch, outgoing-domain allowlist. */

import { ENV, envOr, readEnv } from "./env.ts";
import { STORE_MYSHOPIFY_DOMAIN } from "./store.ts";

export const REFUND_TEST_CHANNEL = envOr("REFUND_TEST_CHANNEL", "#joe-test");
export const REFUND_REVIEW_CHANNEL = envOr("REFUND_REVIEW_CHANNEL", "#exec-leadership-2026");

/**
 * ShopifyRefundHandler Lambda Function URL — receives the approve/process POST
 * when a reviewer confirms a refund. Auth is NONE, so treat the URL as
 * semi-secret. Its host (derived below) must be in `OUTGOING_DOMAINS`.
 */
export const REFUND_PROCESS_URL = envOr(
    "REFUND_PROCESS_URL",
    "https://7wfkjr4jk5hbchf23venzdm3te0yaouc.lambda-url.us-east-1.on.aws/",
);
export const REFUND_PROCESS_DOMAIN = new URL(REFUND_PROCESS_URL).host;

/**
 * In non-prod, approving a refund POSTs the cancel/refund payloads to the test
 * channel as a preview instead of hitting the Lambda — letting us validate the
 * irreversible Shopify calls before they fire. `ENV=prod` (or an explicit
 * `REFUND_DRY_RUN` override) sends them for real.
 */
export const REFUND_DRY_RUN = (readEnv("REFUND_DRY_RUN") ?? String(ENV !== "prod")) === "true";

/**
 * Route a refund review message. In test mode everything stays in the test
 * channel; in prod only requests explicitly flagged `is_test` divert there.
 */
export function resolveRefundChannel(opts: { is_test?: boolean }): string {
    const useTest = ENV === "test" || opts.is_test === true;
    return useTest ? REFUND_TEST_CHANNEL : REFUND_REVIEW_CHANNEL;
}

/** Every external host the app calls. Single source for `manifest.outgoingDomains`. */
export const OUTGOING_DOMAINS = [
    "www.googleapis.com",
    "sheets.googleapis.com",
    "gmail.googleapis.com",
    "oauth2.googleapis.com",
    STORE_MYSHOPIFY_DOMAIN,
    REFUND_PROCESS_DOMAIN,
];
