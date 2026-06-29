#!/usr/bin/env -S uv run --project scripts
"""
Export all Shopify orders for a given product to a CSV.

Fetches every order that contains the product, flattens nested fields with dot
notation, and pivots order-level and line-item-level custom_attributes into
their own columns. Custom-attribute column names are the union of every key
seen across all orders (and all line items), sorted alphabetically.

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


def _pivot_custom_attributes(attrs: list | None) -> dict[str, str]:
    """Convert ``[{key, value}, ...]`` to ``{key: value}``."""
    out: dict[str, str] = {}
    for attr in attrs or []:
        if not isinstance(attr, dict):
            continue
        k = str(attr.get("key") or "")
        v = str(attr.get("value") or "")
        if k:
            out[k] = v
    return out


def _line_item_nodes(line_items: Any) -> list[dict[str, Any]]:
    if isinstance(line_items, Box):
        line_items = box_to_plain(line_items)
    if isinstance(line_items, dict):
        nodes = line_items.get("nodes") or []
    elif isinstance(line_items, list):
        nodes = line_items
    else:
        return []
    return [n if isinstance(n, dict) else box_to_plain(n) for n in nodes]


def order_to_row(order: Box) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    """Convert an order Box to (flat_fields, order_custom_attrs, line_item_custom_attrs).

    Order-level and line-item-level custom_attributes are pivoted separately.
    Line-item attribute keys are merged across every node on the order (first
    non-empty value wins when the same key appears on multiple line items).
    """
    raw: dict = box_to_plain(order)

    order_custom_attrs = _pivot_custom_attributes(raw.pop("custom_attributes", None))

    line_item_custom_attrs: dict[str, str] = {}
    line_items_flat: dict[str, Any] = {}
    nodes = _line_item_nodes(raw.pop("line_items", None))
    for i, node in enumerate(nodes):
        node_ca = _pivot_custom_attributes(node.pop("custom_attributes", None))
        for k, v in node_ca.items():
            if k not in line_item_custom_attrs:
                line_item_custom_attrs[k] = v
        if i == 0:
            prefixed = {f"line_items.{k}": v for k, v in node.items()}
            line_items_flat = flatten_dict(prefixed)

    flat = flatten_dict(raw)
    flat.update(line_items_flat)
    return flat, order_custom_attrs, line_item_custom_attrs


def fetch_orders(client: ShopifyClient, product_id: str) -> list[Box]:
    print(f"Fetching orders for product {product_id!r}...")
    orders = client.run(
        schema.orders.queries.by_product,
        product_id=product_id,
    )
    print(f"  Retrieved {len(orders)} orders")
    return orders


def export_to_csv(orders: list[Box], output_path: Path) -> None:
    # Pass 1: build all rows in memory; collect every custom-attribute key seen.
    all_rows: list[tuple[dict[str, Any], dict[str, str], dict[str, str]]] = []
    all_order_ca_keys: set[str] = set()
    all_line_item_ca_keys: set[str] = set()

    print(f"Flattening {len(orders)} orders...")
    for order in orders:
        flat, order_ca, line_item_ca = order_to_row(order)
        all_rows.append((flat, order_ca, line_item_ca))
        all_order_ca_keys.update(order_ca.keys())
        all_line_item_ca_keys.update(line_item_ca.keys())

    # Determine standard columns: priority first, then the rest sorted.
    all_std_keys: set[str] = set()
    for flat, _, _ in all_rows:
        all_std_keys.update(flat.keys())

    ordered_cols = [c for c in PRIORITY_COLUMNS if c in all_std_keys]
    remaining = sorted(all_std_keys - set(ordered_cols))
    ordered_cols.extend(remaining)

    order_ca_columns = [f"custom_attributes.{k}" for k in sorted(all_order_ca_keys)]
    line_item_ca_columns = [
        f"line_items.custom_attributes.{k}" for k in sorted(all_line_item_ca_keys)
    ]
    all_columns = ordered_cols + order_ca_columns + line_item_ca_columns

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_columns, extrasaction="ignore")
        writer.writeheader()
        for flat, order_ca, line_item_ca in all_rows:
            row: dict[str, Any] = dict(flat)
            for k in sorted(all_order_ca_keys):
                row[f"custom_attributes.{k}"] = order_ca.get(k, "")
            for k in sorted(all_line_item_ca_keys):
                row[f"line_items.custom_attributes.{k}"] = line_item_ca.get(k, "")
            writer.writerow(row)

    print(
        f"Wrote {len(all_rows)} rows × {len(all_columns)} columns "
        f"({len(order_ca_columns)} order + {len(line_item_ca_columns)} line-item "
        f"custom-attribute columns) → {output_path}"
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
