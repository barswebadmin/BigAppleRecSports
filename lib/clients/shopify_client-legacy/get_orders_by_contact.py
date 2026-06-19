#!/usr/bin/env -S uv run --quiet --with pydantic --with pydantic-settings --with requests --with python-dotenv
# /// script
# dependencies = [
#     "pydantic>=2.0.0",
#     "pydantic-settings>=2.0.0",
#     "requests>=2.28.0",
#     "python-dotenv>=1.0.0",
# ]
# ///
"""
Get Shopify orders filtered by customer email or last name.

Usage:
    ./get_orders_by_contact.py email
    ./get_orders_by_contact.py last_name

Opens a temporary editor window for you to enter one value per line.
Queries Shopify for each value individually to find ALL matching orders,
then exports CSV to ~/Documents/shopify_orders_for_provided_{email|last_name}.csv
"""

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

from get_product_with_orders import extract_order_row


def open_editor_for_input(label: str) -> list[str]:
    """Open a temp file in cursor editor, return non-empty non-comment lines."""
    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".txt", delete=False
    ) as tmp:
        tmp.write(f"# Enter one {label} per line\n")
        tmp.write("# Lines starting with # are ignored\n")
        tmp.write("# Save and close editor to continue\n\n")
        tmp_path = Path(tmp.name)

    try:
        subprocess.run(["cursor", "-w", str(tmp_path)], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Editor closed without saving or cursor not found", file=sys.stderr)
        sys.exit(1)

    with open(tmp_path, encoding="utf-8") as f:
        lines = [
            line.strip() for line in f
            if line.strip() and not line.startswith("#")
        ]

    tmp_path.unlink(missing_ok=True)
    return lines


def fetch_orders_by_query(client, query_str: str) -> list[dict]:
    """Fetch all orders matching a Shopify search query, paginating fully."""
    import requests as req_lib

    from shared_utilities.clients.shopify_client.gql import GqlQuery, GqlResult

    class _SearchOrders(GqlQuery):
        query = """
query searchOrders($query: String!, $first: Int!, $after: String) {
  orders(first: $first, after: $after, query: $query,
         sortKey: CREATED_AT, reverse: true) {
    nodes {
      id name legacyResourceId createdAt updatedAt cancelledAt
      displayFinancialStatus displayFulfillmentStatus
      totalPriceSet { shopMoney { amount currencyCode } }
      currentTotalPriceSet { shopMoney { amount currencyCode } }
      customAttributes { key value }
      customer { id email firstName lastName }
      lineItems(first: 50) {
        nodes {
          id name title quantity
          customAttributes { key value }
          variant { id title sku }
          product { id handle title }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""
        data_key = "orders"
        errors_key = None
        result_key = None

        def build_query(self, *, query: str, first: int = 100,  # pyright: ignore[reportIncompatibleMethodOverride]
                        after: str | None = None) -> tuple[str, dict]:
            variables: dict = {"query": query, "first": first}
            if after:
                variables["after"] = after
            return self.query, variables

        def parse_response(self, response: req_lib.Response) -> GqlResult:
            data, errors = super().parse_response(response)
            if errors:
                return None, errors
            return data, None

    orders = []
    cursor = None
    while True:
        data, errors = client.send_request(
            _SearchOrders, query=query_str, first=100, after=cursor
        )
        if errors:
            print(f"  ⚠️ API error: {errors}", file=sys.stderr)
            break
        batch = data.get("nodes", [])
        orders.extend(batch)
        page_info = data.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    return orders


def export_csv(orders: list[dict], filename: str) -> Path:
    """Export orders to CSV using the same flattening as get_product_with_orders."""
    rows = [extract_order_row(order) for order in orders]

    all_columns: set[str] = set()
    for row in rows:
        all_columns.update(row.keys())

    custom_attr_cols = sorted(
        c for c in all_columns
        if c.startswith("lineItems.customAttributes.")
        or c.startswith("customAttributes.")
    )
    other_cols = sorted(c for c in all_columns if c not in custom_attr_cols)
    columns = other_cols + custom_attr_cols

    output_dir = Path.home() / "Documents"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / filename

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return output_file


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("email", "last_name"):
        print(
            "Usage: ./get_orders_by_contact.py <email|last_name>",
            file=sys.stderr,
        )
        sys.exit(1)

    mode = sys.argv[1]

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from dotenv import load_dotenv
        from shared_utilities.clients.shopify_client import ShopifyClient

        load_dotenv()
        client = ShopifyClient()

        values = open_editor_for_input(mode.replace("_", " "))
        if not values:
            print("❌ No values provided", file=sys.stderr)
            sys.exit(1)

        print(f"📋 {len(values)} {mode}(s) provided", file=sys.stderr)

        seen_ids: set[str] = set()
        all_matched: list[dict] = []

        for i, val in enumerate(values, 1):
            if mode == "email":
                q = f"email:{val}"
            else:
                q = f"name:{val}"

            print(
                f"  [{i}/{len(values)}] Searching: {val}",
                file=sys.stderr,
            )
            orders = fetch_orders_by_query(client, q)

            for order in orders:
                oid = order.get("id", "")
                if oid not in seen_ids:
                    seen_ids.add(oid)
                    all_matched.append(order)

            print(
                f"    → {len(orders)} orders found",
                file=sys.stderr,
            )

        print(
            f"🎯 {len(all_matched)} total unique orders matched",
            file=sys.stderr,
        )

        if all_matched:
            output = export_csv(
                all_matched,
                f"shopify_orders_for_provided_{mode}.csv",
            )
            print(f"{output}")
        else:
            print("⚠️ No matching orders found", file=sys.stderr)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
