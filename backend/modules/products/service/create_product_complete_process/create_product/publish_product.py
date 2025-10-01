"""
Product publication service - matching scheduleProductPublication from GAS
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from modules.integrations.shopify.client import ShopifyClient

logger = logging.getLogger(__name__)


# def publish_product_at_time(
#     product_gid: str,
#     publish_date: Optional[datetime] = None,
#     shopify_orchestrator: Optional[ShopifyOrchestrator] = None,
# ) -> Dict[str, Any]:
#     """
#     Publish a product to the online store at a specific time
#     Matches scheduleProductPublication from Create Product From Row.gs

#     Args:
#         product_gid: The Shopify product GID (e.g., "gid://shopify/Product/123")
#         publish_date: When to publish the product (defaults to now)
#         shopify_orchestrator: ShopifyOrchestrator instance (optional, will create if not provided)

#     Returns:
#         Dict with success status and any error details
#     """
#     if not shopify_orchestrator:
#         shopify_orchestrator = ShopifyOrchestrator()

#     # Default to now if no publish date provided
#     if not publish_date:
#         publish_date = datetime.now()

#     # Format the publish date to ISO format (matching GAS logic)
#     formatted_publish_date = publish_date.isoformat()

#     logger.info(f"📅 Publishing product {product_gid} at {formatted_publish_date}")

#     try:
#         # Build GraphQL mutation (exact match to GAS)
#         publish_mutation = {
#             "query": """
#                 mutation productPublish($input: ProductPublishInput!) {
#                     productPublish(input: $input) {
#                         product {
#                             id
#                         }
#                         userErrors {
#                             field
#                             message
#                         }
#                     }
#                 }
#             """,
#             "variables": {
#                 "input": {
#                     "id": product_gid,
#                     "productPublications": [
#                         {
#                             "publicationId": "gid://shopify/Publication/79253667934",
#                             "publishDate": formatted_publish_date,
#                             "channelHandle": "online-store",
#                         }
#                     ],
#                 }
#             },
#         }

#         # Make the request
#         response = shopify_orchestrator._make_shopify_request(publish_mutation)

#         if not response:
#             logger.error("❌ No response from Shopify productPublish mutation")
#             return {
#                 "success": False,
#                 "error": "No response from Shopify productPublish mutation",
#             }

#         logger.info(f"📝 Product publish response: {response}")

#         # Check for errors in the response
#         publish_data = response.get("data", {}).get("productPublish", {})
#         user_errors = publish_data.get("userErrors", [])

#         if user_errors:
#             error_messages = [
#                 f"{error.get('field', '')}: {error.get('message', '')}"
#                 for error in user_errors
#             ]
#             logger.error(f"❌ productPublish errors: {user_errors}")
#             return {
#                 "success": False,
#                 "error": f"productPublish errors: {', '.join(error_messages)}",
#                 "userErrors": user_errors,
#             }

#         # Success
#         published_product = publish_data.get("product", {})
#         logger.info(f"✅ Successfully scheduled product publication for {product_gid}")

#         return {
#             "success": True,
#             "data": {
#                 "productId": published_product.get("id"),
#                 "publishDate": formatted_publish_date,
#                 "publicationId": "gid://shopify/Publication/79253667934",
#             },
#         }

#     except Exception as e:
#         logger.error(f"❌ Error in publish_product_at_time: {str(e)}")
#         return {
#             "success": False,
#             "error": f"Error scheduling product publication: {str(e)}",
#         }


# def publish_product_now(
#     product_gid: str, shopify_orchestrator: Optional[ShopifyOrchestrator] = None
# ) -> Dict[str, Any]:
#     """
#     Convenience method to publish a product immediately

#     Args:
#         product_gid: The Shopify product GID
#         shopify_orchestrator: ShopifyOrchestrator instance (optional)

#     Returns:
#         Dict with success status and any error details
#     """
#     return publish_product_at_time(product_gid, datetime.now(), shopify_orchestrator)
