/** Locate a single waitlist row from a Shopify order-paid webhook payload and
 *  project it to the `WaitlistAction[]` wire format the downstream
 *  `update_waitlist_spreadsheet` step consumes. Pure function — no I/O. */

import { buildLeagueKey } from "../league/identity.ts";
import type { WaitlistAction } from "./types.ts";
import type { LeagueWaitlists } from "./types.ts";
import type { WaitlistSignupPayload } from "./signup_payload.ts";

/** Returns a single-element `actions` list, or `[]` when the body is malformed,
 *  the league is unknown, or the email isn't on that league's waitlist. */
export function resolveWaitlistOrder(inputs: {
    body: string;
    waitlists_json: string;
}): WaitlistAction[] {
    let payload: WaitlistSignupPayload;
    try {
        payload = JSON.parse(inputs.body) as WaitlistSignupPayload;
    } catch {
        console.error("[resolve_order] invalid JSON body");
        return [];
    }

    const { email, sport, day, division, order_number } = payload;
    const leagueKey = buildLeagueKey(sport, day, division);
    console.log(`[resolve_order] order #${order_number ?? "?"} for ${email} in ${leagueKey}`);

    const waitlists = JSON.parse(inputs.waitlists_json) as LeagueWaitlists;
    const league = waitlists.leagues[leagueKey];
    if (!league) {
        console.log(`[resolve_order] no league found for ${leagueKey}`);
        return [];
    }

    const entry = league.entries.find(
        (e) => e.emailAddress.toLowerCase() === email.toLowerCase(),
    );
    if (!entry) {
        console.log(`[resolve_order] ${email} not found on ${leagueKey} waitlist`);
        return [];
    }

    console.log(
        `[resolve_order] resolved row ${entry.rowNumber} (${entry.firstName} ${entry.emailAddress})`,
    );
    return [{
        type: "order",
        rowNumber: String(entry.rowNumber),
        firstName: entry.firstName,
        emailAddress: entry.emailAddress,
    }];
}
