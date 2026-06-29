/** Generic test/review channel routing. The global `ENV` decides the default;
 *  any caller can additionally flag a single message as test via `is_test`. */

import { ENV } from "../../config/store.ts";

export interface ChannelPair {
    test: string;
    review: string;
}

/** Route a Slack post to the test or review channel. Test takes precedence
 *  when (a) the app is not running in `ENV=prod`, or (b) the caller flags this
 *  specific message as a test (e.g. payload from a sandboxed upstream). */
export function resolveChannel(
    channels: ChannelPair,
    { is_test = false }: { is_test?: boolean } = {},
): string {
    const useTest = ENV !== "prod" || is_test;
    return useTest ? channels.test : channels.review;
}

/**
 * Refund-flow channel resolver. Precedence (highest first):
 *
 *   1. `args.requested` — operator-supplied via the picker modal's
 *      "post to channel" input.
 *   2. `args.env.SLACK_CHANNEL__REFUNDS__DEFAULT` — env override (canonical
 *      double-underscore name; matches the workspace convention).
 *   3. Hardcoded fallback `"#joe-test"`.
 *
 * The new `/eval-refund-request` flow reads ONLY this var. The existing
 * webhook-driven refund-evaluation flow continues to use
 * `REFUND_TEST_CHANNEL` / `REFUND_REVIEW_CHANNEL` (consumed via
 * `getStaticChannels("refund")`).
 */
export function resolveRefundChannel(args: {
    requested: string | null;
    env: Record<string, string>;
}): string {
    return (
        args.requested?.trim() ||
        args.env.SLACK_CHANNEL__REFUNDS__DEFAULT ||
        "#joe-test"
    );
}
