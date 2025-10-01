from __future__ import annotations

import argparse
import json
import os
import re
from typing import Dict, List, Optional, Tuple

from config import config
from modules.integrations.slack.slack_orchestrator import SlackOrchestrator


def normalize_handle(text: str) -> str:
    # lowercase, replace non-alphanum with hyphens, collapse repeats
    t = text.strip().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    t = re.sub(r"-+", "-", t).strip("-")
    return t


def load_json(path: str) -> Optional[dict]:
    if not path or not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_group_plans(
    grouped_assignments: Dict[str, Dict[str, List[str]]],
    name_to_id: Dict[str, str],
    group_overrides: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    plans: Dict[str, List[str]] = {}

    # exact sport-night-division groups
    for group_key, roles in grouped_assignments.items():
        handle = normalize_handle(group_key)
        members: List[str] = []
        for person in roles.get("director", []) + roles.get("ops", []):
            slack_id = name_to_id.get(person) or name_to_id.get(person.split(" (")[0])
            if slack_id:
                members.append(slack_id)
        # apply group overrides
        if group_overrides.get(handle):
            members = sorted(list(set(members + group_overrides[handle])))
        plans[handle] = members

    # also build sport-night aggregates
    aggregates: Dict[Tuple[str, str], List[str]] = {}
    for group_key, roles in grouped_assignments.items():
        # keys look like 'dodgeball-monday-big ball' -> split into sport, night, division
        parts = group_key.split("-")
        if len(parts) >= 2:
            sport, night = parts[0], parts[1]
            agg_key = (sport, night)
            agg_list = aggregates.setdefault(agg_key, [])
            for person in roles.get("director", []) + roles.get("ops", []):
                slack_id = name_to_id.get(person) or name_to_id.get(person.split(" (")[0])
                if slack_id:
                    agg_list.append(slack_id)

    for (sport, night), ids in aggregates.items():
        handle = normalize_handle(f"{sport}-{night}")
        ids = sorted(list(set(ids + group_overrides.get(handle, []))))
        plans.setdefault(handle, ids)

    return plans


def main() -> int:
    parser = argparse.ArgumentParser(description="Slack usergroup dry-run sync from leadership assignments")
    parser.add_argument("--assignments", default="/workspace/data/leadership_assignments.json", help="Grouped assignments JSON (from scraper)")
    parser.add_argument("--name-to-id", default="/workspace/data/slack_name_to_id.json", help="Optional name->Slack ID mapping JSON")
    parser.add_argument("--group-overrides", default="/workspace/data/slack_group_overrides.json", help="Optional group handle->Slack IDs mapping JSON")
    parser.add_argument("--dry-run", action="store_true", help="Only check and print diffs, don't modify Slack")
    args = parser.parse_args()

    if not os.path.exists(args.assignments):
        print(f"❌ Assignments file not found: {args.assignments}")
        return 1

    assignments = json.load(open(args.assignments, "r", encoding="utf-8"))
    name_to_id = load_json(args.name_to_id) or {}
    group_overrides = load_json(args.group_overrides) or {}

    plans = build_group_plans(assignments, name_to_id, group_overrides)

    token = config.active_slack_bot_token
    slack_orchestrator = SlackOrchestrator(token) if token else None
    existing_handles: Dict[str, str] = {}

    if slack_orchestrator and token:
        try:
            usergroups = slack_orchestrator.list_usergroups()
            for ug in usergroups:
                handle = ug.get("handle")
                gid = ug.get("id")
                if handle and gid:
                    existing_handles[handle] = gid
        except Exception as e:
            print(f"⚠️ Could not list usergroups: {e}")

    to_create = []
    to_update = []
    for handle, ids in plans.items():
        if handle in existing_handles:
            to_update.append((handle, existing_handles[handle], ids))
        else:
            to_create.append((handle, ids))

    print(f"🧭 Planned groups: {len(plans)} | existing: {len(existing_handles)}")
    print(f"➕ To create: {len(to_create)} | 🔄 To update: {len(to_update)}")

    # Show a small diff preview
    preview = list(plans.items())[:12]
    for handle, ids in preview:
        print(f"- {handle}: {len(ids)} member(s)")

    if args.dry_run or not slack_orchestrator or not token:
        print("✅ Dry run complete. Provide a Slack token to apply changes.")
        return 0

    # Apply changes
    created = 0
    updated = 0
    for handle, ids in to_create:
        gid = slack_orchestrator.create_usergroup(name=handle.replace("-", " ").title(), handle=handle)
        if gid and ids:
            if slack_orchestrator.update_usergroup_users(gid, ids):
                created += 1
    for handle, gid, ids in to_update:
        if gid and ids:
            if slack_orchestrator.update_usergroup_users(gid, ids):
                updated += 1

    print(f"✅ Applied: created={created}, updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

