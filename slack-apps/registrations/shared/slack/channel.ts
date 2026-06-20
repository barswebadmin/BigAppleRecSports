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
