/** Workflow step: take a webhook body + cached waitlist payload, resolve the
 *  one matching row, return it as `actions_json`. Pure delegation to
 *  `domain/waitlist/resolve.ts`. */

import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";

import { resolveWaitlistOrder } from "../domain/waitlist/resolve.ts";

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

export default SlackFunction(ResolveWaitlistOrderFunction, ({ inputs }) => ({
    outputs: { actions_json: JSON.stringify(resolveWaitlistOrder(inputs)) },
}));
