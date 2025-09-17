from __future__ import annotations

import argparse
import csv
import json
import os
import re
from typing import Dict, List, Optional, Tuple

from config import config
from services.slack.usergroup_client import SlackUsergroupClient


def normalize_handle(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    t = re.sub(r"-+", "-", t).strip("-")
    return t


def parse_member_tokens(raw: str) -> List[str]:
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts


def extract_slack_id(token: str) -> Optional[str]:
    # Accept formats: UXXXX, <@UXXXX>, @handle (won't resolve without mapping), raw name (needs mapping)
    m = re.match(r"^<@([A-Z0-9]+)>$", token)
    if m:
        return f"<@{m.group(1)}>"
    if re.match(r"^[A-Z0-9]{9,}$", token):
        return f"<@{token}>"
    return None


def build_group_plans(
    rows: List[Dict[str, str]],
    name_to_id: Dict[str, str],
    group_overrides: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    plans: Dict[str, List[str]] = {}

    def add_members(handle: str, tokens: List[str]) -> None:
        members = plans.setdefault(handle, [])
        for tok in tokens:
            sid = extract_slack_id(tok)
            if not sid:
                # try name/label mapping; also try trimming anything in parentheses
                key = tok
                plain = tok.split(" (")[0].strip()
                sid = name_to_id.get(key) or name_to_id.get(plain)
            if sid:
                members.append(sid)

    for row in rows:
        sport = (row.get("sport") or row.get("Sport") or "").strip()
        night = (row.get("night") or row.get("Night") or "").strip()
        division = (row.get("division") or row.get("Division") or "").strip()
        directors_raw = row.get("Directors") or row.get("directors") or ""
        ops_raw = row.get("Ops") or row.get("ops") or row.get("Operations") or ""

        if not sport:
            continue

        # base handles
        if night:
            base_handle = normalize_handle(f"{sport}-{night}")
        else:
            base_handle = normalize_handle(sport)

        full_handle = base_handle
        if division:
            full_handle = normalize_handle(f"{sport}-{night}-{division}") if night else normalize_handle(f"{sport}-{division}")

        # collect members for full group
        add_members(full_handle, parse_member_tokens(directors_raw))
        add_members(full_handle, parse_member_tokens(ops_raw))

        # also aggregate into sport-night if both present
        if night:
            add_members(base_handle, parse_member_tokens(directors_raw))
            add_members(base_handle, parse_member_tokens(ops_raw))

    # apply overrides
    for handle, extra in group_overrides.items():
        existing = plans.setdefault(handle, [])
        existing.extend(extra)

    # uniq + sort
    for handle, members in list(plans.items()):
        uniq = sorted(list({m for m in members if m}))
        plans[handle] = uniq

    return plans


def read_csv_rows(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def load_json(path: Optional[str]) -> Dict:
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="CSV-driven Slack usergroup sync (Directors/Ops)")
    parser.add_argument("--csv", required=True, help="Path to CSV with columns: Sport,Night,Division,Directors,Ops")
    parser.add_argument("--name-to-id", help="Optional JSON mapping of names/labels to Slack IDs (<@U...>)")
    parser.add_argument("--group-overrides", help="Optional JSON mapping of group handle -> extra Slack IDs list")
    parser.add_argument("--apply", action="store_true", help="Apply changes to Slack (omit for dry run)")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"❌ CSV not found: {args.csv}")
        return 1

    rows = read_csv_rows(args.csv)
    name_to_id = load_json(args.name_to_id)
    group_overrides = load_json(args.group_overrides)

    plans = build_group_plans(rows, name_to_id, group_overrides)

    print(f"🧭 Planned groups: {len(plans)}")
    for handle, members in list(plans.items())[:15]:
        print(f"- {handle}: {len(members)} member(s)")

    token = config.active_slack_bot_token
    if not args.apply:
        print("✅ Dry run complete. Re-run with --apply to update Slack usergroups.")
        return 0

    if not token:
        print("❌ No Slack bot token configured. Set SLACK_DEV_BOT_TOKEN or SLACK_REFUNDS_BOT_TOKEN.")
        return 1

    client = SlackUsergroupClient(token)
    existing: Dict[str, str] = {}
    try:
        for ug in client.list_usergroups():
            h, gid = ug.get("handle"), ug.get("id")
            if h and gid:
                existing[h] = gid
    except Exception as e:
        print(f"⚠️ Could not list usergroups: {e}")

    created = 0
    updated = 0
    for handle, members in plans.items():
        gid = existing.get(handle)
        if not gid:
            gid = client.create_usergroup(name=handle.replace("-", " ").title(), handle=handle, description="Auto-managed from CSV")
            if gid:
                existing[handle] = gid
                if members and client.update_usergroup_users(gid, members):
                    created += 1
        else:
            if members and client.update_usergroup_users(gid, members):
                updated += 1

    print(f"✅ Applied: created={created}, updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

