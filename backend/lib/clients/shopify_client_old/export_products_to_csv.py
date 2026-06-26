#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "httpx",
#   "sgqlc",
# ]
# ///
"""
Export all Shopify products to CSVs using the Product model from shopify_schema_filtered.

Fetches ALL product fields, flattens nested structures with dot notation,
and exports to separate CSV files by sport category.

Usage: ./export_products_to_csv.py [--output-dir DIR]

Output:
  - kickball_products.csv
  - dodgeball_products.csv
  - bowling_products.csv
  - pickleball_products.csv
  - other_products.csv
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent / "shared_utilities" / "clients" / "shopify_client"))
from shopify_schema_filtered import Query

SHOPIFY_STORE = "09fe59-3.myshopify.com"
GRAPHQL_URL = f"https://{SHOPIFY_STORE}/admin/api/2025-01/graphql.json"
TOKEN_FILE = Path.home() / ".config" / "bars" / "bars_shopify_token_admin"

BATCH_SIZE = 50


def load_token() -> str:
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        sys.exit(f"❌ No token found at {TOKEN_FILE}")
    return token


def build_product_query() -> str:
    """Build a GraphQL query that fetches all Product scalar fields.
    
    Excludes connection/relation fields (collections, orders, etc.) to keep response manageable.
    Includes nested scalar fields with dot notation expansion.
    """
    query = Query()
    
    products_connection = query.products(first=BATCH_SIZE)
    products_connection.page_info.__fields__(
        has_next_page=True,
        end_cursor=True,
    )
    
    product = products_connection.edges.node
    
    product.__fields__(
        id=True,
        title=True,
        handle=True,
        description=True,
        description_html=True,
        description_plain_summary=True,
        body_html=True,
        vendor=True,
        product_type=True,
        tags=True,
        status=True,
        created_at=True,
        updated_at=True,
        published_at=True,
        online_store_url=True,
        total_inventory=True,
        total_variants=True,
        tracks_inventory=True,
        has_only_default_variant=True,
        has_out_of_stock_variants=True,
        is_gift_card=True,
        gift_card_template_suffix=True,
        template_suffix=True,
        storefront_id=True,
        requires_selling_plan=True,
        custom_product_type=True,
    )
    
    product.price_range_v2.min_variant_price.__fields__(amount=True, currency_code=True)
    product.price_range_v2.max_variant_price.__fields__(amount=True, currency_code=True)
    
    product.featured_image.__fields__(
        id=True,
        url=True,
        alt_text=True,
        width=True,
        height=True,
    )
    
    product.seo.__fields__(title=True, description=True)
    
    product.category.__fields__(
        id=True,
        full_name=True,
        name=True,
    )
    
    product.product_category.__fields__(
        product_taxonomy_node_id=True,
    )
    
    variants = product.variants(first=100)
    variants.edges.node.__fields__(
        id=True,
        title=True,
        sku=True,
        price=True,
        compare_at_price=True,
        position=True,
        available_for_sale=True,
        inventory_quantity=True,
        created_at=True,
        updated_at=True,
    )
    
    images = product.images(first=20)
    images.edges.node.__fields__(
        id=True,
        url=True,
        alt_text=True,
        width=True,
        height=True,
    )
    
    metafields = product.metafields(first=100)
    metafields.edges.node.__fields__(
        id=True,
        namespace=True,
        key=True,
        value=True,
        type=True,
        created_at=True,
        updated_at=True,
    )
    
    options = product.options(first=10)
    options.__fields__(
        id=True,
        name=True,
        position=True,
        values=True,
        option_values=True,
    )
    
    return str(query)


def flatten_dict(d: dict | list | Any, parent_key: str = "", sep: str = ".") -> dict:
    """Recursively flatten nested dict/list structures with dot notation.
    
    Arrays are converted to JSON strings.
    Terminal leaves become columns.
    """
    items = []
    
    if isinstance(d, dict):
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                if not v:
                    items.append((new_key, ""))
                elif all(isinstance(item, (str, int, float, bool, type(None))) for item in v):
                    items.append((new_key, json.dumps(v)))
                else:
                    items.append((new_key, json.dumps(v, default=str)))
            else:
                items.append((new_key, v if v is not None else ""))
    
    elif isinstance(d, list):
        if not d:
            items.append((parent_key, ""))
        elif all(isinstance(item, (str, int, float, bool, type(None))) for item in d):
            items.append((parent_key, json.dumps(d)))
        else:
            items.append((parent_key, json.dumps(d, default=str)))
    
    else:
        items.append((parent_key, d if d is not None else ""))
    
    return dict(items)


def fetch_all_products_paginated(token: str, query_template: str) -> list[dict]:
    """Fetch all products using cursor-based pagination."""
    
    all_products = []
    cursor = None
    page = 1
    
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token,
    }
    
    while True:
        if cursor:
            query = query_template.replace(
                "products(first: 50)",
                f'products(first: 50, after: "{cursor}")'
            )
        else:
            query = query_template
        
        print(f"📄 Fetching page {page} (batch size: {BATCH_SIZE})...")
        
        response = httpx.post(
            GRAPHQL_URL,
            json={"query": query},
            headers=headers,
            timeout=60.0,
        )
        response.raise_for_status()
        
        data = response.json()
        if "errors" in data:
            sys.exit(f"❌ GraphQL errors: {json.dumps(data['errors'], indent=2)}")
        
        products_data = data["data"]["products"]
        edges = products_data["edges"]
        
        for edge in edges:
            all_products.append(edge["node"])
        
        print(f"   ✅ Retrieved {len(edges)} products (total: {len(all_products)})")
        
        page_info = products_data["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        
        cursor = page_info["endCursor"]
        page += 1
    
    return all_products


def classify_product(title: str, tags: list[str]) -> str:
    """Determine sport category from title and tags."""
    title_lower = title.lower()
    tags_lower = [t.lower() for t in (tags or [])]
    
    if "kickball" in title_lower or "kickball" in tags_lower:
        return "kickball"
    elif "dodgeball" in title_lower or "dodgeball" in tags_lower:
        return "dodgeball"
    elif "bowling" in title_lower or "bowling" in tags_lower:
        return "bowling"
    elif "pickleball" in title_lower or "pickleball" in tags_lower:
        return "pickleball"
    else:
        return "other"


def export_to_csvs(products: list[dict], output_dir: Path):
    """Group products by sport and write to separate CSVs with dot notation columns."""
    
    grouped = {
        "kickball": [],
        "dodgeball": [],
        "bowling": [],
        "pickleball": [],
        "other": [],
    }
    
    print(f"\n📊 Flattening {len(products)} products...")
    for product in products:
        sport_category = classify_product(product.get("title", ""), product.get("tags", []))
        flattened = flatten_dict(product)
        grouped[sport_category].append(flattened)
    
    for sport, rows in grouped.items():
        if not rows:
            print(f"   ⚠️  No products for {sport}")
            continue
        
        all_columns = set()
        for row in rows:
            all_columns.update(row.keys())
        
        priority_columns = [
            "id", "handle", "title", "status", "tags",
            "createdAt", "updatedAt", "publishedAt",
        ]
        
        sorted_columns = [col for col in priority_columns if col in all_columns]
        remaining = sorted(all_columns - set(sorted_columns))
        sorted_columns.extend(remaining)
        
        csv_path = output_dir / f"{sport}_products.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sorted_columns, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"   ✅ Wrote {len(rows)} products to {csv_path.name} ({len(sorted_columns)} columns)")


def main():
    output_dir = Path("shopify_exports")
    
    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        if idx + 1 < len(sys.argv):
            output_dir = Path(sys.argv[idx + 1])
    
    output_dir.mkdir(exist_ok=True)
    
    token = load_token()
    
    print(f"🏪 Store: {SHOPIFY_STORE}")
    print(f"📁 Output directory: {output_dir.absolute()}")
    print()
    
    print("🔧 Building comprehensive Product query from schema...")
    query = build_product_query()
    print(f"   ✅ Query built ({len(query)} chars)")
    
    products = fetch_all_products_paginated(token, query)
    print(f"\n✅ Total products fetched: {len(products)}")
    
    print("\n📊 Exporting to CSVs by sport...")
    export_to_csvs(products, output_dir)
    
    print("\n" + "="*80)
    print("✅ Export complete!")
    print(f"📁 Files written to: {output_dir.absolute()}")


if __name__ == "__main__":
    main()
