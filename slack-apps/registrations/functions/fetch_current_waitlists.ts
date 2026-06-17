/** Workflow step: pull the waitlist sheet, log a debug summary, return JSON.
 *  All real work lives in `domain/waitlist/`; this is SDK wiring + fallback. */

import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";

import { logWaitlistsSummary } from "../domain/waitlist/debug.ts";
import { fetchWaitlists } from "../domain/waitlist/sheet.ts";

/** Soft-fail payload returned when the sheet fetch raises — the downstream
 *  workflow handles "no leagues" cleanly; throwing would mark the step failed. */
const EMPTY_WAITLISTS_JSON = JSON.stringify({
    leagues: {},
    byEmail: {},
    url: "",
    statusColumnIndex: -1,
});

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
    try {
        const waitlists = await fetchWaitlists(env);
        logWaitlistsSummary(waitlists);
        return { outputs: { waitlists_json: JSON.stringify(waitlists) } };
    } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[fetch_waitlists] ${msg}`);
        return { outputs: { waitlists_json: EMPTY_WAITLISTS_JSON } };
    }
});
