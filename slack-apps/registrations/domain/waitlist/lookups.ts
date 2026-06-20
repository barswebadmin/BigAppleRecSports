/** Pure lookups over the waitlist data structures. */

import type { EmailLookupEntry } from "./types.ts";

/** Every other league this email is on, excluding `currentLeagueKey`. Returns
 *  `[]` when the email isn't in the index or only appears on the current
 *  league. Case-insensitive on email. */
export function otherWaitlistsFor(
    email: string,
    currentLeagueKey: string,
    byEmail: Record<string, EmailLookupEntry[]>,
): EmailLookupEntry[] {
    return (byEmail[email.toLowerCase()] ?? [])
        .filter((e) => e.leagueKey !== currentLeagueKey);
}
