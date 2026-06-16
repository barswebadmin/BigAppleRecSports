import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { columnToLetter, getOrCreateGoogleClient } from "../lib/clients/google/client.ts";
import {
    resolveStatusColumnIndex,
    WAITLIST_SPREADSHEET_ID,
    WAITLIST_TAB,
} from "../lib/waitlists/sheet_service.ts";
import type { WaitlistAction } from "../lib/waitlists/waitlist_action.ts";

export function formatStatusTimestamp(): string {
    const now = new Date();
    const month = now.getMonth() + 1;
    const day = now.getDate();
    let hours = now.getHours();
    const minutes = now.getMinutes().toString().padStart(2, "0");
    const ampm = hours >= 12 ? "pm" : "am";
    hours = hours % 12 || 12;
    return `${month}/${day} at ${hours}:${minutes} ${ampm}`;
}

export function statusText(type: string, timestamp: string): string {
    switch (type) {
        case "admit":
            return `Admitted on ${timestamp}`;
        case "remove":
            return `Cancelled on ${timestamp}`;
        case "order":
            return `Registered on ${timestamp}`;
        default:
            return `Updated on ${timestamp}`;
    }
}

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
    if (actions.length === 0) return { outputs: {} };

    try {
        const google = getOrCreateGoogleClient(env);
        const timestamp = formatStatusTimestamp();
        // Locate the Status column by header name once, so writes land in the right
        // cell regardless of the sheet's column order.
        const statusCol = await resolveStatusColumnIndex(env);

        const updates = actions.map((action) => ({
            row: Number(action.rowNumber),
            col: statusCol,
            value: statusText(action.type, timestamp),
        }));

        await google.updateCells(WAITLIST_SPREADSHEET_ID, WAITLIST_TAB.name, updates);

        for (const action of actions) {
            const cell = `${columnToLetter(statusCol)}${action.rowNumber}`;
            console.log(
                `[update_sheet] ${cell}: "${
                    statusText(action.type, timestamp)
                }" (${action.firstName} ${action.emailAddress})`,
            );
        }
    } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[update_sheet] ${msg}`);
    }

    return { outputs: {} };
});
