#!/usr/bin/env -S uv run --project scripts
"""
Export all Shopify orders for a given product to a CSV.

Fetches every order that contains the product, flattens nested fields with dot
notation, and pivots order-level custom_attributes into their own columns.
Custom-attribute column names are deduped across all orders and sorted
alphabetically before the CSV header is written.

Usage (from monorepo root):
    scripts/export_orders_by_product.py <product_id> [--output PATH]

    product_id  Any of:
                  7678746361950
                  gid://shopify/Product/7678746361950
                  https://09fe59-3.myshopify.com/admin/products/7678746361950
                  https://09fe59-3.myshopify.com/admin/products/7678746361950/variants

    --output    CSV output path (default: orders_<product_id>.csv)
"""

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

from benedict import benedict as bdict
from box import Box
from dotenv import load_dotenv
from shop_client import ShopifyClient, schema

load_dotenv()

STORE_ID = os.environ["SHOPIFY__STORE_ID"]
API_VERSION = os.environ.get("SHOPIFY__API_VERSION", "2026-07")
TOKEN = os.environ["SHOPIFY__TOKEN__ADMIN"]

PRIORITY_COLUMNS = [
    "id",
    "name",
    "email",
    "created_at",
    "cancelled_at",
    "cancel_reason",
    "display_financial_status",
    "display_fulfillment_status",
    "total_price_set.shop_money.amount",
    "total_price_set.shop_money.currency_code",
    "customer.id",
    "customer.email",
    "customer.first_name",
    "customer.last_name",
]


def flatten_dict(d: dict) -> dict[str, Any]:
    """Flatten a nested dict to dot-notation keys using benedict.

    benedict.flatten() expands nested dicts; any remaining list/dict leaf
    values (e.g. line_items nodes, tags arrays) are JSON-encoded for CSV.
    The keypath_separator is set to ``|`` so ``.`` is free for flattening.
    """
    flat: dict = bdict(d, keypath_separator="|").flatten(separator=".")
    return {
        k: (json.dumps(v, default=str) if isinstance(v, (list, dict)) else (v if v is not None else ""))
        for k, v in flat.items()
    }


def box_to_plain(val: Any) -> Any:
    """Recursively convert Box instances to plain dicts/lists."""
    if isinstance(val, Box):
        return {k: box_to_plain(v) for k, v in val.items()}
    if isinstance(val, list):
        return [box_to_plain(item) for item in val]
    return val


def order_to_row(order: Box) -> tuple[dict[str, Any], dict[str, str]]:
    """Convert an order Box to (flat_standard_fields, custom_attrs_dict).

    custom_attributes are extracted and pivoted separately so they can be
    assigned deduplicated, alphabetically-sorted columns in the output CSV.
    """
    raw: dict = box_to_plain(order)

    # Pivot order-level custom_attributes: [{key, value}, ...] → {key: value}
    custom_attrs: dict[str, str] = {}
    for attr in raw.pop("custom_attributes", []) or []:
        k = str(attr.get("key") or "")
        v = str(attr.get("value") or "")
        if k:
            custom_attrs[k] = v

    flat = flatten_dict(raw)
    return flat, custom_attrs


def fetch_orders(client: ShopifyClient, product_id: str) -> list[Box]:
    print(f"Fetching orders for product {product_id!r}...")
    orders = client.run(
        schema.orders.queries.by_product,
        product_id=product_id,
    )
    print(f"  Retrieved {len(orders)} orders")
    return orders


def export_to_csv(orders: list[Box], output_path: Path) -> None:
    # Pass 1: build all rows in memory, collect every CA key seen.
    all_rows: list[tuple[dict[str, Any], dict[str, str]]] = []
    all_ca_keys: set[str] = set()

    print(f"Flattening {len(orders)} orders...")
    for order in orders:
        flat, ca = order_to_row(order)
        all_rows.append((flat, ca))
        all_ca_keys.update(ca.keys())

    # Determine standard columns: priority first, then the rest sorted.
    all_std_keys: set[str] = set()
    for flat, _ in all_rows:
        all_std_keys.update(flat.keys())

    ordered_cols = [c for c in PRIORITY_COLUMNS if c in all_std_keys]
    remaining = sorted(all_std_keys - set(ordered_cols))
    ordered_cols.extend(remaining)

    # Custom-attribute columns: alphabetical by attribute key.
    ca_columns = [f"custom_attributes.{k}" for k in sorted(all_ca_keys)]
    all_columns = ordered_cols + ca_columns

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_columns, extrasaction="ignore")
        writer.writeheader()
        for flat, ca in all_rows:
            row: dict[str, Any] = dict(flat)
            for k in sorted(all_ca_keys):
                row[f"custom_attributes.{k}"] = ca.get(k, "")
            writer.writerow(row)

    print(
        f"Wrote {len(all_rows)} rows × {len(all_columns)} columns "
        f"({len(ca_columns)} custom-attribute columns) → {output_path}"
    )


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        sys.exit("Usage: export_orders_by_product.py <product_id> [--output PATH]")

    product_id = args[0]

    # Derive a clean filename from the raw arg regardless of input format.
    numeric_id = product_id.rstrip("/").split("/")[-1]
    output_path = Path(f"orders_{numeric_id}.csv")
    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 >= len(args):
            sys.exit("--output requires a path argument")
        output_path = Path(args[idx + 1])

    client = ShopifyClient(store_id=STORE_ID, api_version=API_VERSION, token=TOKEN)
    orders = fetch_orders(client, product_id)

    if not orders:
        print("No orders found.")
        return

    export_to_csv(orders, output_path)


if __name__ == "__main__":
    main()
