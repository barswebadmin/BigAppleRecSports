/** Workflow step: persist Status-column writes for actions queued by the
 *  waitlist-actions handler. SDK wiring only — the write itself is in
 *  `domain/waitlist/status_write.ts`. */

import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";

import type { WaitlistAction } from "../domain/waitlist/types.ts";
import { applyStatusWrites } from "../domain/waitlist/status_write.ts";

export const UpdateWaitlistSpreadsheetFunction = DefineFunction({
    callback_id: "update_waitlist_spreadsheet",
    // Neutral, truthful in both cases: on admit/remove it records the Status
    // write; on a cancelled run (empty actions_json) it no-ops. Avoids the
    // misleading "Saving updates…" progress toast when nothing was processed.
    title: "Finishing up",
    source_file: "functions/update_waitlist_spreadsheet.ts",
    input_parameters: {
        properties: {
            actions_json: { type: Schema.types.string },
        },
        required: ["actions_json"],
    },
    output_parameters: { properties: {}, required: [] },
});

export default SlackFunction(UpdateWaitlistSpreadsheetFunction, async ({ inputs, env }) => {
    const actions = JSON.parse(inputs.actions_json) as WaitlistAction[];
    await applyStatusWrites(env, actions);
    return { outputs: {} };
});
