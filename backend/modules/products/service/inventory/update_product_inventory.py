from typing import Dict, Any, Optional
from config import config
from ...models import FetchProductRequest
from ..fetch_product_from_shopify import fetch_product_from_shopify

def update_product_inventory(request_details: FetchProductRequest) -> Dict[str, Any]:
    """
    Update product inventory
    """

    product = fetch_product_from_shopify(request_details).get("data", {}).get("product", {})

    return {"success": "false", "message": "Not implemented"}

def adjust_inventory(
    self, inventory_item_id: str, delta: int, location_id: Optional[str] = None
) -> Dict[str, Any]:
    """Adjust inventory using inventoryAdjustQuantities mutation"""
    try:
        # Use default location if not provided
        if not location_id:
            location_id = getattr(config, "shopify_location_id", None)
            if not location_id:
                raise ValueError(
                    "SHOPIFY_LOCATION_ID is required for inventory adjustments"
                )

            # Ensure location_id is in proper global ID format
            if not location_id.startswith("gid://shopify/Location/"):
                location_id = f"gid://shopify/Location/{location_id}"

        from datetime import datetime

        reference_uri = (
            f"logistics://slackrefundworkflow/{datetime.utcnow().isoformat()}"
        )

        query = build_adjust_inventory_mutation(
            inventory_item_id=inventory_item_id,
            delta=delta,
            location_id=location_id,
            reference_uri=reference_uri,
        )

        data = self.shopify_client.send_request(query).raw

        # Enhanced debugging for Shopify response
        logger.info(
            f"🔍 Shopify inventory adjustment response: {json.dumps(data, indent=2) if data else 'None'}"
        )

        if not data:
            raise ValueError("No response received from Shopify")

        if "errors" in data:
            error_msg = json.dumps(data["errors"], indent=2)
            raise ValueError(f"Shopify GraphQL errors: {error_msg}")

        if not data.get("data"):
            raise ValueError(
                f"Invalid response structure from Shopify: {json.dumps(data, indent=2)}"
            )

        user_errors = (
            data["data"].get("inventoryAdjustQuantities", {}).get("userErrors", [])
        )
        if user_errors:
            error_messages = [f"{e['field']}: {e['message']}" for e in user_errors]
            raise ValueError(
                "Inventory adjustment failed: " + "; ".join(error_messages)
            )

        return {
            "success": True,
            "message": f"Successfully adjusted inventory by {delta}",
            "data": data["data"]["inventoryAdjustQuantities"],
        }

    except Exception as e:
        logger.error(f"Error adjusting inventory for {inventory_item_id}: {str(e)}")
        return {"success": False, "message": str(e)}
