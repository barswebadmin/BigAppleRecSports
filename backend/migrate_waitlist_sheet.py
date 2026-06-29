#!/usr/bin/env -S uv run --quiet
# /// script
# dependencies = [
#     "google-auth>=2.0.0",
#     "google-api-python-client>=2.0.0",
#     "python-dotenv>=1.0.0",
# ]
# ///
"""
Migrate + clean up waitlist form responses across two Google Sheets.

Steps (all run when --execute is passed):
  1. Append rows 737+ from old sheet that aren't already in new sheet
     (dedup on email + league)
  2. Swap columns B ↔ E for rows 2-5 and 10-25 in the new sheet
     (those rows were imported with the columns switched)
  3. Sort rows 2-25 chronologically ascending by Timestamp (col A)

Dry run (default — no flags):
  Shows what would be appended and what rows would be swapped/sorted
  without writing anything.

Usage:
    ./scripts/migrate_waitlist_sheet.py            # dry run
    ./scripts/migrate_waitlist_sheet.py --execute  # run all steps
    ./scripts/migrate_waitlist_sheet.py --fix-only # skip append, just swap + sort
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ── Config ──────────────────────────────────────────────────────────────────

OLD_SHEET_ID = "1KcHgBHyeLmL3MQjbkB5CJUNFXbYMrtqZFqOsVnL0id0"
OLD_TAB = "Form Responses"
OLD_START_ROW = 737  # first row to migrate (1-indexed, inclusive; row 1 = header)

NEW_SHEET_ID = "1QgyHDN9EcxqefEJCDozfLZ7QKVxSbOaW28WOET9PYEE"
NEW_TAB = "Form Responses 1"

# Spreadsheet rows (1-indexed) where B and E are swapped and need to be fixed.
# "2-5 and 10 and down" → rows 2,3,4,5 plus 10-25
SWAP_ROWS = set(range(2, 6)) | set(range(10, 26))

# Spreadsheet rows to sort chronologically (1-indexed; SORT_END_ROW=None → sort all data rows)
SORT_START_ROW = 2
SORT_END_ROW: int | None = None  # None = sort everything from row 2 to end of sheet

# Column renames: old sheet name → new sheet name (where they differ)
COLUMN_RENAMES: dict[str, str] = {
    "Please confirm the league you're joining the waitlist for:": (
        "Please select the league you want to sign up for"
        " (leagues will be added as they sell out):"
    ),
}

DEDUP_EMAIL_VARIANTS = {"email address", "email"}
DEDUP_LEAGUE_VARIANTS = {
    "please confirm the league you're joining the waitlist for:",
    "please select the league you want to sign up for (leagues will be added as they sell out):",
}

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ── Auth ─────────────────────────────────────────────────────────────────────

def build_sheets_service():
    load_dotenv(Path(__file__).parent.parent / ".env")
    raw = os.environ.get("GOOGLE__SERVICE_ACCOUNT")
    if not raw:
        print("❌ GOOGLE__SERVICE_ACCOUNT not found in environment / .env", file=sys.stderr)
        sys.exit(1)
    creds = Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)

# ── Sheet helpers ─────────────────────────────────────────────────────────────

def fetch_all_rows(service, sheet_id: str, tab: str) -> list[list[str]]:
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=f"'{tab}'!A:ZZ")
        .execute()
    )
    return result.get("values", [])


def append_rows(service, sheet_id: str, tab: str, rows: list[list[str]]) -> int:
    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=sheet_id,
            range=f"'{tab}'!A:A",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        )
        .execute()
    )
    return result.get("updates", {}).get("updatedRows", 0)


def batch_update_rows(service, sheet_id: str, tab: str,
                      updates: list[tuple[str, list[list[str]]]]) -> None:
    """updates: list of (A1_range, values) tuples."""
    data = [{"range": f"'{tab}'!{r}", "values": v} for r, v in updates]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={"valueInputOption": "USER_ENTERED", "data": data},
    ).execute()


# ── Column helpers ────────────────────────────────────────────────────────────

def find_col(header: list[str], variants: set[str]) -> int | None:
    for i, cell in enumerate(header):
        if cell.strip().lower() in variants:
            return i
    return None


def col_letter(index: int) -> str:
    """Convert 0-based column index to spreadsheet letter (A, B, … Z, AA…)."""
    result = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        result = chr(65 + rem) + result
    return result


# ── Timestamp parser ──────────────────────────────────────────────────────────

def parse_ts(ts: str) -> datetime:
    """Parse 'M/D/YYYY H:MM:SS' or 'M/D/YYYY HH:MM:SS AM/PM' timestamps."""
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p", "%-m/%-d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(ts.strip(), fmt)
        except ValueError:
            continue
    # Fallback: sort unparseable timestamps to the end
    return datetime.max


# ── Step 1: Migrate ───────────────────────────────────────────────────────────

def step_migrate(service, execute: bool) -> None:
    print("\n━━━ Step 1: Migrate rows from old sheet ━━━")

    old_rows = fetch_all_rows(service, OLD_SHEET_ID, OLD_TAB)
    if not old_rows:
        print("❌ Old sheet returned no data"); return

    old_header = old_rows[0]
    old_data = old_rows[OLD_START_ROW - 1:]
    print(f"  Old sheet: {len(old_rows) - 1} total rows; {len(old_data)} rows from row {OLD_START_ROW}+")

    old_email_col = find_col(old_header, DEDUP_EMAIL_VARIANTS)
    old_league_col = find_col(old_header, DEDUP_LEAGUE_VARIANTS)
    if old_email_col is None or old_league_col is None:
        print(f"❌ Could not locate email/league in old header: {old_header}"); return

    new_rows = fetch_all_rows(service, NEW_SHEET_ID, NEW_TAB)
    if not new_rows:
        print("❌ New sheet returned no data"); return

    new_header = new_rows[0]
    new_data = new_rows[1:]
    print(f"  New sheet: {len(new_data)} existing rows")

    new_email_col = find_col(new_header, DEDUP_EMAIL_VARIANTS)
    new_league_col = find_col(new_header, DEDUP_LEAGUE_VARIANTS)
    if new_email_col is None or new_league_col is None:
        print(f"❌ Could not locate email/league in new header: {new_header}"); return

    # Build dedup set
    existing: set[tuple[str, str]] = set()
    for row in new_data:
        e = (row[new_email_col] if new_email_col < len(row) else "").strip().lower()
        lg = (row[new_league_col] if new_league_col < len(row) else "").strip().lower()
        if e:
            existing.add((e, lg))

    # Column mapping: new header index → old header index
    new_to_old_name = {v: k for k, v in COLUMN_RENAMES.items()}
    col_map: list[int | None] = []
    for name in new_header:
        old_name = new_to_old_name.get(name, name)
        try:
            col_map.append(old_header.index(old_name))
        except ValueError:
            col_map.append(None)

    unmapped = [new_header[i] for i, idx in enumerate(col_map) if idx is None]
    if unmapped:
        print(f"  ⚠️  New columns with no old-sheet match (will be blank): {unmapped}")

    # Find rows to add
    to_add: list[list[str]] = []
    skipped_dup = skipped_empty = 0
    for row in old_data:
        e = (row[old_email_col] if old_email_col < len(row) else "").strip()
        lg = (row[old_league_col] if old_league_col < len(row) else "").strip()
        if not e:
            skipped_empty += 1; continue
        key = (e.lower(), lg.lower())
        if key in existing:
            skipped_dup += 1; continue
        new_row = []
        for n in range(len(new_header)):
            i = col_map[n]
            new_row.append(row[i] if i is not None and i < len(row) else "")
        to_add.append(new_row)
        existing.add(key)

    print(f"  Evaluated {len(old_data)}: {skipped_dup} duplicates, "
          f"{skipped_empty} no-email, {len(to_add)} to add")

    if not to_add:
        print("  ✅ Nothing to migrate — all rows already present."); return

    print(f"  First 3 rows to add:")
    for row in to_add[:3]:
        e = row[new_email_col] if new_email_col < len(row) else "?"
        lg = row[new_league_col] if new_league_col < len(row) else "?"
        print(f"    [{e}] | [{lg[:55]}]")
    if len(to_add) > 3:
        print(f"    … and {len(to_add) - 3} more")

    if execute:
        added = append_rows(service, NEW_SHEET_ID, NEW_TAB, to_add)
        print(f"  ✅ Appended {added} rows.")
    else:
        print(f"  💡 Dry run — would append {len(to_add)} rows.")


# ── Step 2: Swap columns B ↔ E ───────────────────────────────────────────────

def step_swap(service, execute: bool) -> None:
    print("\n━━━ Step 2: Swap columns B ↔ E for affected rows ━━━")

    all_rows = fetch_all_rows(service, NEW_SHEET_ID, NEW_TAB)
    if not all_rows:
        print("❌ New sheet returned no data"); return

    # all_rows[0] = header (row 1), all_rows[1] = row 2, etc.
    updates: list[tuple[str, list[list[str]]]] = []
    swapped_count = 0

    for sheet_row in SWAP_ROWS:
        idx = sheet_row - 1  # 0-based index into all_rows
        if idx >= len(all_rows):
            continue
        row = list(all_rows[idx])
        # Pad row if shorter than column E (index 4)
        while len(row) < 5:
            row.append("")
        b_val, e_val = row[1], row[4]
        if b_val == e_val:
            continue  # already identical, skip
        row[1], row[4] = e_val, b_val
        updates.append((f"B{sheet_row}:E{sheet_row}", [row[1:5]]))
        swapped_count += 1
        if swapped_count <= 3:
            print(f"  Row {sheet_row}: B='{b_val[:30]}' ↔ E='{e_val[:30]}'")

    if swapped_count > 3:
        print(f"  … and {swapped_count - 3} more rows")

    if not updates:
        print("  ✅ No rows need swapping."); return

    print(f"  {swapped_count} rows to swap (B ↔ E)")
    if execute:
        batch_update_rows(service, NEW_SHEET_ID, NEW_TAB, updates)
        print("  ✅ Swap complete.")
    else:
        print("  💡 Dry run — would swap the rows above.")


# ── Step 3: Sort rows 2-25 by Timestamp ──────────────────────────────────────

def step_sort(service, execute: bool) -> None:
    all_rows = fetch_all_rows(service, NEW_SHEET_ID, NEW_TAB)
    if not all_rows:
        print("❌ New sheet returned no data"); return

    start_idx = SORT_START_ROW - 1  # 0-based
    end_idx = (len(all_rows) - 1) if SORT_END_ROW is None else min(SORT_END_ROW - 1, len(all_rows) - 1)
    actual_end_row = end_idx + 1  # back to 1-indexed for display

    print(f"\n━━━ Step 3: Sort rows {SORT_START_ROW}–{actual_end_row} by Timestamp (asc) ━━━")

    rows_to_sort = [list(r) for r in all_rows[start_idx:end_idx + 1]]
    if not rows_to_sort:
        print("  ✅ No rows in sort range."); return

    sorted_rows = sorted(rows_to_sort, key=lambda r: parse_ts(r[0]) if r else datetime.max)

    print(f"  Sorting {len(sorted_rows)} rows")
    print("  First 3 timestamps after sort:")
    for r in sorted_rows[:3]:
        print(f"    {r[0] if r else '?'}")
    print(f"  Last timestamp: {sorted_rows[-1][0] if sorted_rows[-1] else '?'}")

    if execute:
        max_cols = max(len(r) for r in sorted_rows)
        padded = [r + [""] * (max_cols - len(r)) for r in sorted_rows]
        end_col = col_letter(max_cols - 1)
        range_str = f"A{SORT_START_ROW}:{end_col}{actual_end_row}"
        batch_update_rows(service, NEW_SHEET_ID, NEW_TAB, [(range_str, padded)])
        print("  ✅ Sort complete.")
    else:
        print("  💡 Dry run — would sort and write back.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    execute = "--execute" in sys.argv
    fix_only = "--fix-only" in sys.argv

    if not execute and not fix_only:
        print("🔍 DRY RUN — pass --execute to write changes, --fix-only to skip migrate\n")
    elif fix_only:
        print("🔧 FIX-ONLY mode — skipping migration, running swap + sort\n")
    else:
        print("🚀 EXECUTE mode — running all steps\n")

    service = build_sheets_service()

    if not fix_only:
        step_migrate(service, execute)

    step_swap(service, execute)
    step_sort(service, execute)

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
