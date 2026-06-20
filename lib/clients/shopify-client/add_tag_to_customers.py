#!/usr/bin/env -S uv run --project scripts
"""Add a tag to multiple customers by email with optional veteran notification.

Usage (from monorepo root):
    scripts/shopify/add_tag_to_customers.py [--dry-run | -D] <csv_file_path>
    scripts/shopify/add_tag_to_customers.py [--dry-run | -D] "2026-spring-dodgeball-monday-open-early"
    scripts/shopify/add_tag_to_customers.py [--dry-run | -D] 2026 spring dodgeball monday open early
    scripts/shopify/add_tag_to_customers.py [--dry-run | -D]

    --dry-run / -D: Preview only — no Shopify tag updates, no veteran emails.

Note: Shebang automatically uses --project scripts for shared_utilities access.
"""

import csv
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import dotenv

from shop_client import ShopifyClient, schema

# shop_client does no I/O at import — consumer reads env + constructs client.
dotenv.load_dotenv()
client = ShopifyClient(
    store_id=os.environ["SHOPIFY__STORE_ID"],
    api_version=os.environ["SHOPIFY__API_VERSION"],
    token=os.environ["SHOPIFY__TOKEN__ADMIN"],
)

_DRY_RUN_FLAGS = frozenset({"--dry-run", "-D"})


def _strip_dry_run_flags(args: list[str]) -> tuple[bool, list[str]]:
    """Return (dry_run, args) with --dry-run / -D removed."""
    dry_run = False
    filtered: list[str] = []
    for arg in args:
        if arg in _DRY_RUN_FLAGS:
            dry_run = True
        else:
            filtered.append(arg)
    return dry_run, filtered


def _is_veteran_tag(tag: str) -> bool:
    """Check if tag matches veteran eligibility pattern."""
    return bool(re.match(r"\d{4}-(spring|summer|fall|winter)-.+-veteran$", tag, re.IGNORECASE))


def _parse_veteran_tag(tag: str) -> dict[str, str] | None:
    """Parse veteran tag into email parameters.

    Expected format: YYYY-SEASON-SPORT-DAY-DIVISIONdiv-veteran
    Example: 2026-spring-dodgeball-monday-opendiv-veteran
    """
    pattern = r"^(?P<year>\d{4})-(?P<season>spring|summer|fall|winter)-(?P<sport>\w+)-(?P<day>\w+)-(?P<division>\w+)-veteran$"
    match = re.match(pattern, tag, re.IGNORECASE)
    if not match:
        return None

    division = match.group("division").lower()
    if division.endswith("div"):
        division = division[:-3]

    return {
        "year": match.group("year"),
        "season": match.group("season").lower(),
        "sport": match.group("sport").lower(),
        "day": match.group("day").lower(),
        "division": division,
    }


SEASONS_MAP = {"season": ["winter", "spring", "summer", "fall"]}
SPORTS_MAP = {"sport": ["dodgeball", "kickball", "bowling", "pickleball"]}
DAYS_MAP = {"day": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}
DIVISIONS_MAP = {"division": ["wtnb", "open"]}
REG_PERIODS_MAP = {"registration_period": ["veteran", "waitlist"]}

def _normalize_division(division: str) -> str:
    """Map tag-style division (opendiv, wtnbdiv) to leadership email segment (open, wtnb)."""
    d = division.lower()
    if d.endswith("div"):
        d = d[:-3]
    return d


def _validate_for_enum(raw_str: str, enum_map: dict[str, list[str]]) -> str | None:
    """Validate string against enum list, return None if invalid."""
    normalized = raw_str.lower()
    if normalized.endswith("div"):
        normalized = normalized[:-3]
    for valid_list in enum_map.values():
        if normalized in valid_list:
            return normalized
    return None


def parse_league_input_args(identifiers: str) -> dict[str, str | dict]:
    """Parse hyphenated league identifiers string.

    Returns dict with keys: year, season, sport, day, division, registration_period
    Each value is either the normalized string or None if invalid/missing.
    """
    league_details = {
        "year": None,
        "season": SEASONS_MAP,
        "sport": SPORTS_MAP,
        "day": DAYS_MAP,
        "division": DIVISIONS_MAP,
        "registration_period": REG_PERIODS_MAP,
    }

    if not identifiers.strip():
        return league_details

    parts = identifiers.split("-")

    for part in parts:
        if part.isdigit() and len(part) == 4:
            league_details["year"] = part
        elif validated := _validate_for_enum(part, SEASONS_MAP):
            league_details["season"] = validated
        elif validated := _validate_for_enum(part, SPORTS_MAP):
            league_details["sport"] = validated
        elif validated := _validate_for_enum(part, DAYS_MAP):
            league_details["day"] = validated
        elif validated := _validate_for_enum(part, DIVISIONS_MAP):
            league_details["division"] = validated
        elif validated := _validate_for_enum(part, REG_PERIODS_MAP):
            league_details["registration_period"] = validated

    return league_details


