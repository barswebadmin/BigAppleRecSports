"""Shopify API utilities for BARS Lambda functions."""
import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Optional

# Token source: SSM Parameter Store only (no env fallback in production)
_CACHED_SHOPIFY_TOKEN: Optional[str] = None
SHOPIFY_API_URL = "https://09fe59-3.myshopify.com/admin/api/2025-04/graphql.json"

def _get_shopify_access_token(token_type: str) -> str:
    """Resolve Shopify token from env or SSM Parameter Store (with decryption).

    Caches on first successful fetch per execution environment to avoid repeated SSM calls.
    """
    global _CACHED_SHOPIFY_TOKEN

    print(f"🔐 _get_shopify_access_token called with type: {token_type}")

    if _CACHED_SHOPIFY_TOKEN:
        print(f"✅ Using cached token (length: {len(_CACHED_SHOPIFY_TOKEN)})")
        return _CACHED_SHOPIFY_TOKEN

    match token_type:
        case "admin":
            name = f"/shopify/token.{token_type}"
        case _:
            raise ValueError(f"Invalid token type: {token_type}")

    print(f"🔍 Attempting to fetch token from SSM parameter: {name}")

    try:
        # Lazy import to avoid hard dependency during unit tests without boto3 installed
        print("📦 Importing boto3...")
        import boto3  # type: ignore
        from botocore.exceptions import BotoCoreError, ClientError  # type: ignore
        print("✅ boto3 imported successfully")
        
        print("🔧 Creating SSM client...")
        ssm = boto3.client("ssm", region_name="us-east-1")
        print("✅ SSM client created")
        
        print(f"📡 Calling SSM get_parameter with Name='{name}', WithDecryption=True")
        resp = ssm.get_parameter(Name=name, WithDecryption=True)
        print(f"✅ SSM parameter retrieved successfully")
        print(f"   Parameter Name: {resp['Parameter']['Name']}")
        print(f"   Parameter Type: {resp['Parameter']['Type']}")
        print(f"   Parameter ARN: {resp['Parameter'].get('ARN', 'N/A')}")
        
        token = resp["Parameter"]["Value"]
        print(f"✅ Token retrieved (length: {len(token)}, starts with: {token[:10]}...)")
        
        _CACHED_SHOPIFY_TOKEN = token
        return token
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"❌ AWS ClientError fetching token from SSM:")
        print(f"   Error Code: {error_code}")
        print(f"   Error Message: {error_msg}")
        print(f"   Parameter Name: {name}")
        print(f"   Full Error Response: {e.response}")
        
        print(f"📋 Falling back to environment variable SHOPIFY_ACCESS_TOKEN")
        token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
        if token:
            print(f"✅ Token found in env (length: {len(token)}, starts with: {token[:10]}...)")
            return token
        else:
            print(f"❌ No token found in env variable SHOPIFY_ACCESS_TOKEN")
            raise ValueError(f"No Shopify token found in SSM ({name}) due to {error_code}: {error_msg}. No fallback env var available.")
    except Exception as e:
        print(f"❌ Unexpected error fetching token from SSM:")
        print(f"   Exception Type: {type(e).__name__}")
        print(f"   Exception Message: {str(e)}")
        print(f"   Parameter Name: {name}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        
        print(f"📋 Falling back to environment variable SHOPIFY_ACCESS_TOKEN")
        token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
        if token:
            print(f"✅ Token found in env (length: {len(token)}, starts with: {token[:10]}...)")
            return token
        else:
            print(f"❌ No token found in env variable SHOPIFY_ACCESS_TOKEN")
            raise ValueError(f"No Shopify token found in SSM ({name}) or environment variable (SHOPIFY_ACCESS_TOKEN)")
    # except (NameError, ModuleNotFoundError) as e:
    #     # boto3 not available in unit test environment
    #     raise RuntimeError("boto3 is required at runtime to fetch Shopify token from SSM") from e
    # except (Exception,) as e:
    #     # Provide actionable logs; fall back to raising a clear error
    #     print(f"❌ Failed to load Shopify token from SSM parameter '{name}': {e}")
    #     raise

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
    print(f"🌐 fetch_shopify called")
    print(f"   API URL: {SHOPIFY_API_URL}")
    print(f"   Variables: {variables}")
    
    payload = json.dumps({
        "query": query,
        "variables": variables or {}
    }).encode("utf-8")

    token = _get_shopify_access_token(token_type="admin")
    print(f"🔑 Using token for Shopify request (length: {len(token)}, starts with: {token[:10]}...)")

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token
    }

    req = urllib.request.Request(SHOPIFY_API_URL, data=payload, headers=headers, method="POST")

    try:
        print(f"📤 Sending request to Shopify...")
        with urllib.request.urlopen(req) as response:
            response_text = response.read().decode()
            print("📬 Raw Shopify Response:", response_text[:500])  # Truncate to first 500 chars
            response_json = json.loads(response_text)

        if "errors" in response_json:
            print("❌ Shopify GraphQL Errors:", json.dumps(response_json["errors"], indent=2))
            raise Exception(f"GraphQL error: {response_json['errors']}")
        
        print("✅ Shopify request successful")
        return response_json.get("data")

    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if hasattr(e, 'read') else 'No error body'
        print(f"❌ HTTP Error {e.code}: {e.reason}")
        print(f"   Error body: {error_body}")
        print(f"   Token used (first 10 chars): {token[:10]}...")
        print(f"   API URL: {SHOPIFY_API_URL}")
        if e.code == 401:
            raise ValueError(f"Shopify authentication failed (401 Unauthorized). Token may be invalid, expired, or not have required permissions. Token starts with: {token[:10]}...")
        raise
    except Exception as e:
        print(f"❌ fetch_shopify failed: {type(e).__name__}: {str(e)}")
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