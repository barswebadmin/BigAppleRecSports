import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import type { LeagueWaitlists } from "../lib/waitlists/handlers/waitlist_entry_types.ts";

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

interface OrderPayload {
    email_address: string;
    sport: string;
    day_of_play: string;
    division: string;
    order_number?: string;
}

export default SlackFunction(ResolveWaitlistOrderFunction, ({ inputs }) => {
    let payload: OrderPayload;
    try {
        payload = JSON.parse(inputs.body) as OrderPayload;
    } catch {
        console.error("[resolve_order] invalid JSON body");
        return { outputs: { actions_json: "[]" } };
    }

    const { email_address, sport, day_of_play, division, order_number } = payload;
    const leagueKey = `${sport}|${day_of_play}|${division}`;
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

    const actions = [
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
});
