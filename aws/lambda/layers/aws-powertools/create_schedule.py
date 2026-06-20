"""Create a one-shot EventBridge schedule that invokes a registration-management Lambda.

Wraps the `aws scheduler create-schedule` call with the conventions BARS uses:

- Lambda target ARN by action shorthand (`set-reg-live`, `update-reg-status`,
  `close-reg`) — points at the current production Lambda
  (`updateRegistrationStatus` v2.3.0 as of 2026-06-09).
- Sport-prefixed schedule group (`move-inventory-between-variants-{sport}` /
  `set-product-live` / `adjust-prices-week-N`) chosen automatically from action.
- ET timezone, FlexibleTimeWindow OFF, ActionAfterCompletion=NONE (matches
  every active 2026 schedule).
- Retry policy MaximumEventAgeInSeconds=1800, MaximumRetryAttempts=5 (production
  default — the Lambda itself is idempotency-safe via `wait_until_next_minute`
  + per-variant inventory snapshots).
- Fire time rule: pass the **public-visible** time (e.g. 18:00); this script
  subtracts 1 minute so EventBridge fires at 17:59 and the Lambda's
  `wait_until_next_minute` ticks over to 18:00.

Examples:

  # Move all inventory: variant A -> variant B, surfaces at 6pm ET tonight
  uv run --project scripts python scripts/aws/create_schedule.py update-reg-status \
      --product 7678746132574 \
      --source-variant 42896444325982 \
      --target-variant 42896444358750 \
      --at 2026-06-16T18:00 \
      --sport pb

  # Veteran go-live: add 20 units to vet variant at 7pm ET
  uv run --project scripts python scripts/aws/create_schedule.py set-reg-live \
      --product 7678746132574 \
      --target-variant 42896444325982 \
      --inventory-to-add 20 \
      --at 2026-06-16T19:00 \
      --sport pb

The script prints the resulting Schedule ARN on success.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

# ── Constants pulled from production schedules / Lambda ──────────────────────

ACCOUNT = "084375563770"
REGION = "us-east-1"

LAMBDA_ARN = f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:updateRegistrationStatus"
SCHEDULER_ROLE_ARN = (
    f"arn:aws:iam::{ACCOUNT}:role/service-role/Amazon_EventBridge_Scheduler_LAMBDA_3bc414251c"
)

# Every active 2026 schedule uses these.
DEFAULT_RETRY = {"MaximumEventAgeInSeconds": 1800, "MaximumRetryAttempts": 5}

# action -> group prefix. Sport suffix is appended for move/update-reg-status.
ACTION_GROUPS = {
    "set-reg-live": "set-product-live",
    "update-reg-status": "move-inventory-between-variants",
    "close-reg": "move-inventory-between-variants",
}

KNOWN_SPORTS = {"pb", "kb", "db", "bowl", "misc"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("action", choices=sorted(ACTION_GROUPS))
    p.add_argument("--product", required=True, help="Shopify product numeric ID or GID")
    p.add_argument("--target-variant", required=True, help="Target variant numeric ID")
    p.add_argument("--source-variant", help="Source variant numeric ID (required for update-reg-status / close-reg)")
    p.add_argument("--inventory-to-add", type=int, help="Units to add (required for set-reg-live)")
    p.add_argument(
        "--at",
        required=True,
        help="Public-visible fire time in ET as ISO without seconds, e.g. 2026-06-16T18:00. The schedule will be set 1 minute earlier so the Lambda's wait_until_next_minute lands on this time.",
    )
    p.add_argument(
        "--sport",
        help="Sport key for the schedule group suffix (pb, kb, db, bowl, misc). Required for update-reg-status/close-reg; ignored for set-reg-live.",
    )
    p.add_argument(
        "--name",
        help="Schedule name. Defaults to '{action-prefix}-{sport}-{handle-tail}'; will fail at create-schedule if it collides — pass --name to override.",
    )
    p.add_argument("--bot-name", default="registrations", help="Slack bot name (defaults to 'registrations')")
    p.add_argument(
        "--slack-channel",
        help="Slack channel (without #). Auto-derived from product handle ({sport}-{day}-{division}) if omitted.",
    )
    p.add_argument(
        "--slack-tag",
        help="Slack team tag (with @). Auto-derived as @{channel}-team if omitted.",
    )
    p.add_argument("--dry-run", action="store_true", help="Print the schedule JSON and exit without creating")
    return p.parse_args()


def normalize_product_id(value: str) -> str:
    m = re.search(r"/Product/(\d+)", value)
    return m.group(1) if m else value


def fetch_product_handle(product_id: str) -> str | None:
    """Best-effort handle fetch via Shopify Admin GraphQL.

    Used only to derive slackConfig defaults. Returns None on any error — the
    Lambda itself auto-derives slackConfig from the handle if slackConfig is
    omitted from the event, so this is just for nicer dry-run previews.
    """
    import os
    token = os.environ.get("SHOPIFY__TOKEN__ADMIN")
    store = os.environ.get("SHOPIFY__STORE_ID")
    ver = os.environ.get("SHOPIFY__API_VERSION", "2026-07")
    if not token or not store:
        return None
    gid = f"gid://shopify/Product/{product_id}"
    body = json.dumps({"query": "query($id: ID!){ product(id:$id){ handle } }", "variables": {"id": gid}}).encode()
    req = urllib.request.Request(
        f"https://{store}.myshopify.com/admin/api/{ver}/graphql.json",
        data=body,
        headers={"Content-Type": "application/json", "X-Shopify-Access-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return ((json.loads(r.read()) or {}).get("data") or {}).get("product", {}).get("handle")
    except Exception:
        return None


def derive_slack_config(handle: str | None, override_channel: str | None, override_tag: str | None, bot: str) -> dict | None:
    """Mirror lib slack_config derivation: {sport}-{day}-{division}div handle → channel."""
    channel = override_channel
    tag = override_tag
    if (not channel or not tag) and handle:
        m = re.match(r"\d{4}-[a-z]+-([a-z]+)-([a-z]+)-([a-z]+)div", handle)
        if m:
            sport, day, division = m.groups()
            channel = channel or f"{sport}-{day}-{division}"
            tag = tag or f"@{sport}-{day}-{division}-team"
    if not channel or not tag:
        return None
    return {"botName": bot, "channelName": channel, "tagTarget": tag}


def public_to_fire_time(public_iso: str) -> str:
    fmt = "%Y-%m-%dT%H:%M"
    try:
        d = dt.datetime.strptime(public_iso, fmt)
    except ValueError:
        d = dt.datetime.fromisoformat(public_iso)
    return (d - dt.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S")


def build_payload(args: argparse.Namespace, slack_cfg: dict | None) -> dict:
    product_id = normalize_product_id(args.product)
    payload: dict = {"action": args.action, "product": product_id, "targetVariant": int(args.target_variant)}
    if args.action == "set-reg-live":
        if args.inventory_to_add is None:
            sys.exit("--inventory-to-add is required for set-reg-live")
        payload["inventoryToAdd"] = args.inventory_to_add
    else:
        if not args.source_variant:
            sys.exit(f"--source-variant is required for {args.action}")
        payload["sourceVariant"] = int(args.source_variant)
    if slack_cfg:
        payload["slackConfig"] = slack_cfg
    return payload


def build_schedule(args: argparse.Namespace, payload: dict) -> dict:
    group_prefix = ACTION_GROUPS[args.action]
    if args.action == "set-reg-live":
        group = group_prefix
    else:
        if not args.sport or args.sport not in KNOWN_SPORTS:
            sys.exit(f"--sport is required for {args.action} and must be one of {sorted(KNOWN_SPORTS)}")
        group = f"{group_prefix}-{args.sport}"

    name = args.name
    if not name:
        sport_part = f"-{args.sport}" if args.sport else ""
        name = f"{args.action}{sport_part}-{payload['product']}"

    fire_at = public_to_fire_time(args.at)
    return {
        "Name": name,
        "GroupName": group,
        "ScheduleExpression": f"at({fire_at})",
        "ScheduleExpressionTimezone": "America/New_York",
        "FlexibleTimeWindow": {"Mode": "OFF"},
        "ActionAfterCompletion": "NONE",
        "State": "ENABLED",
        "Description": f"{args.action} for product {payload['product']} at {args.at} ET (fires 1 min earlier)",
        "Target": {
            "Arn": LAMBDA_ARN,
            "RoleArn": SCHEDULER_ROLE_ARN,
            "Input": json.dumps(payload),
            "RetryPolicy": DEFAULT_RETRY,
        },
    }


def main() -> None:
    args = parse_args()
    product_id = normalize_product_id(args.product)

    handle = fetch_product_handle(product_id)
    slack_cfg = derive_slack_config(handle, args.slack_channel, args.slack_tag, args.bot_name)
    payload = build_payload(args, slack_cfg)
    schedule = build_schedule(args, payload)

    print(json.dumps(schedule, indent=2))

    if args.dry_run:
        return

    # `assume bars --exec` needs a TTY for granted's session check; capture_output
    # deadlocks it. Write JSON to a temp file (avoids 250kb CLI arg + shell-quoting)
    # and let stdout/stderr stream through to the user's terminal.
    fd, path = tempfile.mkstemp(prefix="sched_", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(schedule, f)
        rc = subprocess.call(
            [
                "assume", "bars", "--exec", "--",
                "aws", "scheduler", "create-schedule",
                "--cli-input-json", f"file://{path}",
                "--query", "ScheduleArn", "--output", "text",
            ],
        )
    finally:
        os.unlink(path)
    sys.exit(rc)


if __name__ == "__main__":
    main()
