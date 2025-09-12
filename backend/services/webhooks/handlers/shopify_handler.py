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
        """Handle Shopify product update webhook"""
        try:
            product_data = json.loads(body.decode('utf-8'))
            
            if not self.product_parser.has_zero_inventory(product_data):
                return {"success": True, "message": "Product still has inventory"}
            
            parsed_product = self.product_parser.parse_for_waitlist_form(product_data)
            gas_result = self.gas_client.send_to_waitlist_form(parsed_product)
            
            return {
                "success": True,
                "message": "Product sold out, waitlist form updated",
                "parsed_product": parsed_product,
                "waitlist_result": gas_result
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook body: {e}")
            return {"success": False, "error": "Invalid JSON payload"}
        except Exception as e:
            logger.error(f"Error processing product update webhook: {e}")
            return {"success": False, "error": str(e)}
