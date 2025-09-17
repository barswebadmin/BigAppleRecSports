"""
Webhooks Orchestrator

Main entry point that coordinates webhook processing across different
services and integrations.

TODO: should we delete this??? i don't see why it's needed
"""

import os
from typing import Dict, Any
from .security import SignatureVerifier
from .handlers import shopify_handler
from .integrations import GASClient


class WebhooksOrchestrator:
    """Main orchestrator for webhook processing"""
    
    def __init__(self):
        # Initialize configuration
        webhook_secret = os.getenv("SHOPIFY_WEBHOOK_SECRET")
        gas_url = os.getenv("GAS_WAITLIST_FORM_WEB_APP_URL")
        
        # Initialize components
        self.signature_verifier = SignatureVerifier(webhook_secret)
        self.gas_client = GASClient(gas_url)
    
    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Verify webhook signature for security"""
        return self.signature_verifier.verify(body, signature)
    
    def handle_shopify_webhook(self, headers: Dict[str, str], body: bytes) -> Dict[str, Any]:
        """Handle Shopify webhook processing"""
        return shopify_handler.handle_shopify_webhook(headers, body, self.gas_client)
    
    def handle_shopify_order_create_webhook(self, body: bytes) -> Dict[str, Any]:
        """Handle Shopify order create webhook"""
        from .handlers.order_create_handler import evaluate_order_create_webhook
        return evaluate_order_create_webhook(body)
    
    def handle_shopify_product_update_webhook(self, body: bytes) -> Dict[str, Any]:
        """Handle Shopify product update webhook"""
        from .handlers.product_update_handler import evaluate_product_update_webhook
        return evaluate_product_update_webhook(body, self.gas_client)
    
    def product_has_zero_inventory(self, product_data: Dict[str, Any]) -> bool:
        """Check if all variants have zero inventory"""
        from .parsers import has_zero_inventory
        return has_zero_inventory(product_data)
    
    def parse_shopify_webhook_for_waitlist_form(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Shopify webhook product data for waitlist form"""
        from .parsers import parse_for_waitlist_form
        return parse_for_waitlist_form(product_data)
    
    def send_to_waitlist_form_gas(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send product data to Google Apps Script waitlist form"""
        return self.gas_client.send_to_waitlist_form(product_data)
