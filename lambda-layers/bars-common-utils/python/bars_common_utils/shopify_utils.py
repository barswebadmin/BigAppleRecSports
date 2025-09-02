"""Shopify API utilities for BARS Lambda functions."""
import json
import os
import urllib.request
from datetime import datetime
from typing import Dict, Optional

SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "your_shopify_token")
SHOPIFY_API_URL = "https://09fe59-3.myshopify.com/admin/api/2025-04/graphql.json"

# GraphQL Queries
GET_INVENTORY_ITEM_AND_QUANTITY = """
query GetInventoryItemId($variantId: ID!) {
  productVariant(id: $variantId) {
    id
    inventoryItem {
      id
    }
    inventoryQuantity
  }
}
"""

GET_PRODUCT_VARIANTS = """
query getVariants($id: ID!) {
  product(id: $id) {
    variants(first: 100) {
      nodes {
        id
        title
        inventoryItem { id }
        inventoryQuantity
      }
    }
  }
}
"""

ADJUST_INVENTORY = """
mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
  inventoryAdjustQuantities(input: $input) {
    userErrors {
      field
      message
    }
    inventoryAdjustmentGroup {
      createdAt
      reason
      referenceDocumentUri
      changes {
        name
        delta
      }
    }
  }
}
"""

UPDATE_PRODUCT_TITLE = """
mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      title
    }
    userErrors {
      field
      message
    }
  }
}
"""

def fetch_shopify(query: str, variables: Optional[Dict] = None) -> Dict:
    """Make a request to Shopify's GraphQL API."""
    payload = json.dumps({
        "query": query,
        "variables": variables or {}
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN
    }

    req = urllib.request.Request(SHOPIFY_API_URL, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as response:
            response_text = response.read().decode()
            print("📬 Raw Shopify Response:", response_text)
            response_json = json.loads(response_text)

        if "errors" in response_json:
            print("❌ Shopify GraphQL Errors:", json.dumps(response_json["errors"], indent=2))
            raise Exception(f"GraphQL error: {response_json['errors']}")
            
        return response_json.get("data")

    except Exception as e:
        print("❌ fetch_shopify failed:", str(e))
        raise

def get_inventory_item_and_quantity(variant_gid: str) -> Dict[str, int]:
    """Return inventory item ID and available quantity for a given variant GID."""
    data = fetch_shopify(GET_INVENTORY_ITEM_AND_QUANTITY, {'variantId': variant_gid})

    try:
        variant = data['productVariant']
        return {
            'inventoryItemId': variant['inventoryItem']['id'],
            'inventoryQuantity': variant['inventoryQuantity']
        }
    except (KeyError, TypeError) as e:
        print(f"❌ Error parsing inventory item/quantity: {data}")
        raise ValueError(f"Could not get inventory info for variant {variant_gid}") from e

def adjust_inventory(inventory_item_id: str, delta: int) -> Dict:
    """Adjust inventory using inventoryAdjustQuantities."""
    location_id = os.environ.get("SHOPIFY_LOCATION_ID")
    if not location_id:
        raise ValueError("SHOPIFY_LOCATION_ID env variable is required")

    reference_uri = f"logistics://moveinventorylambda/{datetime.utcnow().isoformat()}"

    variables = {
        "input": {
            "reason": "correction",
            "name": "available",
            "referenceDocumentUri": reference_uri,
            "changes": [
                {
                    "delta": delta,
                    "inventoryItemId": inventory_item_id,
                    "locationId": location_id
                }
            ]
        }
    }

    data = fetch_shopify(ADJUST_INVENTORY, variables)

    user_errors = data.get("inventoryAdjustQuantities", {}).get("userErrors", [])
    if user_errors:
        raise ValueError("Inventory adjustment failed: " + '; '.join(
            f"{e['field']}: {e['message']}" for e in user_errors
        ))

    return data

def get_product_variants(product_id: str) -> Dict:
    """Get all variants for a product."""
    product_gid = f"gid://shopify/Product/{product_id}"
    return fetch_shopify(GET_PRODUCT_VARIANTS, {"id": product_gid})

def update_product_title(product_id: str, new_title: str) -> Dict:
    """Update a product's title."""
    product_gid = f"gid://shopify/Product/{product_id}"
    
    variables = {
        "input": {
            "id": product_gid,
            "title": new_title
        }
    }
    
    data = fetch_shopify(UPDATE_PRODUCT_TITLE, variables)
    
    user_errors = data.get("productUpdate", {}).get("userErrors", [])
    if user_errors:
        raise ValueError("Product update failed: " + '; '.join(
            f"{e['field']}: {e['message']}" for e in user_errors
        ))
    
    return data 