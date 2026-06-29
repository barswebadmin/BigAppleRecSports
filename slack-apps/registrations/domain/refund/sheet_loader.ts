/**
 * Sheet loader for the `Refund_Requests` Google Sheet. Reads the spreadsheet
 * id from `SHEET_ID__REFUND_REQUESTS` and the tab id from `TAB_ID__REFUND_REQUESTS`
 * (no defaults — fail fast at deploy if either is unset).
 *
 * The parser is parameterized by a field-name → substring-tokens map so the
 * matcher works against the live, free-form Google-Form question headers
 * regardless of column order. See design.md § "Column header resolution".
 */

import { findColumn } from "../../shared/google/columns.ts";
import { getOrCreateGoogleClient } from "../../shared/google/client.ts";
import type { RefundSheetData, RefundSheetEntry } from "./types.ts";

// ────────────────────────────────────────────────────────────────────────────
// Column-token constants (design.md § "Column header resolution")
//
// Tried in order; first case-insensitive substring match wins. Tokens were
// chosen to be unique against the live header set (e.g. `email` is unique;
// `name` would NOT be unique because both "First Name" and "Last Name"
// contain it).
// ────────────────────────────────────────────────────────────────────────────

export const TIMESTAMP_TOKENS = ["timestamp"] as const;
export const EMAIL_TOKENS = ["email"] as const;
export const ORDER_NUMBER_TOKENS = ["order number"] as const;
export const REFUND_OR_CREDIT_TOKENS = [
    "store credit",
    "original form",
    "refund",
] as const;
export const NOTES_TOKENS = ["anything else", "note about"] as const;
export const FIRST_NAME_TOKENS = ["first name"] as const;
export const LAST_NAME_TOKENS = ["last name"] as const;
export const TRANSFER_REQUEST_TOKENS = [
    "transfer to another day",
    "sport, day, and division",
] as const;
export const STATUS_TOKENS = ["status"] as const;

/** Range fetched from the tab — header + data, with headroom. The Sheets
 *  client drops rows whose first cell is empty. */
const SHEET_FETCH_RANGE = "A1:N";

const log = (fn: string, ...args: unknown[]) => console.log(`[refund_sheet_loader:${fn}]`, ...args);
const warn = (fn: string, ...args: unknown[]) =>
    console.warn(`[refund_sheet_loader:${fn}]`, ...args);

/** Reads an env var with a clear error message when absent. */
function requireEnv(env: Record<string, string>, key: string): string {
    const v = env[key];
    if (v && v.trim() !== "") return v;
    let fromDeno: string | undefined;
    try {
        fromDeno = Deno.env.get(key) ?? undefined;
    } catch {
        fromDeno = undefined;
    }
    if (fromDeno && fromDeno.trim() !== "") return fromDeno;
    throw new Error(
        `[refund_sheet_loader] required env var ${key} is not set; configure it before invoking the workflow.`,
    );
}

/** Try each candidate token in order; return the first matching column index,
 *  or `null` if none match. Logs a warning naming the field on full miss. */
function resolveColumn(
    headers: string[],
    fieldName: string,
    candidates: readonly string[],
): number | null {
    for (const c of candidates) {
        const idx = findColumn(headers, c);
        if (idx !== null) return idx;
    }
    warn(
        "resolveColumn",
        `no header matched any token for "${fieldName}" (tried: ${candidates.join(", ")})`,
    );
    return null;
}

/** Read a cell at `colIdx` from a row, returning `null` for missing/blank cells. */
function readCell(row: string[], colIdx: number | null): string | null {
    if (colIdx === null) return null;
    const v = row[colIdx];
    if (v === undefined || v === null) return null;
    const trimmed = String(v).trim();
    return trimmed === "" ? null : trimmed;
}

/** Strip a leading `#` from a Shopify order number (the live form sometimes
 *  collects values with the prefix; downstream API expects digits only). */
