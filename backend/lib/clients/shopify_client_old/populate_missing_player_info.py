#!/usr/bin/env python3
"""
Populate missing lineItems.customAttributes values in a target CSV
using data from a source CSV, matching rows by customer.email
(with fallback to Best Contact Email Address).

Usage:
    ./populate_missing_player_info.py <csv_to_migrate_into> <csv_to_migrate_from>

For each row in the target CSV that has empty customAttributes columns,
looks up the customer email in the source CSV, merges ALL source rows
for that email (preferring later createdAt for conflicts), and fills
in the blanks. Fuzzy-matches column names between the two CSVs.

Overwrites the target CSV in place.
"""

import csv
import sys
from difflib import SequenceMatcher
from pathlib import Path


def strip_prefix(col: str) -> str:
    return col.replace("lineItems.customAttributes.", "").strip().lower()


def fuzzy_match(target_col: str, source_cols: list[str],
                threshold: float = 0.75) -> str | None:
    t_name = strip_prefix(target_col)
    best_col, best_score = None, 0.0
    for sc in source_cols:
        s_name = strip_prefix(sc)
        if t_name == s_name:
            return sc
        score = SequenceMatcher(None, t_name, s_name).ratio()
        if score > best_score:
            best_score = score
            best_col = sc
    return best_col if best_score >= threshold else None


def merge_rows(rows: list[dict], custom_cols: list[str]) -> dict:
    """Merge all rows into one composite profile.

    Sorted by createdAt so later values overwrite earlier ones.
    """
    sorted_rows = sorted(rows, key=lambda r: r.get("createdAt", ""))
    merged: dict[str, str] = {}
    for row in sorted_rows:
        for col in custom_cols:
            val = (row.get(col) or "").strip()
            if val:
                merged[col] = val
    return merged


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: ./populate_missing_player_info.py "
            "<csv_to_migrate_into> <csv_to_migrate_from>",
            file=sys.stderr,
        )
        sys.exit(1)

    target_path = Path(sys.argv[1])
    source_path = Path(sys.argv[2])

    for p in (target_path, source_path):
        if not p.is_file():
            print(f"❌ File not found: {p}", file=sys.stderr)
            sys.exit(1)

    with open(target_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        target_fields: list[str] = list(reader.fieldnames or [])
        target_rows = list(reader)

    with open(source_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        source_fields: list[str] = list(reader.fieldnames or [])
        source_rows = list(reader)

    target_custom = [
        c for c in target_fields
        if c.startswith("lineItems.customAttributes.")
    ]
    source_custom = [
        c for c in source_fields
        if c.startswith("lineItems.customAttributes.")
    ]

    col_mapping: dict[str, str] = {}
    for tc in target_custom:
        match = fuzzy_match(tc, source_custom)
        if match:
            col_mapping[tc] = match

    print(f"📋 Mapped {len(col_mapping)}/{len(target_custom)} target columns", file=sys.stderr)
    unmapped = [tc for tc in target_custom if tc not in col_mapping]
    if unmapped:
        print(f"⚠️  Unmapped: {unmapped}", file=sys.stderr)

    # Index source rows by email and by Best Contact Email Address
    email_groups: dict[str, list[dict]] = {}
    for row in source_rows:
        e = (row.get("customer.email") or "").lower().strip()
        if e:
            email_groups.setdefault(e, []).append(row)
        for col in source_custom:
            if "best contact email" in col.lower():
                alt = (row.get(col) or "").lower().strip()
                if alt and alt != e:
                    email_groups.setdefault(alt, []).append(row)

    merged_by_email = {
        e: merge_rows(rows, source_custom)
        for e, rows in email_groups.items()
    }

    filled_count = 0
    row_fill_count = 0

    for row in target_rows:
        email = (row.get("customer.email") or "").lower().strip()
        source = merged_by_email.get(email)

        if not source:
            alt = (
                row.get("lineItems.customAttributes.Best Contact Email Address")
                or ""
            ).lower().strip()
            if alt:
                source = merged_by_email.get(alt)

        if not source:
            continue

        row_filled = False
        for tc, sc in col_mapping.items():
            if not (row.get(tc) or "").strip():
                val = (source.get(sc) or "").strip()
                if val:
                    row[tc] = val
                    filled_count += 1
                    row_filled = True

        if row_filled:
            row_fill_count += 1

    with open(target_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=target_fields, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(target_rows)

    print(
        f"✅ Filled {filled_count} values across {row_fill_count} rows → {target_path}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
