"""
Shopify Webhook Handler

Handles specific Shopify webhook processing logic.
"""

import json
import logging
from typing import Dict, Any
from ..parsers import ProductParser
from ..integrations import GASClient

logger = logging.getLogger(__name__)


class ShopifyHandler:
    """Handles Shopify-specific webhook processing"""

    def __init__(self, shopify_store: str, gas_client: GASClient):
        self.product_parser = ProductParser(shopify_store)
        self.gas_client = gas_client

    def is_product_update(self, headers: Dict[str, str]) -> bool:
        """Check if webhook is a product update from headers"""
        topic = headers.get("x-shopify-topic", "")
        return topic == "products/update"

    def handle_webhook(self, headers: Dict[str, str], body: bytes) -> Dict[str, Any]:
        """Main handler for Shopify webhooks"""
        if not self.is_product_update(headers):
            return {"success": True, "message": "Not a product update webhook"}

        return self.handle_product_update_webhook(body)

    def handle_product_update_webhook(self, body: bytes) -> Dict[str, Any]:
        """Handle Shopify product update webhook with enhanced logging"""
        try:
            product_data = json.loads(body.decode("utf-8"))

            # Extract product information for logging
            product_id = product_data.get("id", "unknown")
            product_title = product_data.get("title", "Unknown Product")
            product_handle = product_data.get("handle", "")

            # Generate product URLs
            shopify_admin_url = f"https://admin.shopify.com/store/{self.product_parser.shopify_store.split('.')[0]}/products/{product_id}"
            shopify_store_url = (
                f"https://{self.product_parser.shopify_store}/products/{product_handle}"
                if product_handle
                else ""
            )

            # Check inventory status
            has_zero_inventory = self.product_parser.has_zero_inventory(product_data)

            # Calculate total inventory across all variants
            variants = product_data.get("variants", [])
            total_inventory = sum(
                variant.get("inventory_quantity", 0) for variant in variants
            )

            logger.info(f"📦 PRODUCT UPDATE: '{product_title}' (ID: {product_id})")
            logger.info(f"🔗 Admin URL: {shopify_admin_url}")
            if shopify_store_url:
                logger.info(f"🛍️ Store URL: {shopify_store_url}")
            logger.info(f"📊 Total Inventory: {total_inventory} units")
            logger.info(
                f"🚨 Sold Out Status: {'✅ SOLD OUT' if has_zero_inventory else '❌ Still has inventory'}"
            )

            if not has_zero_inventory:
                logger.info(
                    f"⏭️ Product still has {total_inventory} units in stock - no waitlist action needed"
                )
                return {
                    "success": True,
                    "message": f"Product '{product_title}' still has inventory ({total_inventory} units)",
                    "product_info": {
                        "id": product_id,
                        "title": product_title,
                        "admin_url": shopify_admin_url,
                        "store_url": shopify_store_url,
                        "total_inventory": total_inventory,
                        "sold_out": False,
                    },
                }

            logger.info("🎯 Product is sold out - processing for waitlist form...")
            parsed_product = self.product_parser.parse_for_waitlist_form(product_data)

            logger.info(f"📤 Sending to GAS waitlist form: {parsed_product}")
            gas_result = self.gas_client.send_to_waitlist_form(parsed_product)

            if gas_result.get("success"):
                logger.info(f"✅ Successfully added '{product_title}' to waitlist form")
            else:
                logger.error(
                    f"❌ Failed to add '{product_title}' to waitlist form: {gas_result}"
                )

            return {
                "success": True,
                "message": f"Product '{product_title}' sold out - waitlist form {'updated' if gas_result.get('success') else 'update failed'}",
                "product_info": {
                    "id": product_id,
                    "title": product_title,
                    "admin_url": shopify_admin_url,
                    "store_url": shopify_store_url,
                    "total_inventory": total_inventory,
                    "sold_out": True,
                },
                "parsed_product": parsed_product,
                "waitlist_result": gas_result,
            }

        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in webhook body: {e}")
            return {"success": False, "error": "Invalid JSON payload"}
        except Exception as e:
            logger.error(f"💥 Error processing product update webhook: {e}")
            return {"success": False, "error": str(e)}
