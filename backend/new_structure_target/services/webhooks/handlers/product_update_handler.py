"""
Product Update Webhook Handler

Handles Shopify product update webhooks specifically, including inventory tracking
and waitlist form integration for sold-out products.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from new_structure_target.clients.shopify.builders.shopify_url_builders import build_product_url
from new_structure_target.services.webhooks.handlers.order_create_handler import slack_message_builder
from ..parsers.product_parser import has_zero_inventory, get_slack_group_mention
from config import config
from utils.date_utils import format_date_and_time, parse_shopify_datetime

logger = logging.getLogger(__name__)


def evaluate_product_update_webhook(body: bytes) -> Dict[str, Any]:
    """
    Handle Shopify product update webhook with enhanced logging and waitlist processing.
    
    Args:
        body: Raw webhook body containing product data
        gas_client: Client for Google Apps Script integration
        
    Returns:
        Dict containing success status, message, and detailed product information
    """
    try:
        webhook_data = json.loads(body.decode("utf-8"))

        evaluation_result = _generate_product_update_analysis(webhook_data)

        return evaluation_result

    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in webhook body: {e}")
        return {"success": False, "error": "Invalid JSON payload"}
    except Exception as e:
        logger.error(f"💥 Error processing product update webhook: {e}")
        return {"success": False, "error": str(e)}

def _generate_product_update_analysis(
    webhook_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate product analysis."""
    product_title = webhook_data.get("title") or webhook_data.get("product_title", "Unknown Product")
    product_id = webhook_data.get("id", "Unknown")
    product_data = {
        "product_id": product_id,
        "product_title": product_title,
    }
    reasons = []
    result = {
        "product_data": product_data,
        "action_needed": False,
        "reasons": reasons
    }
    
    early_reason = _check_early_exit_conditions(webhook_data)
    if early_reason:
        reasons.append(early_reason)
        return result

    
    
    product_url = build_product_url(product_id)
    result["product_data"]["product_url"] = product_url
    product_has_zero_inventory = has_zero_inventory(webhook_data)
    if not product_has_zero_inventory:
        reasons.append("product_not_sold_out")
        return result
    
    reasons.append("product_sold_out")
    result["action_needed"] = True
    result["product_data"]["sold_out_at"] = format_date_and_time(webhook_data.get("updated_at", ""))
    
    product_tags = webhook_data.get("tags")
    result["product_data"]["tags"] = product_tags


    return result


def _check_early_exit_conditions(webhook_data: Dict[str, Any]) -> Optional[str]:
    """
    Check if product update should skip inventory processing.
    
    Returns:
        String reason for early exit if any condition is met, None otherwise
    """
    # Check if product is already marked as waitlist-only via tags
    tags_value = webhook_data.get("tags")
    tags_list: List[str] = []
    if isinstance(tags_value, list):
        tags_list = [str(t).strip().lower() for t in tags_value]
    elif isinstance(tags_value, str):
        # Shopify often sends tags as a comma-separated string
        tags_list = [t.strip().lower() for t in tags_value.split(",") if t.strip()]
    if "waitlist-only" in tags_list:
        try:
            # Log the raw webhook payload to validate waitlist-only state
            logger.info(f"🧾 Raw product webhook payload (waitlist-only detected): {json.dumps(webhook_data)[:4000]}")
        except Exception:
            logger.info("🧾 Raw product payload available but could not be serialized for logging")
        return "already_waitlisted"

    # Check if status is draft
    status = webhook_data.get("status", "").lower()
    if status == "draft":
        return "product status is draft"
    
    # Check if published_at is null
    published_at = webhook_data.get("published_at")
    if published_at is None:
        return "product is not published (published_at is null)"
    
    # Check if published_at is less than 24 hours ago
    try:
        if published_at:
            published_datetime = parse_shopify_datetime(published_at)
            if not isinstance(published_datetime, datetime):
                raise ValueError("Could not parse published_at")

            now = datetime.now(timezone.utc)
            published_utc = published_datetime.astimezone(timezone.utc)
            hours_since_published = (now - published_utc).total_seconds() / 3600

            if hours_since_published < 24:
                return f"product was published recently ({hours_since_published:.1f} hours ago)"
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not parse published_at '{published_at}': {e}")
        # Don't early exit if we can't parse the date - let inventory check proceed
    
    return None


# def _log_product_update(
#     product_title: str, 
#     product_id: str, 
#     total_inventory: int, 
#     has_zero_inventory: bool
# ) -> None:
#     """Log detailed product update information"""
#     logger.info(f"📦 PRODUCT UPDATE: '{product_title}' (ID: {product_id})")
#     logger.info(f"📊 Total Inventory: {total_inventory} units")
#     logger.info(
#         f"🚨 Sold Out Status: {'✅ SOLD OUT' if has_zero_inventory else '❌ Still has inventory'}"
#     )