"""
Inventory tracking service - matching enableInventoryTracking from GAS
"""

import logging
from typing import Dict, Any, Optional
from modules.integrations.shopify import ShopifyClient

logger = logging.getLogger(__name__)


def enable_inventory_tracking(
    variant_gid: str, shopify_orchestrator: Optional[ShopifyClient] = None
) -> Dict[str, Any]:
    """
    Enable inventory tracking for a variant using Shopify management
    Matches enableInventoryTracking from Create Product From Row.gs

    Args:
        variant_gid: The Shopify variant GID (e.g., "gid://shopify/ProductVariant/123")
        shopify_orchestrator: ShopifyClient instance (optional, will create if not provided)

    Returns:
        Dict with success status and any error details
    """
    if not shopify_orchestrator:
        shopify_orchestrator = ShopifyClient()

    try:
        # Use REST API to enable inventory management
        # This matches the GAS REST API call setting inventory_management: "shopify"
        variant_update_data = {"inventory_management": "shopify"}

        # Make the REST API request
        response = shopify_orchestrator.update_variant_rest(variant_gid, variant_update_data)

        if not response:
            logger.error("❌ No response from Shopify variant update REST API")
            return {
                "success": False,
                "error": "No response from Shopify variant update REST API",
            }

        # Check for errors in the response
        if not response.get("success", False):
            error_message = response.get("message", "Unknown error")
            logger.error(f"❌ Enable inventory tracking failed: {error_message}")
            return {
                "success": False,
                "error": f"Enable inventory tracking failed: {error_message}",
            }

        # Success
        updated_variant = response.get("variant", {})
        inventory_management = updated_variant.get("inventory_management", "")

        return {
            "success": True,
            "data": {
                "variantId": updated_variant.get("id"),
                "inventoryManagement": inventory_management,
            },
        }

    except Exception as e:
        logger.error(f"❌ Error in enable_inventory_tracking: {str(e)}")
        return {
            "success": False,
            "error": f"Error enabling inventory tracking: {str(e)}",
        }
