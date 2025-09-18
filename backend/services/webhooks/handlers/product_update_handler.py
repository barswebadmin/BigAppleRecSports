"""
Product Update Webhook Handler

Handles Shopify product update webhooks specifically, including inventory tracking
and waitlist form integration for sold-out products.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from ..parsers import has_zero_inventory, parse_for_waitlist_form
from ..integrations import GASClient
from config import config
from utils.date_utils import format_date_and_time

logger = logging.getLogger(__name__)


def evaluate_product_update_webhook(body: bytes, gas_client: GASClient) -> Dict[str, Any]:
    """
    Handle Shopify product update webhook with enhanced logging and waitlist processing.
    
    Args:
        body: Raw webhook body containing product data
        gas_client: Client for Google Apps Script integration
        
    Returns:
        Dict containing success status, message, and detailed product information
    """
    try:
        product_data = json.loads(body.decode("utf-8"))

        # Extract product information for logging
        product_id = product_data.get("id", "unknown")
        product_title = product_data.get("title", "Unknown Product")
        product_handle = product_data.get("handle", "")

        # Generate product URLs
        shopify_admin_url = f"{config.shopify_admin_url}/products/{product_id}"
        shopify_store_url = f"https://{config.shopify_store}/products/{product_handle}" if product_handle else ""

        # Early exit checks - skip inventory processing if any of these conditions are true
        early_exit_reason = _check_early_exit_conditions(product_data)
        if early_exit_reason:
            logger.info(f"🚫 Skipping inventory checks for product {product_id}: {early_exit_reason}")
            
            # Build data for early exit
            data = {
                "product_id": product_id,
                "sold_out_at": product_data.get("created_at", ""),
                "product_title": product_title
            }
            
            # Generate analysis with Slack blocks
            result = _generate_analysis(product_data, False, early_exit_reason, data)
            
            # Return result structure
            return result

        # Check inventory status
        has_zero_inventory_result = has_zero_inventory(product_data)
        total_inventory = _calculate_total_inventory(product_data)

        # Log product update details first
        _log_product_update(
            product_title, product_id, shopify_admin_url, 
            shopify_store_url, total_inventory, has_zero_inventory_result
        )

        # Handle products that still have inventory
        if not has_zero_inventory_result:
            data = {
                "product_id": product_id,
                "sold_out_at": None,
                "product_title": product_title
            }
            
            # Generate analysis with Slack blocks
            result = _generate_analysis(product_data, False, "product_not_sold_out", data)
            
            # Return result structure
            return result

        # Handle sold-out products - this needs action
        data = {
            "product_id": product_id,
            "sold_out_at": product_data.get("created_at", ""),
            "product_title": product_title
        }
        
        # Generate analysis with Slack blocks  
        result = _generate_analysis(product_data, True, "product_sold_out", data)
        
        # Return result structure
        return result

    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in webhook body: {e}")
        return {"success": False, "error": "Invalid JSON payload"}
    except Exception as e:
        logger.error(f"💥 Error processing product update webhook: {e}")
        return {"success": False, "error": str(e)}

def _check_early_exit_conditions(product_data: Dict[str, Any]) -> Optional[str]:
    """
    Check if product update should skip inventory processing.
    
    Returns:
        String reason for early exit if any condition is met, None otherwise
    """
    # Check if product is already marked as waitlist-only via tags
    tags_value = product_data.get("tags")
    tags_list: List[str] = []
    if isinstance(tags_value, list):
        tags_list = [str(t).strip().lower() for t in tags_value]
    elif isinstance(tags_value, str):
        # Shopify often sends tags as a comma-separated string
        tags_list = [t.strip().lower() for t in tags_value.split(",") if t.strip()]
    if "waitlist-only" in tags_list:
        try:
            # Log the raw webhook payload to validate waitlist-only state
            logger.info(f"🧾 Raw product webhook payload (waitlist-only detected): {json.dumps(product_data)[:4000]}")
        except Exception:
            logger.info("🧾 Raw product payload available but could not be serialized for logging")
        return "already_waitlisted"

    # Check if status is draft
    status = product_data.get("status", "").lower()
    if status == "draft":
        return "product status is draft"
    
    # Check if published_at is null
    published_at = product_data.get("published_at")
    if published_at is None:
        return "product is not published (published_at is null)"
    
    # Check if published_at is less than 24 hours ago
    try:
        if published_at:
            # Parse the published_at timestamp (Shopify format: "2025-09-16T23:59:29-04:00")
            # Handle both Z suffix and timezone offsets
            if published_at.endswith('Z'):
                published_datetime = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            else:
                published_datetime = datetime.fromisoformat(published_at)
            
            # Get current time in UTC
            now = datetime.now(timezone.utc)
            
            # Convert published_datetime to UTC for comparison
            if published_datetime.tzinfo is None:
                # Assume UTC if no timezone info
                published_datetime = published_datetime.replace(tzinfo=timezone.utc)
            else:
                # Convert to UTC
                published_datetime = published_datetime.astimezone(timezone.utc)
            
            time_since_published = now - published_datetime
            hours_since_published = time_since_published.total_seconds() / 3600
            
            if hours_since_published < 24:
                return f"product was published recently ({hours_since_published:.1f} hours ago)"
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not parse published_at '{published_at}': {e}")
        # Don't early exit if we can't parse the date - let inventory check proceed
    
    return None


def _calculate_total_inventory(product_data: Dict[str, Any]) -> int:
    """Calculate total inventory across all product variants"""
    variants = product_data.get("variants", [])
    return sum(variant.get("inventory_quantity", 0) for variant in variants)


def _generate_analysis(
    product_data: Dict[str, Any],
    action_needed: bool,
    reason: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate Slack message blocks for product analysis."""
    product_title = data.get("product_title", "Unknown Product")
    product_id = data.get("product_id", "Unknown")
    
    # Header section - special format for sold out products
    if reason == "product_sold_out":
        header_text = f":rotating_light: {product_title} has sold out!"
    else:
        header_text = f"📦 Product Update: {product_title}"
    
    # Status and reason mapping
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
        }
    }
    
    config_data = status_config.get(reason, {
        "emoji": "❓",
        "status": "Unknown Status", 
        "description": "Unknown product status",
        "color": "#808080"  # Gray
    })
    
    # Create Slack blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text", 
                "text": header_text
            }
        },
        {
            "type": "section", 
            "text": {
                "type": "mrkdwn",
                "text": f"*Product:* {product_title}\n*Analysis:*\n{config_data['description']}" if reason == "product_sold_out" else f"{config_data['emoji']} *{config_data['status']}*\n\n*Product:* {product_title}\n*ID:* {product_id}\n\n*Analysis:*\n{config_data['description']}"
            }
        }
    ]
    
    # Add product details section
    product_details = []
    if data.get("sold_out_at"):
        formatted_date = format_date_and_time(data['sold_out_at'])
        product_details.append(f"*Sold Out At:* {formatted_date}")
    
    # Add admin URL if available
    shopify_admin_url = f"{config.shopify_admin_url}/products/{product_id}"
    product_details.append(f"*Shopify Product URL:* <{shopify_admin_url}|View in Shopify>")
    product_details.append(f"Please add the product to the waitlist form options (automation is coming soon): <{'https://docs.google.com/forms/d/14ID7mSW747aO1CtIEWzamXreeIBimBsVgmQ6ZqCMadw/edit#responsesc'}|View in Google Forms>")
    product_details.append(f"*Waitlist Responses:* <{'https://docs.google.com/spreadsheets/d/1rrmEu6QKNnDoNJs2XnAD08W-7smUhFPKYnNC5y7iNI0?resourcekey=&usp=forms_web_b&urp=linked#gid=1214906876'}|View in Google Sheets>")
    
    if product_details:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(product_details)
            }
        })
    
    return {
        "action_needed": action_needed,
        "reason": reason,
        "data": data,
        "slack_blocks": blocks
    }


