__version__ = "1.1.0"

import json
import os
import traceback
import urllib.request
from typing import Dict

from bars_common_utils.response_utils import format_response, format_error
from bars_common_utils.event_utils import validate_required_fields
from bars_common_utils.request_utils import wait_until_next_minute

SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "your_shopify_token")
SHOPIFY_API_URL = "https://09fe59-3.myshopify.com/admin/api/2025-04/graphql.json"

# GraphQL queries
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

def fetch_shopify(query, variables=None):
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

def get_inventory_item_and_quantity(variant_gid: str) -> Dict[str, str]:
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
    """Adjust inventory using inventoryAdjustQuantities (Shopify Admin API 2025-07)."""
    location_id = os.environ.get("SHOPIFY_LOCATION_ID")
    if not location_id:
        raise ValueError("SHOPIFY_LOCATION_ID env variable is required")

    mutation = """
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

    data = fetch_shopify(mutation, variables)

    user_errors = data.get("inventoryAdjustQuantities", {}).get("userErrors", [])
    if user_errors:
        raise ValueError("Inventory adjustment failed: " + '; '.join(
            f"{e['field']}: {e['message']}" for e in user_errors
        ))

    return data

def lambda_handler(event, context):
    """
    Move inventory between variants based on the type of transfer.
    Supports:
      - Veteran ➡ Early (calculates deltaToMove)
      - Early/Vet ➡ Open (consolidates inventory)
    """
    try:
        print("📦 MoveInventoryLambda invoked with event:", json.dumps(event, indent=2))

        required_fields = ['scheduleName', 'productUrl', 'sourceVariant', 'destinationVariant']
        validate_required_fields(event, required_fields)

        source = event['sourceVariant']
        dest = event['destinationVariant']
        source_gid = source['gid']
        dest_gid = dest['gid']
        source_type = source.get('type', '').lower()
        dest_type = dest.get('type', '').lower()

        # 🧠 Case 1: Veteran ➡ Early logic
        if source_type == 'veteran' and dest_type == 'early':
            validate_required_fields(event, ['totalInventory', 'numEligibleVeterans'])

            total_inventory = event['totalInventory']
            num_vets = event['numEligibleVeterans']

            source_data = get_inventory_item_and_quantity(source_gid)
            dest_data = get_inventory_item_and_quantity(dest_gid)

            source_qty = source_data['inventoryQuantity']
            source_id = source_data['inventoryItemId']
            dest_id = dest_data['inventoryItemId']

            num_orders = total_inventory - source_qty
            remaining_non_vet_spots = source_qty - (num_vets - num_orders)
            delta_to_move = min(remaining_non_vet_spots, source_qty)

            print(f"📊 Calculated deltaToMove: {delta_to_move}")
            if delta_to_move <= 0:
                raise ValueError(f"Delta to move is not positive: {delta_to_move}")

            wait_until_next_minute()
            adjust_inventory(source_id, -delta_to_move)
            adjust_inventory(dest_id, delta_to_move)

            return format_response(200,{
                "success": True,
                "message": f"Moved {delta_to_move} units from veteran to early",
                "details": {
                    "from": source_gid,
                    "to": dest_gid,
                    "amountMoved": delta_to_move
                }
            })

        # 🧠 Case 2: Consolidate from veteran+early ➡ open
        if dest_type == 'open':
            product_id = event['productUrl'].split('/')[-1]
            product_gid = f"gid://shopify/Product/{product_id}"

            get_variants_query = """
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

            result = fetch_shopify(get_variants_query, {"id": product_gid})
            variants = result['product']['variants']['nodes']

            move_variants = []
            total_delta = 0

            for v in variants:
                title = v['title'].lower()
                if 'early' in title or 'veteran' in title:
                    qty = v['inventoryQuantity']
                    if qty != 0:
                        item_id = v['inventoryItem']['id']
                        print(f"🔁 Queuing {qty} from '{title}'")
                        move_variants.append((item_id, qty))
                        total_delta += qty

            if total_delta == 0:
                raise ValueError("No inventory found to move from early/veteran variants.")

            dest_data = get_inventory_item_and_quantity(dest_gid)
            dest_id = dest_data['inventoryItemId']

            wait_until_next_minute()
            for item_id, qty in move_variants:
                adjust_inventory(item_id, -qty)
            adjust_inventory(dest_id, total_delta)

            return format_response(200,{
                "success": True,
                "message": f"Moved {total_delta} units into open variant",
                "details": {
                    "from": "early+vet",
                    "to": dest_gid,
                    "amountMoved": total_delta
                }
            })

        # ❌ Catch-all for unhandled types
        raise ValueError(f"Unsupported source→destination move: {source_type} → {dest_type}")

    except Exception as e:
        print("❌ Exception occurred:", traceback.format_exc())
        return format_error(500, str(e))