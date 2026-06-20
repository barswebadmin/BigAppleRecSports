#!/usr/bin/env -S uv run --quiet
# /// script
# dependencies = [
#     "google-auth>=2.0.0",
#     "google-api-python-client>=2.0.0",
#     "python-dotenv>=1.0.0",
# ]
# ///
"""
Load waitlist Google Sheet → DynamoDB `waitlists` table.

Each row becomes one item keyed by a deterministic ID derived from
email + league so re-runs are idempotent (put-item overwrites).

Usage:
    ./scripts/load_waitlist_to_dynamo.py            # dry run — prints what would be written
    ./scripts/load_waitlist_to_dynamo.py --execute  # write to DynamoDB
"""

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv(pathlib.Path(__file__).parent.parent / ".env")

# ── Config ───────────────────────────────────────────────────────────────────

SHEET_ID = "1QgyHDN9EcxqefEJCDozfLZ7QKVxSbOaW28WOET9PYEE"
TAB      = "Form Responses 1"
TABLE    = "waitlists"
REGION   = "us-east-1"

TIMESTAMP_FORMATS = (
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %I:%M:%S %p",
    "%-m/%-d/%Y %H:%M:%S",
)

STATUS_MAP = {
    "joined":  "joined",
    "removed": "removed",
    "denied":  "denied",
    "":        "active",
}

OPTIONAL_FIELDS: dict[str, str] = {
    "phone":    "phone_number",
    "gender":   "gender",
    "pronouns": "pronouns",
}

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


def parse_league(raw: str) -> tuple[str, str, str]:
    """'Kickball - Sunday - Open Division' → (sport, day, division)."""
    parts = [p.strip() for p in raw.split(" - ")]
    sport    = parts[0].lower() if len(parts) > 0 else ""
    day      = parts[1].lower() if len(parts) > 1 else ""
    division = parts[2].lower() if len(parts) > 2 else ""
    return sport, day, division


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def make_league_key(sport: str, day: str, division: str) -> str:
    return slugify(f"{sport}-{day}-{division}")


def make_id(email: str, league_key: str) -> str:
    """Deterministic ID so re-runs are idempotent."""
    digest = hashlib.sha256(f"{email.lower()}|{league_key}".encode()).hexdigest()[:16]
    return f"wl-{digest}"


def parse_status(raw: str) -> str:
    return STATUS_MAP.get(raw.strip().lower(), raw.strip().lower() or "active")


# ── Column index discovery ────────────────────────────────────────────────────

def find(header: list[str], *candidates: str) -> int:
    lowered = [c.lower() for c in header]
    return next((lowered.index(c.lower()) for c in candidates if c.lower() in lowered), -1)


# ── Row → DynamoDB item ───────────────────────────────────────────────────────

def row_to_item(row: list[str], position: int, col: dict[str, int]) -> dict | None:
    email = cell(row, col["email"]).lower()
    if not email:
        return None

    league_raw = cell(row, col["league"])
    sport, day, division = parse_league(league_raw)
    if not sport:
        return None

    league_key = make_league_key(sport, day, division)
    item: dict[str, dict] = {
        "id":          {"S": make_id(email, league_key)},
        "email":       {"S": email},
        "first_name":  {"S": cell(row, col["first_name"])},
        "last_name":   {"S": cell(row, col["last_name"])},
        "sport":       {"S": sport},
        "day":         {"S": day},
        "division":    {"S": division},
        "league_key":  {"S": league_key},
        "status":      {"S": parse_status(cell(row, col["status"]))},
        "created_at":  {"S": parse_timestamp(cell(row, col["timestamp"]))},
        "position":    {"N": str(position)},
    }
    item |= {
        dynamo_key: {"S": val}
        for col_name, dynamo_key in OPTIONAL_FIELDS.items()
        if (val := cell(row, col[col_name]))
    }
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
    print(f"Sheet: {len(data_rows)} data rows")

    col = {
        "timestamp":  find(header, "Timestamp"),
        "email":      find(header, "Email Address", "Email"),
        "first_name": find(header, "First Name"),
        "last_name":  find(header, "Last Name"),
        "league":     find(header, "Please select the league you want to sign up for (leagues will be added as they sell out):"),
        "status":     find(header, "Status"),
        "phone":      find(header, "Phone Number"),
        "gender":     find(header, "Gender"),
        "pronouns":   find(header, "Pronouns"),
    }

    required = ("timestamp", "email", "first_name", "last_name", "league")
    missing = [k for k in required if col[k] == -1]
    if missing:
        print(f"Could not find required columns: {missing}", file=sys.stderr)
        print(f"Header was: {header}", file=sys.stderr)
        sys.exit(1)

    seen: dict[str, dict] = {}
    skipped = 0
    position_by_league: defaultdict[str, int] = defaultdict(int)

    for row in data_rows:
        league_raw = cell(row, col["league"])
        sport, day, division = parse_league(league_raw)
        league_key = make_league_key(sport, day, division)
        position_by_league[league_key] += 1

        item = row_to_item(row, position_by_league[league_key], col)
        if item is None:
            skipped += 1
            continue
        item_id = item["id"]["S"]
        if item_id in seen:
            print(f"  dedup: {item['email']['S']} / {league_key} — keeping latest row")
        seen[item_id] = item

    items = list(seen.values())
    print(f"Parsed: {len(items)} items, {skipped} skipped (no email/league)\n")

    leagues = Counter(item["league_key"]["S"] for item in items)
    print("By league:")
    for league, count in sorted(leagues.items()):
        print(f"  {league:<45} {count} entries")

    if items:
        print(f"\nSample item (first):")
        sample = {k: list(v.values())[0] for k, v in items[0].items()}
        for k, v in sample.items():
            print(f"  {k}: {v}")

    batch_size = 25
    batches: list[dict] = [
        {TABLE: [{"PutRequest": {"Item": item}} for item in items[s : s + batch_size]]}
        for s in range(0, len(items), batch_size)
    ]
    for i, batch in enumerate(batches):
        pathlib.Path(f"/tmp/wl-batch-{i}.json").write_text(json.dumps(batch))
    print(f"\nBatch files written: /tmp/wl-batch-{{0..{len(batches)-1}}}.json  ({len(batches)} batches of ≤{batch_size})")

    if not execute:
        print(f"\nDry run complete — would write {len(items)} items to `{TABLE}`.")
        print(f"To load, run:\n  ./scripts/load_waitlist_to_dynamo.py --execute")
        return

    print("Writing via AWS CLI (credentials passed by shell hook)…")
    written = errors = 0
    for i, batch in enumerate(batches):
        result = subprocess.run(
            ["aws", "dynamodb", "batch-write-item", "--request-items", f"file:///tmp/wl-batch-{i}.json"],
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
