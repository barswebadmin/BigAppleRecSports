"""
Shopify Webhook Handler

Functional handlers for Shopify webhook processing.
"""

import logging
from typing import Dict, Any
from .product_update_handler import evaluate_product_update_webhook
from .order_create_handler import evaluate_order_create_webhook
from ..integrations import GASClient
from ...slack.slack_service import SlackService
from ...slack.slack_config import SlackConfig

logger = logging.getLogger(__name__)


def handle_shopify_webhook(headers: Dict[str, str], body: bytes, gas_client: GASClient) -> Dict[str, Any]:
    """
    Main handler for Shopify webhooks
    
    Args:
        headers: HTTP headers from the webhook request
        body: Raw body content from the webhook
        gas_client: GAS client for waitlist form integration
        
    Returns:
        Dict containing processing results
    """
    slack_service = SlackService()
    
    if headers.get("x-shopify-topic") == "orders/create":
        result = evaluate_order_create_webhook(body)
        if result.get("action_needed"):
            slack_service.send_message(
                channel='joe-test',
                message_text="Order requires attention",
                blocks=result.get("slack_blocks"),
                bot='registrations'
            )
        return result
    elif headers.get("x-shopify-topic") == "products/update":
        result = evaluate_product_update_webhook(body, gas_client)
        
        # Handle actions needed for product updates
        if result.get("action_needed"):
            # Send Slack notification (non-blocking)
            try:
                slack_service.send_message(
                    channel='joe-test',
                    message_text="Product requires attention",
                    blocks=result.get("slack_blocks"),
                    bot='registrations'
                )
                logger.info("✅ Slack notification sent for product update")
            except Exception as e:
                logger.error(f"❌ Failed to send Slack notification: {e}")
            
            # Handle GAS waitlist integration if product is sold out (non-blocking)
            if "product_sold_out" in result.get("reason", []):
                try:
                    from ..parsers.product_parser import parse_for_waitlist_form
                    import json
                    
                    # Parse the original product data
                    product_data = json.loads(body.decode("utf-8"))
                    parsed_product = parse_for_waitlist_form(product_data)
                    
                    logger.info(f"📤 Sending to GAS waitlist form: {parsed_product}")
                    gas_result = gas_client.send_to_waitlist_form(parsed_product)
                    
                    if gas_result.get("success"):
                        product_title = result.get("data", {}).get("product_title", "Unknown")
                        logger.info(f"✅ Successfully added '{product_title}' to waitlist form")
                    else:
                        logger.error(f"❌ Failed to add product to waitlist form: {gas_result}")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to process GAS waitlist integration: {e}")
        else:
            logger.info(f"No action needed for product update: {result.get('reason')}")
        return result
    else:
        return {"success": True, "message": "Not a product update webhook"}


def send_to_joetest(message: str) -> Dict[str, Any]:
    """
    Send a message to JoeTest channel using Registrations bot
    
    Args:
        message: The message text to send
        
    Returns:
        Dict containing success status and response details
    """
    try:
        # Get registrations bot token using clean API
        token = SlackConfig.Token.RegistrationsBot()
        if not token:
            logger.error("SLACK_REGISTRATIONS_BOT_TOKEN not found in environment")
            return {"success": False, "error": "Missing registrations bot token"}
        
        # Create slack service and send message
        slack_service = SlackService()
        result = slack_service.send_message(
            channel='joe-test',
            message_text=message,
            bot='registrations'
        )
        
        logger.info(f"✅ Message sent to JoeTest: {message[:50]}...")
        return {"success": True, "slack_response": result}
        
    except Exception as e:
        logger.error(f"❌ Failed to send message to JoeTest: {e}")
        return {"success": False, "error": str(e)}
