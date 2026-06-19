# google-sheets-api

**Kind:** REST API (Google Sheets API v4)
**Version / API version:** v4
**Last touched:** 2026-06-15
**Official docs:** <https://developers.google.com/workspace/sheets/api>
**Source root:** n/a (hosted API). Our client: `slack-apps/registrations/lib/clients/google/client.ts`

## What it is (one sentence)

RESTful API to read/write Google Spreadsheet cell values and structure (formatting, rows/columns, formatting, filters).

## Confirmed facts

### Two different "batchUpdate" endpoints — do not confuse them

- (docs: <https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/batchUpdate>, search: "Sets values in one or more ranges of a spreadsheet", fetched 2026-06-15) — **`spreadsheets.values.batchUpdate`** (the "values" endpoint) sets cell **values** in one or more ranges. `POST /v4/spreadsheets/{spreadsheetId}/values:batchUpdate`, body `{ valueInputOption, data: [ { range, values } ] }`. Ranges are **A1 strings keyed by sheet NAME**. This is what we use for the waitlist Status write.
- (docs: <https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/batchUpdate>, search: "Applies one or more updates to the spreadsheet", fetched 2026-06-15) — **`spreadsheets.batchUpdate`** (the "structural" endpoint) applies `Request` objects for everything beyond plain values: formatting, insert/delete rows & columns, conditional formatting, data validation, freezing, merges, protected ranges, sort/filter, add/rename/delete sheets. It addresses cells via **`GridRange`/`GridCoordinate`, keyed by integer `sheetId` + 0-based indices** — never by name. (We do not use this yet.)

### Addressing: A1 (values) vs GridRange (structural)

- (docs: <https://developers.google.com/workspace/sheets/api/guides/concepts>, search: "Single quotes are required for sheet names with spaces", fetched 2026-06-15) — A1 notation = sheet name + column **letters** + **1-based** row numbers (e.g. `Sheet1!A1:B2`). Single quotes required for sheet names with spaces/special chars (e.g. `'Form Responses 1'!F10`).
- (docs: <https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/other#GridRange>, search: "All indexes are zero-based. Indexes are half open", fetched 2026-06-15) — `GridRange` uses `sheetId` + `startRowIndex/endRowIndex/startColumnIndex/endColumnIndex`, all **zero-based** and **half-open** `[start, end)`. Example: `Sheet1!A1:A1 == sheetId, startRowIndex 0, endRowIndex 1, startColumnIndex 0, endColumnIndex 1`.
- (docs: <https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/other#GridCoordinate>, search: "A coordinate in a sheet. All indexes are zero-based", fetched 2026-06-15) — `GridCoordinate` = `{ sheetId, rowIndex, columnIndex }`, all zero-based.

### Why the sheetId (gid) is worth retaining

- (docs: concepts, search: "Sheet IDs are stable, even if the sheet name changes", fetched 2026-06-15) — `sheetId` (the `gid` in the URL) is **stable across tab renames**; the sheet **name** is not. Name-based addressing (values API) silently breaks on rename; the sheetId does not.
- The structural API above requires `sheetId`, so any future formatting/structure work needs it.
- (docs: concepts, search: "it can be derived from the spreadsheet's URL", fetched 2026-06-15) — both spreadsheetId and sheetId derive from the URL `…/d/SPREADSHEET_ID/edit?gid=SHEET_ID#gid=SHEET_ID`; the gid is required to deep-link a specific tab.

### Why 0-based indices (not a column letter) are the canonical internal form

- The values API needs A1 **letters**; the structural API needs **0-based indices** (GridRange/GridCoordinate above). The 0-based index converts trivially to a letter but a letter must be parsed back to an index for GridRange — so the **index is the more fundamental, API-spanning representation**. Carry the index; adapt to a letter only at the values-API boundary.
- (verified by working call site `slack-apps/registrations/lib/clients/google/client.ts:columnToLetter`, 2026-06-15) — our single A1 adapter; `findColumn` already yields a 0-based index, so no reverse parsing is needed.

### Response shape useful for verification

- (docs: values/batchUpdate, search: "One UpdateValuesResponse per requested range, in the same order", fetched 2026-06-15) — response has `totalUpdatedCells` and one `responses[]` entry per requested range, in request order. `totalUpdatedCells === 0` flags a write that matched nothing (does NOT catch a write to the wrong-but-valid cell).
- (docs: values/batchUpdate, search: "Requires one of the following OAuth scopes", fetched 2026-06-15) — write scopes: `…/auth/spreadsheets` (what we use), `…/auth/drive`, or `…/auth/drive.file`.

## Quirks / gotchas

- (verified by working call site `slack-apps/registrations/functions/update_waitlist_spreadsheet.ts`, 2026-06-15) — **Locate the target column by header name, never hard-code a letter.** We had Status hard-coded to column `J` while the header put Status at `F`; the write returned HTTP 200 into the empty column J, so it looked successful but updated nothing visible. Resolve the column from the header row (`resolveStatusColumnIndex`) before writing.
- (verified by working call site `slack-apps/registrations/lib/clients/google/client.ts:getSpreadsheet` + `lib/waitlists/handlers/sheet_parser.ts:parseWaitlistRows`, 2026-06-15) — `getSpreadsheet` filters out rows with an empty first cell, but the parser derives `rowNumber` from the **post-filter** array index (`i + 1`). That mapping is only correct when no rows are dropped; an interior blank row would shift every subsequent rowNumber and misdirect writes. (Form-responses sheets are contiguous today, so it holds — but it's fragile. See open question.)

## Common usage in this repo

- `slack-apps/registrations/lib/clients/google/client.ts:updateCells` — single `values:batchUpdate` POST for N cells (`{ row, col, value }[]`, RAW input).
- `slack-apps/registrations/lib/clients/google/client.ts:getSpreadsheet` — `values.get` of `A1:J` for the waitlist tab.
- `slack-apps/registrations/lib/waitlists/sheet_service.ts` — `fetchWaitlists` + `resolveStatusColumnIndex` (column-by-name).

## Open questions / unverified

- [ ] Exact `values.get` return shape for **interior** fully-blank rows: returned as `[]` (index preserved) or omitted (index shifts)? Trailing empties are known to be trimmed. Verify before relying on positional row numbers across blank rows. (Suggested: empirical probe against a sheet with a mid-data blank row.)

## Cross-references

- Gmail API (same `GoogleClient` JWT/service-account auth): `slack-apps/registrations/lib/clients/google/gmail.ts`.
- Auth: domain-wide-delegation service account, scope `…/auth/spreadsheets`.
