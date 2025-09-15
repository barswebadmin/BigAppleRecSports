"""
Inventory tracking service - matching enableInventoryTracking from GAS
"""

import logging
from typing import Dict, Any, Optional
from services.shopify.shopify_service import ShopifyService

logger = logging.getLogger(__name__)


def enable_inventory_tracking(
    variant_gid: str, shopify_service: Optional[ShopifyService] = None
) -> Dict[str, Any]:
    """
    Enable inventory tracking for a variant using Shopify management
    Matches enableInventoryTracking from Create Product From Row.gs

    Args:
        variant_gid: The Shopify variant GID (e.g., "gid://shopify/ProductVariant/123")
        shopify_service: ShopifyService instance (optional, will create if not provided)

    Returns:
        Dict with success status and any error details
    """
    if not shopify_service:
        shopify_service = ShopifyService()

    logger.info(f"🔧 Enabling inventory tracking for variant {variant_gid}")

    try:
        # Build GraphQL mutation to enable inventory management
        # This is equivalent to the GAS REST API call setting inventory_management: "shopify"
        inventory_mutation = {
            "query": """
                mutation productVariantUpdate($input: ProductVariantInput!) {
                    productVariantUpdate(input: $input) {
                        productVariant {
                            id
                            inventoryManagement
                        }
                        userErrors {
                            field
                            message
                        }
                    }
                }
            """,
            "variables": {
                "input": {"id": variant_gid, "inventoryManagement": "SHOPIFY"}
            },
        }

        # Make the request
        response = shopify_service._make_shopify_request(inventory_mutation)

        if not response:
            logger.error("❌ No response from Shopify productVariantUpdate mutation")
            return {
                "success": False,
                "error": "No response from Shopify productVariantUpdate mutation",
            }

        logger.info(f"📝 Inventory tracking response: {response}")

        # Check for errors in the response
        variant_data = response.get("data", {}).get("productVariantUpdate", {})
        user_errors = variant_data.get("userErrors", [])

        if user_errors:
            error_messages = [
                f"{error.get('field', '')}: {error.get('message', '')}"
                for error in user_errors
            ]
            logger.error(f"❌ Enable inventory tracking errors: {user_errors}")
            return {
                "success": False,
                "error": f"Enable inventory tracking errors: {', '.join(error_messages)}",
                "userErrors": user_errors,
            }

        # Success
        updated_variant = variant_data.get("productVariant", {})
        inventory_management = updated_variant.get("inventoryManagement", "")

        logger.info(f"✅ Successfully enabled inventory tracking for {variant_gid}")
        logger.info(f"📦 Inventory management set to: {inventory_management}")

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
