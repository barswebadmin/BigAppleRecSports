import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { buildLeagueKey } from "../lib/waitlists/league_key.ts";
import type { LeagueWaitlists } from "../lib/waitlists/handlers/waitlist_entry_types.ts";
import type { WaitlistAction } from "../lib/waitlists/waitlist_action.ts";
import type { WaitlistSignupPayload } from "../types/waitlist_signup_payload.ts";

export const ResolveWaitlistOrderFunction = DefineFunction({
    callback_id: "resolve_waitlist_order",
    title: "Resolve Waitlist Order",
    source_file: "functions/resolve_waitlist_order.ts",
    input_parameters: {
        properties: {
            body: { type: Schema.types.string },
            waitlists_json: { type: Schema.types.string },
        },
        required: ["body", "waitlists_json"],
    },
    output_parameters: {
        properties: {
            actions_json: { type: Schema.types.string },
        },
        required: ["actions_json"],
    },
});

/** Handler body — exported for in-process regression tests (Stage 8). */
export function resolveWaitlistOrder(inputs: {
    body: string;
    waitlists_json: string;
}): { outputs: { actions_json: string } } {
    let payload: WaitlistSignupPayload;
    try {
        payload = JSON.parse(inputs.body) as WaitlistSignupPayload;
    } catch {
        console.error("[resolve_order] invalid JSON body");
        return { outputs: { actions_json: "[]" } };
    }

    const { email_address, sport, day, division, order_number } = payload;
    const leagueKey = buildLeagueKey(sport, day, division);
    console.log(
        `[resolve_order] order #${order_number ?? "?"} for ${email_address} in ${leagueKey}`,
    );

    const waitlists = JSON.parse(inputs.waitlists_json) as LeagueWaitlists;
    const league = waitlists.leagues[leagueKey];
    if (!league) {
        console.log(`[resolve_order] no league found for ${leagueKey}`);
        return { outputs: { actions_json: "[]" } };
    }

    const entry = league.entries.find(
        (e) => e.emailAddress.toLowerCase() === email_address.toLowerCase(),
    );
    if (!entry) {
        console.log(`[resolve_order] ${email_address} not found on ${leagueKey} waitlist`);
        return { outputs: { actions_json: "[]" } };
    }

    const actions: WaitlistAction[] = [
        {
            type: "order",
            rowNumber: String(entry.rowNumber),
            firstName: entry.firstName,
            emailAddress: entry.emailAddress,
        },
    ];

    console.log(
        `[resolve_order] resolved row ${entry.rowNumber} (${entry.firstName} ${entry.emailAddress})`,
    );
    return { outputs: { actions_json: JSON.stringify(actions) } };
}

export default SlackFunction(
    ResolveWaitlistOrderFunction,
    ({ inputs }) => resolveWaitlistOrder(inputs),
);
