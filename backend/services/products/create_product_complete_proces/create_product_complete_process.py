"""
Complete product creation process orchestrator - matching GAS flow expectations
"""

import logging
from typing import Dict, Any
from models.products.product_creation_request import ProductCreationRequest
from .create_product.create_product import create_product
from .create_variants.create_variants import create_variants
from .schedule_product_updates.schedule_product_updates import schedule_product_updates

logger = logging.getLogger(__name__)


def create_product_complete_process(
    validated_request: ProductCreationRequest,
) -> Dict[str, Any]:
    """
    Complete product creation process that orchestrates the same flow as GAS:
    1. Create Product (Create Product From Row.gs)
    2. Create Variants (Create Variants From Row.gs)
    3. Schedule Updates (scheduleInventoryMoves.gs + schedulePriceChanges.gs)

    Returns format expected by sendProductInfoToBackendForCreation:
    {
        "success": true,
        "data": {
            "productUrl": "https://admin.shopify.com/store/09fe59-3/products/123456",
            "variants": {
                "vet": "gid://shopify/ProductVariant/123",
                "early": "gid://shopify/ProductVariant/456",
                "open": "gid://shopify/ProductVariant/789",
                "waitlist": "gid://shopify/ProductVariant/012"
            }
        }
    }

    Args:
        validated_request: Validated ProductCreationRequest instance

    Returns:
        Dict with success status and data formatted for GAS compatibility
    """
    basic_details = validated_request.regularSeasonBasicDetails
    logger.info(
        f"🚀 Starting complete product creation process: {validated_request.sportName} - {basic_details.dayOfPlay} - {basic_details.division}"
    )

    try:
        # Step 1: Create the product (matching Create Product From Row.gs)
        logger.info("📦 Step 1: Creating product...")
        product_result = create_product(validated_request)
        logger.info(f"📦 Product creation result: {product_result}")

        if not product_result.get("success"):
            logger.error(f"❌ Product creation failed: {product_result.get('error')}")
            return {
                "success": False,
                "error": f"Product creation failed: {product_result.get('error')}",
                "message": f"Product creation failed: {product_result.get('error')}",
                "step_failed": "create_product",
                "details": product_result,
            }

        logger.info(
            f"✅ Product created: {product_result.get('data', {}).get('productUrl')}"
        )

        # Step 2: Create variants (matching Create Variants From Row.gs)
        logger.info("🎯 Step 2: Creating variants...")
        variants_result = create_variants(
            validated_request, product_result.get("data", {})
        )

        if not variants_result.get("success"):
            logger.error(f"❌ Variants creation failed: {variants_result.get('error')}")
            return {
                "success": False,
                "error": f"Variants creation failed: {variants_result.get('error')}",
                "message": f"Variants creation failed: {variants_result.get('error')}",
                "step_failed": "create_variants",
                "details": {
                    "product_result": product_result,
                    "variants_result": variants_result,
                },
            }

        logger.info(
            f"✅ Variants created: {variants_result.get('data', {}).get('total_variants')} variants"
        )

        # Step 3: Schedule product updates (matching scheduleInventoryMoves + schedulePriceChanges)
        logger.info("⏰ Step 3: Scheduling product updates...")
        scheduling_result = schedule_product_updates(
            validated_request, product_result.get("data", {}), variants_result
        )

        if not scheduling_result.get("success"):
            logger.error(
                f"❌ Product scheduling failed: {scheduling_result.get('error')}"
            )
            return {
                "success": False,
                "error": f"Product scheduling failed: {scheduling_result.get('error')}",
                "message": f"Product scheduling failed: {scheduling_result.get('error')}",
                "step_failed": "schedule_product_updates",
                "details": {
                    "product_result": product_result,
                    "variants_result": variants_result,
                    "scheduling_result": scheduling_result,
                },
            }

        logger.info(
            f"✅ Scheduling completed: {scheduling_result.get('data', {}).get('total_requests')} requests"
        )

        # Extract data for sendProductInfoToBackendForCreation response format
        product_data = product_result.get("data", {})
        variants_data = variants_result.get("data", {})
        scheduling_data = scheduling_result.get("data", {})

        # Build response in the exact format expected by sendProductInfoToBackendForCreation
        product_url = product_data.get("productUrl") or product_data.get("product_url")
        variant_mapping = variants_data.get("variant_mapping", {})

        # Success response matching the writeProductCreationResults_ function expectations
        complete_result = {
            "success": True,
            "message": "✅ Product and Variants created successfully!",
            "data": {
                # Primary data for writeProductCreationResults_
                "productUrl": product_url,
                "variants": variant_mapping,  # This matches the GAS expected format
                # Additional data for comprehensive response
                "product": {
                    "gid": product_data.get("product_gid"),
                    "id": product_data.get("product_id"),
                    "title": product_data.get("product_title"),
                    "url": product_url,
                },
                "variant_details": variants_data.get("variants", []),
                "scheduling": {
                    "requests": scheduling_data.get("requests", []),
                    "total_requests": scheduling_data.get("total_requests", 0),
                    "inventory_moves_scheduled": scheduling_data.get(
                        "inventory_moves_scheduled", False
                    ),
                    "price_changes_scheduled": scheduling_data.get(
                        "price_changes_scheduled", False
                    ),
                },
                "summary": {
                    "sport": validated_request.sportName,
                    "day": basic_details.dayOfPlay,
                    "division": basic_details.division,
                    "season": f"{basic_details.season.value} {basic_details.year}",
                    "total_variants": variants_data.get("total_variants", 0),
                    "registration_flow": scheduling_data.get("summary", {}).get(
                        "registration_flow", ""
                    ),
                    "total_inventory": scheduling_data.get("summary", {}).get(
                        "total_inventory", 0
                    ),
                },
            },
        }

        logger.info("🎉 Complete product creation process finished successfully!")
        logger.info(f"   Product URL: {product_url}")
        logger.info(f"   Variants: {list(variant_mapping.keys())}")
        logger.info(
            f"   Scheduled Requests: {scheduling_data.get('total_requests', 0)}"
        )

        return complete_result

    except Exception as e:
        logger.error(f"💥 Unexpected error in complete product creation process: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "message": f"Complete product creation process failed: {str(e)}",
            "step_failed": "unexpected_error",
            "exception": str(e),
        }
