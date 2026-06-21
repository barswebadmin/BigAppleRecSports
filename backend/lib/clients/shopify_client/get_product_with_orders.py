#!/usr/bin/env -S uv run --quiet --with pydantic --with pydantic-settings --with requests --with python-dotenv --with python-dateutil
# /// script
# dependencies = [
#     "pydantic>=2.0.0",
#     "pydantic-settings>=2.0.0",
#     "requests>=2.28.0",
#     "python-dotenv>=1.0.0",
#     "python-dateutil>=2.8.0",
# ]
# ///
"""
Get Shopify product with all orders and custom attributes.
Usage: ./get_product_with_orders.py [PRODUCT_ID_OR_URL]

Fetches a product with all attributes and all orders containing that product,
including order-level and line-item-level custom attributes.
Exports all orders to CSV with flattened column names in ~/Documents.

Arguments:
    PRODUCT_ID_OR_URL: Shopify product ID (e.g., 7587513565278) or product URL
                       If URL, extracts ID from the last path segment
                       If omitted, prompts for interactive input
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

def extract_product_id(input_str: str) -> str:
    """Extract product ID from URL or return ID as-is."""
    if "/" in input_str:
        return input_str.rstrip("/").split("/")[-1]
    return input_str

def _flatten(obj, prefix=""):
    """Recursively flatten a dict/list into dot-delimited keys."""
    items = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, (dict, list)):
                items.update(_flatten(v, full_key))
            else:
                items[full_key] = "" if v is None else v
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            full_key = f"{prefix}[{i}]"
            if isinstance(v, (dict, list)):
                items.update(_flatten(v, full_key))
            else:
                items[full_key] = "" if v is None else v
    return items


def extract_order_row(order: dict) -> dict:
    """Flatten an order response into a single row using raw API field paths.

    customAttributes are keyed by their attribute name rather than array index
    so that columns are consistent across orders.
    """
    row = {}
    line_items = order.get("lineItems", {}).get("nodes", [])

    for k, v in order.items():
        if k == "lineItems":
            continue
        if k == "customAttributes":
            for attr in (v or []):
                key = attr.get("key", "")
                if key:
                    row[f"customAttributes.{key}"] = attr.get("value", "")
            continue
        if isinstance(v, (dict, list)):
            for fk, fv in _flatten(v, k).items():
                row[fk] = fv
        else:
            row[k] = "" if v is None else v

    if line_items:
        first = line_items[0]
        for k, v in first.items():
            if k == "customAttributes":
                continue
            col = f"lineItems.{k}"
            if isinstance(v, (dict, list)):
                for fk, fv in _flatten(v, col).items():
                    row[fk] = fv
            else:
                row[col] = "" if v is None else v

    for li in line_items:
        for attr in li.get("customAttributes", []):
            key = attr.get("key", "")
            if key:
                col = f"lineItems.customAttributes.{key}"
                if col not in row:
                    row[col] = attr.get("value", "")

    return row

def main():
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

        from dotenv import load_dotenv
        from dateutil.relativedelta import relativedelta
        from shared_utilities.clients.shopify_client import ShopifyClient

        load_dotenv()

        if len(sys.argv) > 1:
            product_id = extract_product_id(sys.argv[1])
        else:
            user_input = input("Enter Shopify product ID or URL: ").strip()
            if not user_input:
                print("❌ Product ID/URL is required", file=sys.stderr)
                sys.exit(1)
            product_id = extract_product_id(user_input)

        client = ShopifyClient()

        product_data, errors = client.get_product(product_id)

        if errors:
            print(f"❌ Error getting product: {errors}", file=sys.stderr)
            sys.exit(1)

        if not product_data:
            print(f"❌ Product {product_id} not found", file=sys.stderr)
            sys.exit(1)

        print(f"🔍 Fetching all orders for product {product_id}...", file=sys.stderr)

        all_orders = []
        cursor = None
        page_num = 1

        while True:
            page_orders, next_cursor = client.get_orders_by_product(
                product_id=product_id,
                first=100,
                after=cursor,
                created_at_min=None,
                created_at_max=None
            )

            all_orders.extend(page_orders)
            print(f"  Page {page_num}: {len(page_orders)} orders (total: {len(all_orders)})", file=sys.stderr)

            if not next_cursor:
                break
            cursor = next_cursor
            page_num += 1

        print(f"✅ Found {len(all_orders)} total orders", file=sys.stderr)

        if all_orders:
            output_dir = Path.home() / "Documents"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"shopify_orders_for_{product_id}.csv"

            rows = [extract_order_row(order) for order in all_orders]

            all_columns = set()
            for row in rows:
                all_columns.update(row.keys())

            custom_attr_cols = sorted(
                c for c in all_columns
                if c.startswith("lineItems.customAttributes.")
                or c.startswith("customAttributes.")
            )
            other_cols = sorted(c for c in all_columns if c not in custom_attr_cols)
            columns = other_cols + custom_attr_cols

            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)

            print(f"{output_file}")
        else:
            print(f"⚠️ No orders found for product {product_id}", file=sys.stderr)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
