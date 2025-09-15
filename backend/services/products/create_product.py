"""
Product creation service
"""

import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def create_product(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a product from validated product data

    Args:
        product_data: Validated product data dictionary

    Returns:
        Dict with success status and any relevant data
    """
    # Extract basic details for logging
    basic_details = product_data.get("regularSeasonBasicDetails", {})
    logger.info(
        f"Creating product: {product_data.get('sportName')} - {basic_details.get('dayOfPlay')} - {basic_details.get('division')}"
    )

    try:
        # For now, just return success
        # In the future, this would:
        # 1. Create the product in Shopify
        # 2. Create variants
        # 3. Set up inventory
        # 4. Configure registration windows
        # 5. Set up any automated processes

        result = {
            "success": True,
            "message": "Product created successfully",
            "product_id": f"temp_{datetime.now().timestamp()}",  # Temporary ID
            "data": {
                "sport": product_data.get("sportName"),
                "day": basic_details.get("dayOfPlay"),
                "division": basic_details.get("division"),
                "season": f"{basic_details.get('season')} {basic_details.get('year')}",
                "location": basic_details.get("location"),
                "price": product_data.get("inventoryInfo", {}).get("price"),
                "inventory": product_data.get("inventoryInfo", {}).get(
                    "totalInventory"
                ),
            },
        }

        logger.info(f"Product created successfully with ID: {result['product_id']}")
        return result

    except Exception as e:
        logger.error(f"Error creating product: {e}")
        return {
            "success": False,
            "message": f"Product creation failed: {str(e)}",
            "error": str(e),
        }
