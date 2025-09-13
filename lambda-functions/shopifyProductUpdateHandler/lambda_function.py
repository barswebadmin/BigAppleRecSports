"""
Shopify Product Update Handler Lambda Function

Automatically updates product images to "sold out" versions when all relevant variants
are out of stock. Uses sport detection to apply appropriate sold-out images.

📚 Documentation: See README.md#lambda-functions for overview
🚀 Development: See README_EXT/CONTRIBUTING.md#lambda-development for local setup
🚀 Deployment: See README_EXT/DEPLOYMENT.md#lambda-functions-deployment for deployment

Author: BARS
Version: 1.0.1
Last Updated: 2025-01-13
"""

__version__ = "1.0.0"

import json
from typing import Dict, Any

# Import shared utilities (would use lambda layer in production)
try:
    from bars_common_utils.event_utils import parse_event_body
    from bars_common_utils.response_utils import format_response, format_error
except ImportError:
    # Fallback for local development without layer
    print("⚠️ Lambda layer not available, using local utilities")

# Import local modules
from sport_detection import (
    detect_sport,
    get_sold_out_image_url,
    is_all_closed,
    get_supported_sports,
)
from shopify_image_updater import ShopifyImageUpdater
# from version import get_version_info


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Shopify product image updates

    Args:
        event: Lambda event containing Shopify webhook data
        context: Lambda context object

    Returns:
        HTTP response dictionary
    """
    print(f"📦 Shopify Product Update Handler v{__version__} invoked")
    print("📥 Event received:", json.dumps(event, indent=2))

    try:
        # Parse event body with standardized utility
        body = parse_event_body(event)

        # Extract required fields from Shopify webhook
        product_id = body.get("id")
        product_gid = body.get("admin_graphql_api_id")
        product_title = body.get("title", "")
        product_tags = body.get("tags", "")
        product_image = body.get("image", {}).get("src")
        variants = body.get("variants", [])

        # Validate required data
        if not product_id or not product_gid or not variants:
            return format_error(
                400,
                "Missing required product data",
                {
                    "missing": [
                        f
                        for f in ["id", "admin_graphql_api_id", "variants"]
                        if not body.get(f)
                    ]
                },
            )

        print(f"📦 Processing product: {product_title} (ID: {product_id})")
        print(f"🔢 Found {len(variants)} variants")

        # Check if all relevant variants are sold out
        if is_all_closed(variants):
            print("🚫 All relevant variants are sold out")

            # Detect sport from title and tags
            sport = detect_sport(product_title, product_tags)
            print(f"🏷️ Detected sport: {sport}")

            if sport:
                # Get the appropriate sold-out image URL
                sold_out_url = get_sold_out_image_url(sport)
                if sold_out_url:
                    # Update the product image
                    image_updater = ShopifyImageUpdater()
                    success = image_updater.update_product_image(
                        product_id=str(product_id),
                        product_gid=product_gid,
                        image_url=sold_out_url,
                        sport=sport,
                        original_image=product_image,
                    )

                    if success:
                        return format_response(
                            200,
                            {
                                "success": True,
                                "message": f"✅ Updated {sport} product image to sold-out version",
                                "product_id": product_id,
                                "sport": sport,
                                "image_url": sold_out_url,
                            },
                        )
                    else:
                        return format_error(500, "Failed to update product image")
                else:
                    return format_error(
                        500, f"No sold-out image configured for sport: {sport}"
                    )
            else:
                supported_sports = get_supported_sports()
                return format_response(
                    200,
                    {
                        "success": True,
                        "message": "ℹ️ Unrecognized sport - no action taken",
                        "product_title": product_title,
                        "product_tags": product_tags,
                        "supported_sports": supported_sports,
                    },
                )
        else:
            return format_response(
                200,
                {
                    "success": True,
                    "message": "ℹ️ Product still has inventory - no action needed",
                    "product_id": product_id,
                },
            )

    except Exception as e:
        print(f"❌ Exception in lambda_handler: {str(e)}")
        return format_error(500, "Internal server error", str(e))


# For backwards compatibility and fallback when layer is not available
def parse_event_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback event parsing if layer not available"""
    if isinstance(event, dict) and "body" in event:
        return (
            json.loads(event["body"])
            if isinstance(event["body"], str)
            else event["body"]
        )
    return event
