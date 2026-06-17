/** Shared access to the waitlist spreadsheet: one place that knows the
 *  sheet/tab/range and turns raw rows into structured leagues. Status column is
 *  resolved in the same fetch — no second HTTP call from writers. */

import { getOrCreateGoogleClient } from "../../shared/google/client.ts";
import { getWorkflowSheet } from "../../config/workflows.ts";
import { parseWaitlistRows } from "./parse.ts";
import type { LeagueWaitlists } from "./types.ts";

const SHEET = getWorkflowSheet("waitlist");
export const WAITLIST_SPREADSHEET_ID = SHEET.spreadsheet_id;
export const WAITLIST_TAB = { name: SHEET.tab_name, id: SHEET.tab_id };

/** Columns A..J span every field the parser reads (incl. Status). */
const PARSE_RANGE = "A1:J";

/** Fetch and parse the waitlist sheet into structured leagues. The returned
 *  payload carries `statusColumnIndex` so downstream writers don't need a
 *  second sheet round-trip to locate the column. */
export async function fetchWaitlists(env: Record<string, string>): Promise<LeagueWaitlists> {
    const google = getOrCreateGoogleClient(env);
    const { url, values } = await google.getSpreadsheet(
        SHEET.spreadsheet_id,
        WAITLIST_TAB,
        PARSE_RANGE,
    );
    const parsed = parseWaitlistRows(values, url);
    if (parsed.statusColumnIndex < 0) {
        throw new Error(`No "Status" column found in '${WAITLIST_TAB.name}' header row`);
    }
    return parsed;
}

/** Deep link to the waitlist tab (no specific cell). */
export function waitlistSheetUrl(): string {
    return `https://docs.google.com/spreadsheets/d/${SHEET.spreadsheet_id}/edit?gid=${WAITLIST_TAB.id}#gid=${WAITLIST_TAB.id}`;
}
