import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { getOrCreateGoogleClient } from "../lib/clients/google/client.ts";
import { GOOGLE_SHEETS } from "../config.ts";

const SHEET = GOOGLE_SHEETS.waitlists;

function formatStatusTimestamp(): string {
    const now = new Date();
    const month = now.getMonth() + 1;
    const day = now.getDate();
    let hours = now.getHours();
    const minutes = now.getMinutes().toString().padStart(2, "0");
    const ampm = hours >= 12 ? "pm" : "am";
    hours = hours % 12 || 12;
    return `${month}/${day} at ${hours}:${minutes} ${ampm}`;
}

function statusText(type: string, timestamp: string): string {
    switch (type) {
        case "admit":
            return `Contacted on ${timestamp}`;
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
    title: "Update Waitlist Spreadsheet",
    source_file: "functions/update_waitlist_spreadsheet.ts",
    input_parameters: {
        properties: {
            actions_json: { type: Schema.types.string },
        },
        required: ["actions_json"],
    },
    output_parameters: { properties: {}, required: [] },
});

interface WaitlistAction {
    type: "admit" | "remove" | "order";
    rowNumber: string;
    firstName: string;
    emailAddress: string;
}

export default SlackFunction(UpdateWaitlistSpreadsheetFunction, async ({ inputs, env }) => {
    const actions = JSON.parse(inputs.actions_json) as WaitlistAction[];
    if (actions.length === 0) return { outputs: {} };

    try {
        const google = getOrCreateGoogleClient(env);
        const timestamp = formatStatusTimestamp();

        for (const action of actions) {
            const status = statusText(action.type, timestamp);

            await google.updateSpreadsheet(
                SHEET.spreadsheet_id,
                { name: SHEET.tab_name, id: SHEET.tab_id },
                `J${action.rowNumber}`,
                [[status]],
            );

            console.log(
                `[update_sheet] row ${action.rowNumber}: "${status}" (${action.firstName} ${action.emailAddress})`,
            );
        }
    } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[update_sheet] ${msg}`);
    }

    return { outputs: {} };
});
