#!/usr/bin/env -S uv run --quiet
# /// script
# dependencies = [
#     "google-auth>=2.0.0",
#     "google-api-python-client>=2.0.0",
#     "python-dotenv>=1.0.0",
# ]
# ///
"""
Load refund request Google Sheet → DynamoDB `refunds` table.

Each row becomes one item keyed by a deterministic ID derived from
email + order_number so re-runs are idempotent (put-item overwrites).

Fields NOT in the sheet (customer_id, order_id, amount) are omitted;
those items will not appear in the customer-index GSI until backfilled
via a Shopify lookup pass.

Usage:
    ./scripts/load_refunds_to_dynamo.py            # dry run
    ./scripts/load_refunds_to_dynamo.py --execute  # write to DynamoDB
"""

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv(pathlib.Path(__file__).parent.parent / ".env")

# ── Config ───────────────────────────────────────────────────────────────────

SHEET_ID = "11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw"
TAB      = "Refund_Requests"
TABLE    = "refunds"
REGION   = "us-east-1"

TIMESTAMP_FORMATS = (
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %I:%M:%S %p",
    "%-m/%-d/%Y %H:%M:%S",
)

# ── Auth ─────────────────────────────────────────────────────────────────────

def build_sheets_service(creds_json: str):
    creds = Credentials.from_service_account_info(
        json.loads(creds_json),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    return build("sheets", "v4", credentials=creds)


# ── Sheet helpers ─────────────────────────────────────────────────────────────

def fetch_rows(service) -> tuple[list[str], list[list[str]]]:
    res = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SHEET_ID, range=f"'{TAB}'!A:ZZ")
        .execute()
    )
    rows = res.get("values", [])
    if not rows:
        return [], []
    return [c.strip() for c in rows[0]], rows[1:]


def cell(row: list[str], idx: int) -> str:
    return row[idx].strip() if 0 <= idx < len(row) else ""


# ── Parsing ───────────────────────────────────────────────────────────────────

def attempt_strptime(raw: str, fmt: str) -> datetime | None:
    try:
        return datetime.strptime(raw, fmt)
    except ValueError:
        return None


def parse_timestamp(raw: str) -> str:
    raw = raw.strip()
    dt = next((d for fmt in TIMESTAMP_FORMATS if (d := attempt_strptime(raw, fmt))), None)
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt else raw


def normalize_order_number(raw: str) -> str:
    """Strip non-digits, prepend #. Returns '' if no digits found."""
    digits = re.sub(r"[^0-9]", "", raw.strip())
    return f"#{digits}" if digits else ""


def parse_refund_to(raw: str) -> str:
    """'Cancel for refund' → 'original_method'; credit/store answers → 'store_credit'."""
    return "original_method" if "refund" in raw.lower() else "store_credit"


def parse_status(processed_raw: str) -> str:
    return "completed" if processed_raw.strip().upper() == "TRUE" else "pending"


def make_id(email: str, order_number: str) -> str:
    """Deterministic ID so re-runs are idempotent."""
    digest = hashlib.sha256(f"{email.lower()}|{order_number}".encode()).hexdigest()[:16]
    return f"rf-{digest}"


# ── Column index discovery ────────────────────────────────────────────────────

def find(header: list[str], *candidates: str) -> int:
    lowered = [c.lower() for c in header]
    return next((lowered.index(c.lower()) for c in candidates if c.lower() in lowered), -1)


def find_containing(header: list[str], *fragments: str) -> int:
    lowered = [c.lower() for c in header]
    return next((i for frag in fragments for i, h in enumerate(lowered) if frag.lower() in h), -1)


# ── Row → DynamoDB item ───────────────────────────────────────────────────────

def is_blank(row: list[str], col_email: int, col_ts: int) -> bool:
    return not cell(row, col_email) and not cell(row, col_ts)


