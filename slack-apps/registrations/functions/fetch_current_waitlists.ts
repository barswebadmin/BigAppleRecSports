/** Workflow step: pull the waitlist sheet and return JSON.
 *  All real work lives in `domain/waitlist/`; this is SDK wiring only. */

import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";

import { fetchWaitlistsOrEmpty } from "../domain/waitlist/sheet.ts";

export const FetchCurrentWaitlistsFunction = DefineFunction({
    callback_id: "fetch_current_waitlists",
    title: "Fetch Current Waitlists",
    source_file: "functions/fetch_current_waitlists.ts",
    input_parameters: {
        properties: {},
        required: [],
    },
    output_parameters: {
        properties: {
            waitlists_json: { type: Schema.types.string },
        },
        required: ["waitlists_json"],
    },
});

export default SlackFunction(FetchCurrentWaitlistsFunction, async ({ env }) => {
    const waitlists = await fetchWaitlistsOrEmpty(env);
    return { outputs: { waitlists_json: JSON.stringify(waitlists) } };
});
