/**
 * Shared access to the waitlist spreadsheet: a single place that knows the
 * sheet/tab/range and how to turn raw rows into structured leagues, plus how to
 * locate the Status column by name. Reused by the fetch, action, and write
 * functions so none of them re-encode the sheet layout.
 */

import { columnToLetter, getOrCreateGoogleClient } from "../clients/google/client.ts";
import { GOOGLE_SHEETS } from "../../config.ts";
import { findColumn, parseWaitlistRows } from "./handlers/sheet_parser.ts";
import type { LeagueWaitlists } from "./handlers/waitlist_entry_types.ts";

const SHEET = GOOGLE_SHEETS.waitlists;
export const WAITLIST_SPREADSHEET_ID = SHEET.spreadsheet_id;
export const WAITLIST_TAB = { name: SHEET.tab_name, id: SHEET.tab_id };

/** Columns A..J span every field the parser reads (incl. Status). */
const PARSE_RANGE = "A1:J";

/** Fetch and parse the waitlist sheet into structured leagues. */
export async function fetchWaitlists(env: Record<string, string>): Promise<LeagueWaitlists> {
    const google = getOrCreateGoogleClient(env);
    const { url, values } = await google.getSpreadsheet(
        SHEET.spreadsheet_id,
        WAITLIST_TAB,
        PARSE_RANGE,
    );
    return parseWaitlistRows(values, url);
}

/**
 * Resolve the Status column's 0-based index by matching the header row by name
 * (same case-insensitive substring match the parser uses). Targeting the column
 * by name keeps writes correct even if the sheet layout shifts, instead of
 * trusting a hard-coded column.
 */
/** Deep link to the waitlist tab (no specific cell). */
export function waitlistSheetUrl(): string {
    return `https://docs.google.com/spreadsheets/d/${SHEET.spreadsheet_id}/edit?gid=${WAITLIST_TAB.id}#gid=${WAITLIST_TAB.id}`;
}

/**
 * Deep link to a single cell in the waitlist tab. `colIndex` is 0-based (the
 * canonical form used everywhere); row is 1-based as shown in the UI. The
 * `range=` fragment focuses the cell when the sheet opens.
 */
export function waitlistCellUrl(colIndex: number, row: number): string {
    const cell = `${columnToLetter(colIndex)}${row}`;
    return `https://docs.google.com/spreadsheets/d/${SHEET.spreadsheet_id}/edit#gid=${WAITLIST_TAB.id}&range=${cell}`;
}

export async function resolveStatusColumnIndex(env: Record<string, string>): Promise<number> {
    const google = getOrCreateGoogleClient(env);
    const { values } = await google.getSpreadsheet(SHEET.spreadsheet_id, WAITLIST_TAB, "A1:Z1");
    const idx = findColumn(values[0] ?? [], "status");
    if (idx < 0) throw new Error(`No "Status" column found in '${WAITLIST_TAB.name}' header row`);
    return idx;
}