def row_to_item(row: list[str], col: dict[str, int], created_at: str) -> dict | None:
    email = cell(row, col["email"]).lower()
    raw_order = cell(row, col["order_number"])
    order_number = normalize_order_number(raw_order)

    if not email or not order_number:
        return None

    refund_to_raw = cell(row, col["refund_to"])
    item: dict[str, dict] = {
        "id":           {"S": make_id(email, order_number)},
        "email":        {"S": email},
        "first_name":   {"S": cell(row, col["first_name"])},
        "last_name":    {"S": cell(row, col["last_name"])},
        "order_number": {"S": order_number},
        "refund_to":    {"S": parse_refund_to(refund_to_raw)},
        "status":       {"S": parse_status(cell(row, col["processed"]))},
        "submitted_at": {"S": parse_timestamp(cell(row, col["timestamp"]))},
        "created_at":   {"S": created_at},
    }

    optional: dict[str, str] = {
        "note":             cell(row, col["note"]),
        "admin_notes":      cell(row, col["admin_notes"]),
        "transfer_request": cell(row, col["transfer_request"]),
    }
    item |= {k: {"S": v} for k, v in optional.items() if v}

    return item


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    execute = "--execute" in sys.argv

    if not execute:
        print("DRY RUN — pass --execute to write to DynamoDB\n")

    creds_json = os.environ.get("GOOGLE__SERVICE_ACCOUNT")
    if not creds_json:
        print("GOOGLE__SERVICE_ACCOUNT not set", file=sys.stderr)
        sys.exit(1)

    service = build_sheets_service(creds_json)
    header, data_rows = fetch_rows(service)
    print(f"Sheet '{TAB}': {len(data_rows)} data rows")

    col = {
        "timestamp":        find(header, "Timestamp"),
        "email":            find_containing(header, "email address"),
        "order_number":     find_containing(header, "order number"),
        "refund_to":        find_containing(header, "refund to your original", "store credit"),
        "note":             find_containing(header, "anything else to note"),
        "first_name":       find(header, "First Name"),
        "last_name":        find(header, "Last Name"),
        "transfer_request": find_containing(header, "transfer to another day"),
        "processed":        find_containing(header, "processed"),
        "admin_notes":      find(header, "Notes"),
    }

    required = ("timestamp", "email", "order_number", "refund_to", "first_name", "last_name")
    missing = [k for k in required if col[k] == -1]
    if missing:
        print(f"Could not find required columns: {missing}", file=sys.stderr)
        print(f"Header: {header}", file=sys.stderr)
        sys.exit(1)

    created_at = datetime.now(timezone.utc).isoformat()
    seen: dict[str, dict] = {}
    skipped_blank = skipped_bad = 0

    for row in data_rows:
        if is_blank(row, col["email"], col["timestamp"]):
            skipped_blank += 1
            continue
        item = row_to_item(row, col, created_at)
        if item is None:
            email = cell(row, col["email"]).lower()
            raw_order = cell(row, col["order_number"])
            print(f"  skip: {email!r} / order={raw_order!r} — no valid order number")
            skipped_bad += 1
            continue
        item_id = item["id"]["S"]
        if item_id in seen:
            print(f"  dedup: {item['email']['S']} / {item['order_number']['S']} — keeping latest row")
        seen[item_id] = item

    items = list(seen.values())
    print(f"Parsed: {len(items)} items  blank rows skipped: {skipped_blank}  bad order: {skipped_bad}\n")

    statuses = Counter(item["status"]["S"] for item in items)
    refund_tos = Counter(item["refund_to"]["S"] for item in items)
    print("By status:   ", dict(statuses))
    print("By refund_to:", dict(refund_tos))

    if items:
        print(f"\nSample item (first):")
        for k, v in items[0].items():
            print(f"  {k}: {list(v.values())[0]}")

    batch_size = 25
    batches: list[dict] = [
        {TABLE: [{"PutRequest": {"Item": item}} for item in items[s : s + batch_size]]}
        for s in range(0, len(items), batch_size)
    ]
    for i, batch in enumerate(batches):
        pathlib.Path(f"/tmp/rf-batch-{i}.json").write_text(json.dumps(batch))
    print(f"\nBatch files: /tmp/rf-batch-{{0..{len(batches)-1}}}.json  ({len(batches)} batches of ≤{batch_size})")

    if not execute:
        print(f"\nDry run complete — would write {len(items)} items to `{TABLE}`.")
        print(f"To load, run:\n  ./scripts/load_refunds_to_dynamo.py --execute")
        return

    print("Writing via AWS CLI…")
    written = errors = 0
    for i, batch in enumerate(batches):
        result = subprocess.run(
            ["aws", "dynamodb", "batch-write-item", "--request-items", f"file:///tmp/rf-batch-{i}.json"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  ERROR batch {i}: {result.stderr.strip()}")
            errors += len(batch[TABLE])
            continue
        resp = json.loads(result.stdout or "{}")
        n_unprocessed = len(resp.get("UnprocessedItems", {}).get(TABLE, []))
        written += len(batch[TABLE]) - n_unprocessed
        errors += n_unprocessed
        print(f"  WARNING: {n_unprocessed} unprocessed in batch {i}") if n_unprocessed else None

    print(f"\n✅ Written: {written}  Errors: {errors}")


if __name__ == "__main__":
    main()
