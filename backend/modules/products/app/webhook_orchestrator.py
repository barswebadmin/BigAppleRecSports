"""
Webhooks Orchestrator

Main entry point that coordinates webhook processing across different
services and integrations.

TODO: should we delete this??? i don't see why it's needed
"""

import os
from typing import Dict, Any
from new_structure_target.services.webhooks.parsers.product_parser import get_slack_group_mention, parse_for_waitlist_form
from new_structure_target.clients.shopify.core.shopify_security import ShopifySecurity
from new_structure_target.clients.slack.core.slack_client import SlackClient
from new_structure_target.clients.google_apps_script.gas_client import GASClient
from .handlers.order_create_handler import evaluate_order_create_webhook, slack_message_builder
from .handlers.product_update_handler import evaluate_product_update_webhook
from config import config


class WebhooksOrchestrator:
    """Main orchestrator for webhook processing"""
    
    def __init__(self):
        # Initialize configuration
        gas_url = os.getenv("GAS_WAITLIST_FORM_WEB_APP_URL")
        
        # Initialize components (ShopifySecurity resolves secret from ENV internally)
        self.signature_verifier = ShopifySecurity()
        self.slack_client = SlackClient()
        self.gas_client = GASClient(gas_url)
        self.slack_channel = config.SlackChannel
        self.slack_bot = config.SlackBot
        self.slack_group = config.SlackGroup
    
    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Verify webhook signature for security"""
        return self.signature_verifier.verify_shopify_webhook(body, signature)
    
    def handle_shopify_order_create_webhook(self, body: bytes) -> Dict[str, Any]:
        """Handle Shopify order create webhook"""

        evaluation_result = evaluate_order_create_webhook(body)
        product_data = evaluation_result["product_data"]
        reasons = ", ".join(evaluation_result["reasons"])

        product_tags = product_data.get("tags")
        slack_group_mention = get_slack_group_mention(product_tags)
        group_info = self.slack_group.get(slack_group_mention) if slack_group_mention else None
        
        return {
                "result": "success",
                "reasons": reasons,
                "product_data": product_data
            }
    
    def handle_shopify_product_update_webhook(self, body: bytes) -> Dict[str, Any]:
        """Handle Shopify product update webhook"""
        evaluation_result = evaluate_product_update_webhook(body)
        reasons = ", ".join(evaluation_result["reasons"])
        action_needed = evaluation_result["action_needed"]
        product_data = evaluation_result["product_data"]


        status_config = {
            "registration_not_yet_open": {
                "emoji": "⏳",
                "status": "Registration Not Open",
                "description": "Product published recently or is in draft status",
                "color": "#FFA500"  # Orange
            },
            "already_waitlisted": {
                "emoji": "🔒",
                "status": "Already Waitlisted",
                "description": "Product is already marked as waitlist-only; skipping processing",
                "color": "#808080"  # Gray
            },
            "product_not_sold_out": {
                "emoji": "✅", 
                "status": "Inventory Available",
                "description": "Product still has inventory available",
                "color": "#36a64f"  # Green
            },
            "product_sold_out": {
                "emoji": "🚨",
                "status": "Sold Out",
                "description": "Product is detected to be sold out",
                "color": "#FF0000"  # Red
            },
            "unknown": {
                "emoji": "❓",
                "status": "Unknown Status", 
                "description": "Unknown product status",
                "color": "#808080"  # Gray
            }
        }

        if not action_needed:
            return {
                "result": "success",
                "reasons": reasons,
                "product_data": product_data
            }


        # Header section - special format for sold out products

        product_title = product_data["product_title"]
        product_id = product_data["product_id"]
        product_url = product_data["product_url"]
        sold_out_at = product_data["sold_out_at"]
        # parsed_title = parse_for_waitlist_form(product_title)
        slack_group_mention = product_data.get("slack_group_mention")
        config_data = status_config[reasons] if reasons in status_config else status_config["unknown"]
        
        header_text = f"{config_data['emoji']} Attention: {product_title}"
        header_block = slack_message_builder.build_header_block(header_text)

        section_text_1 = f"*Reason(s):* {config_data['description']}\n\n*Sold Out At:* {sold_out_at}" if reasons == "product_sold_out" else f"{config_data['emoji']} *{config_data['status']}*\n\n*Product:* {product_title}\n*ID:* {product_id}\n\n*Analysis:*\n{config_data['description']}\n\n*Sold Out At:* {sold_out_at}"
        section_block_1 = slack_message_builder.build_section_block(section_text_1)

        section_text_2 = f"*View Product in Shopify:* {slack_message_builder.build_hyperlink(product_url, product_title)}"
        section_block_2 = slack_message_builder.build_section_block(section_text_2)

        section_text_3 = f"*Waitlist Responses:* {slack_message_builder.build_hyperlink('https://docs.google.com/spreadsheets/d/1rrmEu6QKNnDoNJs2XnAD08W-7smUhFPKYnNC5y7iNI0?resourcekey=&usp=forms_web_b&urp=linked#gid=1214906876', 'View in Google Sheets')}"
        section_block_3 = slack_message_builder.build_section_block(section_text_3)

        product_tags = product_data.get("tags")
        slack_group_mention = get_slack_group_mention(product_tags)
        group_info = self.slack_group.get(slack_group_mention) if slack_group_mention else None
        
        mention_target = group_info.get('id') if isinstance(group_info, dict) else "@here"
        mention_text = f"*Attn*: {mention_target}"
        mention_block = slack_message_builder.build_section_block(mention_text)

        blocks = [
            header_block,
            section_block_1,
            section_block_2,
            section_block_3,
            mention_block,
        ]

        self.slack_client.send_message(
            channel=self.slack_channel.JoeTest,
            bot=self.slack_bot.Registrations,
            blocks=blocks,
        )


        return {
            "result": "success",
            "reasons": reasons,
            "product_data": product_data
        }
    
    def parse_shopify_webhook_for_waitlist_form(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Shopify webhook product data for waitlist form"""
        from .parsers import parse_for_waitlist_form
        return parse_for_waitlist_form(product_data)
    
    def send_to_waitlist_form_gas(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send product data to Google Apps Script waitlist form"""
        return self.gas_client.send_to_waitlist_form(product_data)
