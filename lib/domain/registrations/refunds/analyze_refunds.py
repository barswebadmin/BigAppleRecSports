"""Stage 2 (scripts venv): enrich refund rows with Shopify order + product data
and the canonical refund estimate.

Run: uv run --project lib python lib/domain/registrations/refunds/analyze_refunds.py [in_path] [out_path]
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv
from shop_client import ShopifyClient, schema

from lib.domain.registrations.refunds import (
    EstimateTierKind,
    SeasonDates,
    estimate_refund_due,
    parse_season_date,
    strip_html,
)
from lib.domain.registrations.refunds.refund_calculator import _norm_date

# shop_client does no I/O at import — consumer reads env + constructs client.
dotenv.load_dotenv()
client = ShopifyClient(
    store_id=os.environ["SHOPIFY__STORE_ID"],
    api_version=os.environ["SHOPIFY__API_VERSION"],
    token=os.environ["SHOPIFY__TOKEN__ADMIN"],
)

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

ORDER_FIELDS = [
    "id",
    "name",
    "email",
    "display_financial_status",
    "cancelled_at",
    "total_price_set.shop_money.amount",
    "total_price_set.shop_money.currency_code",
    "refunds.id",
    "refunds.created_at",
    "refunds.total_refunded_set.shop_money.amount",
    "line_items.nodes.id",
    "line_items.nodes.title",
    "line_items.nodes.product.id",
    "line_items.nodes.product.title",
    "line_items.nodes.product.handle",
    "line_items.nodes.product.description_html",
]


_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
)


def parse_season(html: str) -> tuple[SeasonDates, str]:
    """Return (SeasonDates, parser_used). Falls back to the 'IMPORTANT DATES /
    Regular Season starts on …' format used by older (e.g. Spring 2026) products
    when the canonical 'Season Dates START – END' pattern is absent."""
    season = SeasonDates.from_html(html or "")
    if season.start_date:
        return season, "season_dates"

    text = strip_html(html or "")
    m = re.search(
        rf"Regular Season starts on\s+((?:{_MONTHS})\s+\d{{1,2}},?\s*\d{{4}})",
        text,
        re.IGNORECASE,
    )
    if not m:
        return season, "none"
    start = parse_season_date(m.group(1))
    if start is None:
        return season, "none"

    weeks_m = re.search(r"Total\s*#?\s*of weeks[^:]*:\s*(\d+)", text, re.IGNORECASE)
    total_weeks = int(weeks_m.group(1)) if weeks_m else None

    off_seg = re.search(
        r"Off Week\(s\)(.*?)(?:Total\s*#|REGISTRATION|$)", text, re.IGNORECASE
    )
    off_norm: list[str] = []
    if off_seg:
        for tok in re.findall(rf"((?:{_MONTHS})\s+\d{{1,2}})", off_seg.group(1)):
            dt = parse_season_date(f"{tok}, {start.year}")
            if dt:
                off_norm.append(_norm_date(dt))

    return (
        SeasonDates(
            start_date=_norm_date(start),
            off_dates=", ".join(off_norm) or None,
            total_weeks=total_weeks,
        ),
        "important_dates",
    )


def parse_ts(ts: str) -> datetime | None:
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M"):
        try:
            naive = datetime.strptime(ts, fmt)
            return naive.replace(tzinfo=ET).astimezone(UTC)
        except ValueError:
            continue
    return None


def money(node: Any) -> float:
    """Extract amount from a MoneyBag-shaped Box (``.shop_money.amount``)."""
    if not node:
        return 0.0
    try:
        return float(node.shop_money.amount or 0)
    except (AttributeError, KeyError, TypeError, ValueError):
        return 0.0


def main() -> None:
    in_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/refund_rows.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/refund_analysis.json"

    rows = json.loads(Path(in_path).read_text())

    results = []
    for row in rows:
        rec: dict = {
            "row": row["row"],
            "timestamp": row["timestamp"],
            "order_number": row["order_number"],
            "refund_to": row["refund_to"],
            "processed": row["processed"],
            "requester": f"{row['first_name']} {row['last_name']}".strip(),
            "email": row["email"],
            "note": row["note"],
        }
        ts_utc = parse_ts(row["timestamp"])
        rec["submitted_at_utc"] = ts_utc.isoformat() if ts_utc else None

        try:
            # Shopify order search needs the `#` prefix for exact-name match.
            matches = client.run(
                schema.orders.queries.by_name,
                name=f"#{row['order_number']}",
                returns=ORDER_FIELDS,
            )
        except Exception as e:  # noqa: BLE001
            rec["error"] = f"lookup failed: {e}"
            results.append(rec)
            continue
        order = next(iter(matches or []), None)
        if order is None:
            rec["error"] = "order not found"
            results.append(rec)
            continue

        rec["order_name"] = order.name
        rec["order_email"] = order.email
        rec["financial_status"] = order.display_financial_status
        rec["cancelled_at"] = order.cancelled_at

        order_total = money(order.total_price_set)
        refund_nodes = order.refunds or []
        total_refunded = sum(money(r.total_refunded_set) for r in refund_nodes)
        refundable = max(0.0, order_total - total_refunded)
        rec["amount_paid"] = round(order_total, 2)
        rec["already_refunded"] = round(total_refunded, 2)
        rec["refundable_balance"] = round(refundable, 2)
        rec["existing_refunds"] = [
            {
                "id": r.id,
                "created_at": r.created_at,
                "amount": round(money(r.total_refunded_set), 2),
            }
            for r in refund_nodes
        ]

        product = None
        for li in (order.line_items.nodes if order.line_items else []) or []:
            if li.product:
                product = li.product
                break
        if product is not None:
            rec["product_title"] = product.title
            rec["product_handle"] = product.handle
            season, parser_used = parse_season(product.description_html or "")
            rec["season_start"] = season.start_date
            rec["season_weeks"] = season.total_weeks
            rec["season_off_dates"] = season.off_dates
            rec["season_parser"] = parser_used
        else:
            season = SeasonDates()
            rec["product_title"] = None
            rec["season_start"] = None
            rec["season_parser"] = "no_product"

        # Estimate (on refundable balance, matching the Lambda path)
        tier_kind = (
            EstimateTierKind.REFUND_TO_ORIGINAL
            if row["refund_to"] == "original_method"
            else EstimateTierKind.STORE_CREDIT
        )
        est = estimate_refund_due(season, refundable, tier_kind, ts_utc)
        rec["estimate_success"] = est.success
        rec["estimate_amount"] = round(est.amount, 2)
        rec["estimate_pct"] = est.percentage
        rec["estimate_timing"] = est.timing
        rec["estimate_message"] = est.message
        results.append(rec)

    Path(out_path).write_text(json.dumps(results, indent=2, default=str))

    # Console table
    hdr = (f"{'row':>3} {'order':>8} {'type':>10} {'paid':>8} {'refunded':>9} "
           f"{'balance':>8} {'season':>10} {'wks':>3} {'est':>8} {'pct':>4}  status")
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        if r.get("error"):
            print(f"{r['row']:>3} {r['order_number']:>8} {r['refund_to']:>10} "
                  f"{'':>8} {'':>9} {'':>8} {'':>10} {'':>3} {'':>8} {'':>4}  ERROR: {r['error']}")
            continue
        est = f"{r['estimate_amount']:>7.2f}" if r["estimate_success"] else "  REVIEW"
        pct = f"{r['estimate_pct']:>3}%" if r["estimate_success"] else "  - "
        status = str(r["financial_status"] or "")
        print(f"{r['row']:>3} {r['order_name']:>8} {r['refund_to']:>10} "
              f"{r['amount_paid']:>8.2f} {r['already_refunded']:>9.2f} "
              f"{r['refundable_balance']:>8.2f} {str(r.get('season_start')):>10} "
              f"{str(r.get('season_weeks') or ''):>3} {est:>8} "
              f"{pct}  {status}"
              f"{'  [PROCESSED]' if r['processed'] == 'TRUE' else ''}")
    print(f"\nWrote {len(results)} records to {out_path}")


if __name__ == "__main__":
    main()