def _log_product_update(
    product_title: str, 
    product_id: str, 
    admin_url: str,
    store_url: str, 
    total_inventory: int, 
    has_zero_inventory: bool
) -> None:
    """Log detailed product update information"""
    logger.info(f"📦 PRODUCT UPDATE: '{product_title}' (ID: {product_id})")
    logger.info(f"🔗 Admin URL: {admin_url}")
    if store_url:
        logger.info(f"🛍️ Store URL: {store_url}")
    logger.info(f"📊 Total Inventory: {total_inventory} units")
    logger.info(
        f"🚨 Sold Out Status: {'✅ SOLD OUT' if has_zero_inventory else '❌ Still has inventory'}"
    )


def _handle_product_with_inventory(
    product_title: str,
    product_id: str,
    admin_url: str,
    store_url: str,
    total_inventory: int
) -> Dict[str, Any]:
    """Handle products that still have inventory available"""
    logger.info(
        f"⏭️ Product still has {total_inventory} units in stock - no waitlist action needed"
    )
    return {
        "success": True,
        "message": f"Product '{product_title}' still has inventory ({total_inventory} units)",
        "product_info": {
            "id": product_id,
            "title": product_title,
            "admin_url": admin_url,
            "store_url": store_url,
            "total_inventory": total_inventory,
            "sold_out": False,
        },
    }


def _handle_sold_out_product(
    product_data: Dict[str, Any],
    product_title: str,
    product_id: str,
    admin_url: str,
    store_url: str,
    total_inventory: int,
    gas_client: GASClient
) -> Dict[str, Any]:
    """Handle sold-out products by processing them for the waitlist"""
    logger.info("🎯 Product is sold out - processing for waitlist form...")
    
    # Parse product data for waitlist form
    parsed_product = parse_for_waitlist_form(product_data)
    logger.info(f"📤 Sending to GAS waitlist form: {parsed_product}")
    
    # Send to waitlist form
    gas_result = gas_client.send_to_waitlist_form(parsed_product)
    
    # Log result
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
            "admin_url": admin_url,
            "store_url": store_url,
            "total_inventory": total_inventory,
            "sold_out": True,
        },
        "parsed_product": parsed_product,
        "waitlist_result": gas_result,
    }