function normalizeOrderNumber(raw: string | null): string {
    if (!raw) return "";
    return raw.replace(/^#+/, "").trim();
}

interface ColumnIndex {
    timestamp: number | null;
    email: number | null;
    orderNumber: number | null;
    refundOrCredit: number | null;
    notes: number | null;
    firstName: number | null;
    lastName: number | null;
    transferRequest: number | null;
    status: number | null;
}

function buildColumnIndex(headers: string[]): ColumnIndex {
    return {
        timestamp: resolveColumn(headers, "timestamp", TIMESTAMP_TOKENS),
        email: resolveColumn(headers, "email", EMAIL_TOKENS),
        orderNumber: resolveColumn(headers, "orderNumber", ORDER_NUMBER_TOKENS),
        refundOrCredit: resolveColumn(
            headers,
            "refundOrCredit",
            REFUND_OR_CREDIT_TOKENS,
        ),
        notes: resolveColumn(headers, "notes", NOTES_TOKENS),
        firstName: resolveColumn(headers, "firstName", FIRST_NAME_TOKENS),
        lastName: resolveColumn(headers, "lastName", LAST_NAME_TOKENS),
        transferRequest: resolveColumn(
            headers,
            "transferRequest",
            TRANSFER_REQUEST_TOKENS,
        ),
        status: resolveColumn(headers, "status", STATUS_TOKENS),
    };
}

function parseRow(
    row: string[],
    rowNumber: number,
    cols: ColumnIndex,
): RefundSheetEntry {
    const statusCellValue = readCell(row, cols.status);
    return {
        rowNumber,
        timestamp: readCell(row, cols.timestamp) ?? "",
        email: readCell(row, cols.email) ?? "",
        firstName: readCell(row, cols.firstName) ?? "",
        lastName: readCell(row, cols.lastName) ?? "",
        orderNumber: normalizeOrderNumber(readCell(row, cols.orderNumber)),
        refundOrCredit: readCell(row, cols.refundOrCredit),
        notes: readCell(row, cols.notes),
        transferRequest: readCell(row, cols.transferRequest),
        statusCellValue,
        // Inlined per design — no isProcessedRow helper.
        isProcessed: !!statusCellValue?.trim(),
    };
}

/**
 * Fetch all unprocessed refund-request rows from the live sheet.
 *
 * Throws if the required env vars are absent or the Sheets call fails. The
 * `fetchRefundRequestsOrEmpty` variant catches errors and returns an empty
 * snapshot — used by handlers that want to render "no rows found" instead
 * of erroring the whole workflow.
 */
export async function fetchRefundRequests(
    env: Record<string, string>,
): Promise<RefundSheetData> {
    const spreadsheetId = requireEnv(env, "SHEET_ID__REFUND_REQUESTS");
    const tabId = requireEnv(env, "TAB_ID__REFUND_REQUESTS");

    const google = getOrCreateGoogleClient(env);
    const tab = { name: "Refund_Requests", id: tabId };
    const { url, values } = await google.getSpreadsheet(
        spreadsheetId,
        tab,
        SHEET_FETCH_RANGE,
    );

    if (values.length === 0) {
        warn("fetchRefundRequests", "sheet returned zero rows (header missing?)");
        return { url, spreadsheetId, tabId, unprocessed: [] };
    }

    const [headers, ...dataRows] = values;
    const cols = buildColumnIndex(headers);

    if (cols.status === null) {
        warn(
            "fetchRefundRequests",
            "Status column not found — every row will be treated as unprocessed (graceful degradation)",
        );
    }

    const entries: RefundSheetEntry[] = dataRows.map((row, idx) =>
        parseRow(row, /* rowNumber: 1-based, header at row 1 */ idx + 2, cols)
    );

    const unprocessed = entries.filter((e) => !e.isProcessed);
    log("fetchRefundRequests", {
        spreadsheetId,
        tabId,
        totalRows: entries.length,
        unprocessed: unprocessed.length,
    });

    return { url, spreadsheetId, tabId, unprocessed };
}

/** Same as `fetchRefundRequests` but swallows errors and returns an empty
 *  snapshot. Useful for handlers that prefer to render "no rows" over
 *  failing the whole workflow on a transient Sheets outage. */
export async function fetchRefundRequestsOrEmpty(
    env: Record<string, string>,
): Promise<RefundSheetData> {
    try {
        return await fetchRefundRequests(env);
    } catch (err) {
        warn(
            "fetchRefundRequestsOrEmpty",
            "falling back to empty snapshot:",
            String(err),
        );
        return { url: "", spreadsheetId: "", tabId: "", unprocessed: [] };
    }
}
