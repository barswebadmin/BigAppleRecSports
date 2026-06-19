/** Shared access to the waitlist spreadsheet: one place that knows the
 *  sheet/tab/range and turns raw rows into structured leagues. Status column is
 *  resolved in the same fetch — no second HTTP call from writers. */

import { getOrCreateGoogleClient } from "../../shared/google/client.ts";
import { WORKFLOWS } from "../../config/workflows.ts";
import { parseWaitlistRows } from "./parse.ts";
import type { LeagueWaitlists } from "./types.ts";

const SHEET = WORKFLOWS.waitlist.sheet;
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

/** Soft-fail fallback used when a workflow step must always succeed (a thrown
 *  step strands the run). Mirrors a fresh `LeagueWaitlists` with no rows. */
const EMPTY_WAITLISTS: LeagueWaitlists = {
    leagues: {},
    byEmail: {},
    url: "",
    statusColumnIndex: -1,
};

/** Same as `fetchWaitlists` but converts any thrown error into `EMPTY_WAITLISTS`
 *  + a `console.error` trace. Use from Slack-function steps where the workflow
 *  can't recover from a thrown step. */
export async function fetchWaitlistsOrEmpty(
    env: Record<string, string>,
): Promise<LeagueWaitlists> {
    try {
        return await fetchWaitlists(env);
    } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[fetch_waitlists] ${msg}`);
        return EMPTY_WAITLISTS;
    }
}

/** Deep link to the waitlist tab (no specific cell). */
export function waitlistSheetUrl(): string {
    return `https://docs.google.com/spreadsheets/d/${SHEET.spreadsheet_id}/edit?gid=${WAITLIST_TAB.id}#gid=${WAITLIST_TAB.id}`;
}
