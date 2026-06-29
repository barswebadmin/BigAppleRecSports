"""Flatten JSON records to CSV with configurable columns.

Default: converts /tmp/refund_analysis.json to CSV at repo root.
Usage: python lib/tooling/json_to_csv.py [in_path] [out_filename]
"""

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

COLUMNS = [
    "row", "timestamp", "submitted_at_utc", "order_number", "order_name",
    "requester", "email", "refund_to", "processed",
    "amount_paid", "already_refunded", "refundable_balance", "financial_status",
    "product_title", "product_handle", "season_start", "season_weeks",
    "season_off_dates", "season_parser",
    "estimate_success", "estimate_amount", "estimate_pct", "estimate_timing",
    "estimate_message", "note", "error",
]


def main() -> None:
    in_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/refund_analysis.json"
    out_path = REPO / (sys.argv[2] if len(sys.argv) > 2 else "refund_analysis_rows_237plus.csv")
    records = json.loads(Path(in_path).read_text())
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, "") for k in COLUMNS})
    print(f"Wrote {len(records)} rows to {out_path}")


if __name__ == "__main__":
    main()
