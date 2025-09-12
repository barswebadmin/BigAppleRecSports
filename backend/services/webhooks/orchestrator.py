"""
Webhooks Orchestrator

Main entry point that coordinates webhook processing across different
services and integrations.
"""

import os
from typing import Dict, Any
from .security import SignatureVerifier
from .handlers import ShopifyHandler
from .integrations import GASClient


class WebhooksOrchestrator:
    """Main orchestrator for webhook processing"""
    
    def __init__(self):
        # Initialize configuration
        webhook_secret = os.getenv("SHOPIFY_WEBHOOK_SECRET")
        gas_url = os.getenv("GAS_WAITLIST_FORM_WEB_APP_URL")
        shopify_store = os.getenv("SHOPIFY_STORE", "09fe59-3.myshopify.com")
        
        # Initialize components
        self.signature_verifier = SignatureVerifier(webhook_secret)
        self.gas_client = GASClient(gas_url)
        self.shopify_handler = ShopifyHandler(shopify_store, self.gas_client)
    
    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Verify webhook signature for security"""
        return self.signature_verifier.verify(body, signature)
    
    def handle_shopify_webhook(self, headers: Dict[str, str], body: bytes) -> Dict[str, Any]:
        """Handle Shopify webhook processing"""
        return self.shopify_handler.handle_webhook(headers, body)
    
    # Convenience methods for backward compatibility
    def is_product_update(self, headers: Dict[str, str]) -> bool:
        """Check if webhook is a product update"""
        return self.shopify_handler.is_product_update(headers)
    
    def handle_shopify_product_update_webhook(self, body: bytes) -> Dict[str, Any]:
        """Handle Shopify product update webhook"""
        return self.shopify_handler.handle_product_update_webhook(body)
    
    def product_has_zero_inventory(self, product_data: Dict[str, Any]) -> bool:
        """Check if all variants have zero inventory"""
        return self.shopify_handler.product_parser.has_zero_inventory(product_data)
    
    def parse_shopify_webhook_for_waitlist_form(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Shopify webhook product data for waitlist form"""
        return self.shopify_handler.product_parser.parse_for_waitlist_form(product_data)
    
    def send_to_waitlist_form_gas(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send product data to Google Apps Script waitlist form"""
        return self.gas_client.send_to_waitlist_form(product_data)