def _prompt_numbered_choice(component_name: str, valid_options: list[str]) -> str:
    """Prompt user to select from numbered options."""
    print(f"\n{component_name.capitalize()}:")
    for i, option in enumerate(valid_options, 1):
        print(f"  {i}. {option}")

    while True:
        choice = input(f"Select {component_name} (1-{len(valid_options)}): ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(valid_options):
                return valid_options[idx]
        print(f"❌ Invalid selection. Enter a number between 1 and {len(valid_options)}")


def _construct_tag(components: dict[str, str]) -> str:
    """Construct tag string from components."""
    division = _normalize_division(components["division"])
    return (
        f"{components['year']}-{components['season']}-{components['sport']}-"
        f"{components['day']}-{division}div-{components['registration_period']}"
    )


def _construct_leadership_email(components: dict[str, str]) -> str:
    """Construct default leadership email from components."""
    division = _normalize_division(components["division"])
    return f"{components['sport']}.{components['day']}.{division}@bigapplerecsports.com"


def _prompt_send_veteran_emails(tag: str, recipients: list[str], default_leadership_email: str | None = None) -> None:
    """Prompt user to send veteran eligibility emails."""
    print("\n" + "=" * 60)
    print("🏷️  VETERAN TAG DETECTED")
    print("=" * 60)

    params = _parse_veteran_tag(tag)
    if not params:
        print("⚠️  Could not parse veteran tag format. Email sending skipped.")
        return

    division_display = "WTNB" if params['division'] == "wtnb" else params['division'].capitalize()

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from google_api.send_email import _prompt_opens_datetime

    opens_datetime = _prompt_opens_datetime()

    print("\n📋 Email Details:")
    print(f"   Sport: {params['sport'].capitalize()}")
    print(f"   Day: {params['day'].capitalize()}")
    print(f"   Division: {division_display}")
    print(f"   Season: {params['season'].capitalize()} {params['year']}")
    print(f"   Opens: {opens_datetime}")
    print(f"   Recipients: {len(recipients)}")

    response = input("\n📧 Send veteran eligibility emails to these customers? [Y/n]: ").strip().lower()
    if response in ("n", "no"):
        print("Skipping email send.")
        return

    if default_leadership_email:
        leadership_email = default_leadership_email
        print(f"Alias to CC and set as the reply-to address (default: {leadership_email})")
    else:
        leadership_email = input("Leadership email for CC/replies [joe@bigapplerecsports.com]: ").strip()
        if not leadership_email:
            leadership_email = "joe@bigapplerecsports.com"

    print("\n📤 Sending emails...")
    try:
        from google_api.send_email import send_veteran_emails

        send_veteran_emails(
            recipients=recipients,
            sport=params["sport"],
            day=params["day"],
            division=params["division"],
            season=params["season"],
            year=params["year"],
            leadership_email=leadership_email,
            opens_datetime=opens_datetime,
            impersonate_user="web@bigapplerecsports.com",
        )
    except Exception as e:
        print(f"❌ Failed to send emails: {e}")
        print("You can manually send emails using:")
        print(f"  uv run scripts/google_api/send_email.py {params['sport']} {params['day']} "
              f"{params['division']} {params['season']} {params['year']} {leadership_email} " +
              " ".join(recipients))


def main(dry_run: bool | None = None) -> None:
    if dry_run is None:
        dry_run, args = _strip_dry_run_flags(sys.argv[1:])
    else:
        _, args = _strip_dry_run_flags(sys.argv[1:])

    if dry_run:
        print("[DRY RUN] No Shopify updates or emails will be sent.\n")

    # Check if first arg is a CSV/XLSX file path
    use_csv_mode = False
    csv_file_path = None

    if len(args) >= 1:
        potential_path = Path(args[0])
        if potential_path.suffix.lower() in [".csv", ".xlsx"]:
            if potential_path.exists():
                use_csv_mode = True
                csv_file_path = potential_path
            else:
                print(f"❌ File not found: {potential_path}")
                sys.exit(1)

    # If not CSV mode and too many args, show usage
    if not use_csv_mode and len(args) > 6:
        print("Usage: add_tag_to_customers.py [--dry-run | -D] <csv_file_path>")
        print("   or: add_tag_to_customers.py [--dry-run | -D] [year-season-sport-day-division-registration_period]")
        print("   or: add_tag_to_customers.py [--dry-run | -D] [year] [season] [sport] [day] [division] [registration_period]")
        print("   or: add_tag_to_customers.py [--dry-run | -D]  (interactive)")
        sys.exit(1)

    print("🏷️  Interactive Tag Builder\n")

    # Handle CSV mode
    if use_csv_mode:
        print(f"📄 Reading: {csv_file_path}")

        with open(csv_file_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            print("❌ CSV file is empty")
            sys.exit(1)

        if "email" not in rows[0]:
            print(f"❌ CSV must have 'email' column. Found columns: {list(rows[0].keys())}")
            sys.exit(1)

        emails = [row["email"].strip() for row in rows if row.get("email", "").strip()]
        if not emails:
            print("❌ No valid emails found in CSV")
            sys.exit(1)

        # Check for duplicates
        seen = {}
        duplicates = []
        for email in emails:
            email_lower = email.lower()
            if email_lower in seen:
                duplicates.append(email)
            else:
                seen[email_lower] = email

        unique_emails = list(seen.values())

        print(f"📧 Total emails in CSV: {len(emails)}")
        print(f"📧 Unique emails: {len(unique_emails)}")

        if duplicates:
            print(f"\n⚠️  WARNING: {len(duplicates)} DUPLICATE email(s) found in CSV:")
            print("=" * 60)
            for email in duplicates:
                print(f"   {email}")
            print("=" * 60)

        # Extract identifiers from first row
        first_row = rows[0]
        identifier_values = [v for k, v in first_row.items() if k.lower() != "email" and v.strip()]
        identifiers = "-".join(identifier_values) if identifier_values else ""
        print(f"🔍 Detected identifiers: '{identifiers}'\n")

    else:
        # Handle command-line or interactive mode
        if len(args) == 0:
            # Prompt for file path or manual entry
            print("Choose input method:")
            print("  1. Provide CSV file path")
            print("  2. Paste emails directly (opens editor)")

            while True:
                choice = input("\nSelect (1-2) or press ENTER for option 2: ").strip()
                if choice == "" or choice == "2":
                    break
                if choice == "1":
                    file_path_input = input("CSV file path: ").strip()
                    if file_path_input:
                        potential_path = Path(file_path_input)
                        if potential_path.exists():
                            args = [file_path_input]
                            return main(dry_run=dry_run)
                        print(f"❌ File not found: {potential_path}")
                        continue
                print("Invalid selection")

        # Join args to identifiers
        if len(args) == 0:
            identifiers = ""
        elif len(args) == 1:
            identifiers = args[0].strip().replace(" ", "-")
        else:
            identifiers = "-".join(args)

        unique_emails = None

    # Parse league identifiers
    league_details: dict[str, str | dict] = parse_league_input_args(identifiers)

    # Prompt for any missing components
    for identifier, value_or_map in league_details.items():
        if isinstance(value_or_map, dict):
            valid_options = list(value_or_map.values())[0]
            league_details[identifier] = _prompt_numbered_choice(identifier, valid_options)

    current_year = str(datetime.now().year)
    if league_details["year"] is None:
        response = input(f"Year [{current_year}]: ").strip()
        league_details["year"] = response if response else current_year

    tag_to_add = _construct_tag(league_details)
    print(f"\n✅ Constructed tag: '{tag_to_add}'")

    default_leadership_email = _construct_leadership_email(league_details)
    print("\n📧 Leadership Email Configuration")
    response = input(f"Leadership email [{default_leadership_email}]: ").strip()
    leadership_email = response if response else default_leadership_email
    print(f"Using: {leadership_email}")

    # Get emails from editor if not from CSV
    if unique_emails is None:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as tmp:
            tmp.write("# Enter one email per line (lines starting with # are ignored)\n")
            tmp.write("# Save and close editor to continue\n\n")
            tmp_path = Path(tmp.name)

        try:
            try:
                subprocess.run(["cursor", "-w", str(tmp_path)], check=True)
            except subprocess.CalledProcessError:
                print("❌ Editor closed without saving")
                sys.exit(1)

            with open(tmp_path) as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

            if not lines:
                print("❌ No emails provided")
                sys.exit(1)

            # Check for duplicates in manual entry
            seen = {}
            duplicates = []
            for email in lines:
                email_lower = email.lower()
                if email_lower in seen:
                    duplicates.append(email)
                else:
                    seen[email_lower] = email

            unique_emails = list(seen.values())

            if duplicates:
                print(f"\n⚠️  WARNING: {len(duplicates)} DUPLICATE email(s) found:")
                print("=" * 60)
                for email in duplicates:
                    print(f"   {email}")
                print("=" * 60)

        finally:
            tmp_path.unlink(missing_ok=True)

    print(f"\n📧 Processing {len(unique_emails)} unique emails...")
    print(f"🏷️  Tag to add: '{tag_to_add}'\n")

    print("🔍 Searching for customers in Shopify...")
    found: list[dict] = []
    not_found: list[str] = []
    for email in unique_emails:
        # connection search `email:foo@bar` can return near-matches; filter exact.
        matches = client.run(
            schema.customers.queries.by_email,
            email=email,
            returns=["id", "email", "tags"],
        )
        exact = next((m for m in matches if (m.email or "").lower() == email.lower()), None)
        if exact:
            found.append(exact)
        else:
            not_found.append(email)

    print(f"\n✅ Found {len(found)} customers in Shopify")

    if not_found:
        print(f"\n❌ WARNING: {len(not_found)} email(s) NOT FOUND in Shopify:")
        print("=" * 60)
        for email in not_found:
            print(f"   {email}")
        print("=" * 60)
        print()

    if not found:
        print("\n❌ No customers found. Exiting.")
        sys.exit(0)

    updates = []
    for customer in found:
        current_tags = list(customer.tags or [])
        if tag_to_add in current_tags:
            print(f"  ⏭️  {customer.email}: already has tag '{tag_to_add}'")
            continue

        new_tags = current_tags + [tag_to_add]
        updates.append({
            "id": customer.id,
            "email": customer.email,
            "tags": new_tags,
        })

    if not updates:
        print("\n✅ All customers already have the tag. Nothing to update.")
        if _is_veteran_tag(tag_to_add):
            all_emails = [c.email for c in found]
            _prompt_send_veteran_emails(tag_to_add, all_emails, leadership_email)
        sys.exit(0)

    if dry_run:
        print(f"\n[DRY RUN] Would add tag '{tag_to_add}' to {len(updates)} customer(s):")
        for update in updates:
            print(f"  - {update['email']}")
        if _is_veteran_tag(tag_to_add):
            would_email = [u["email"] for u in updates]
            print(f"\n[DRY RUN] Would prompt to send veteran eligibility emails to {len(would_email)} recipient(s).")
            print(f"[DRY RUN] Leadership email: {leadership_email}")
            params = _parse_veteran_tag(tag_to_add)
            if params:
                print("[DRY RUN] Manual send command (if needed later):")
                print(
                    f"  uv run scripts/google_api/send_email.py {params['sport']} {params['day']} "
                    f"{params['division']} {params['season']} {params['year']} {leadership_email} "
                    + " ".join(would_email)
                )
        return

    print(f"\n🔄 Updating {len(updates)} customers...")
    updated: list[str] = []
    errors: list[str] = []
    for u in updates:
        try:
            payload = client.run(
                schema.customers.mutations.update,
                id=u["id"],
                tags=u["tags"],
                returns=["customer.id", "customer.email"],
            )
            if payload.user_errors:
                print(f"  ❌ {u['email']}: {list(payload.user_errors)}")
                errors.append(u["email"])
            else:
                updated.append(u["email"])
        except Exception as e:  # noqa: BLE001
            print(f"  ❌ {u['email']}: {e}")
            errors.append(u["email"])

    print(f"\n✅ Successfully updated {len(updated)} customers")
    if errors:
        print(f"❌ Failed to update {len(errors)} customers:")
        for email in errors:
            print(f"  - {email}")

    if updated and _is_veteran_tag(tag_to_add):
        _prompt_send_veteran_emails(
            tag_to_add,
            [c.email for c in found],
            leadership_email,
        )


if __name__ == "__main__":
    main()
