"""
Order Create Webhook Handler

Handles Shopify order create webhooks specifically, including email mismatch detection
and waitlist registration identification.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from config import config
from new_structure_target.clients.shopify.builders.shopify_url_builders import build_order_url
from new_structure_target.clients.slack.builders.message_builder import SlackMessageBuilder
from utils.date_utils import format_date_and_time

logger = logging.getLogger(__name__)

slack_message_builder = SlackMessageBuilder(sport_groups=config.SlackGroup.all())


def evaluate_order_create_webhook(body: bytes) -> Dict[str, Any]:
    """
    Handle Shopify order create webhook with email mismatch and waitlist detection.
    
    Args:
        body: Raw webhook body containing order data
        
    Returns:
        Dict containing success status, analysis results, and detailed order information
    """
    try:
        webhook_data = json.loads(body.decode("utf-8"))

        evaluation_result = _generate_order_create_analysis(webhook_data)

        evaluation_result["action_needed"] = "email_mismatch" in evaluation_result["reasons"] or "waitlist_registration" in evaluation_result["reasons"]

        return evaluation_result

    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in order webhook body: {e}")
        return {"success": False, "error": "Invalid JSON payload"}
    except Exception as e:
        logger.error(f"💥 Error processing order create webhook: {e}")
        return {"success": False, "error": str(e)}

def _generate_order_create_analysis(
    webhook_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate Slack message blocks for order analysis."""
    reasons = []
    order_number = webhook_data.get("order_number", "Unknown")
    order_id = webhook_data.get("order_id", "Unknown")
    order_created_at = webhook_data.get("created_at", "")
    product_title = webhook_data.get("product_title", "Unknown Product")
    product_id = webhook_data.get("product_id", "Unknown")
    order_url = build_order_url(order_id)
    order_data = {
        "order_id": order_id,
        "order_number": order_number,
        "order_created_at": order_created_at,
        "product_title": product_title,
        "product_id": product_id,
        "order_url": order_url,
    }
    
    result = {
        "order_data": order_data, 
        "reasons": reasons, 
        "action_needed": False
    }
    extracted_form_names = _extract_form_names(webhook_data)
    full_name_in_form = f"{extracted_form_names[0] or ''} {extracted_form_names[1] or ''}".strip()
    email_in_form = _extract_form_email(webhook_data)

    email_in_shopify = webhook_data.get("contact_email", "Unknown Shopify Email")
    customer = webhook_data.get("customer", {})
    full_name_in_shopify = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
    is_email_mismatch = order_has_email_mismatch(email_in_shopify, email_in_form)

    result["order_data"]["email_in_shopify"] = email_in_shopify
    result["order_data"]["full_name_in_shopify"] = full_name_in_shopify
    result["order_data"]["email_in_form"] = email_in_form
    result["order_data"]["full_name_in_form"] = full_name_in_form

    if is_email_mismatch:
        result["reasons"].append("email_mismatch")
        result["action_needed"] = True

    
    variant_title = _extract_variant_title(webhook_data)
    is_waitlist_registration = order_is_waitlist_registration(variant_title)
    
    if is_waitlist_registration:
        result["reasons"].append("waitlist_registration")
        result["action_needed"] = True

    # product_tags = 

    return result


def _extract_form_email(order_data: Dict[str, Any]) -> str:
    """
    Extract email from line item properties.
    
    Looks for the first property where 'email' appears in the property name (case insensitive).
    """
    line_items = order_data.get("line_items", [])
    if not line_items:
        return "Unknown form email"
    
    first_item = line_items[0]
    properties = first_item.get("properties", [])
    
    for prop in properties:
        prop_name = prop.get("name", "").lower()
        if "email" in prop_name:
            return prop.get("value", "").strip()
    
    return "Unknown form email"



def _extract_form_names(order_data: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """
    Extract first and last names from line item properties.
    
    Returns:
        tuple: (form_first_name, form_last_name)
    """
    line_items = order_data.get("line_items", [])
    if not line_items:
        return None, None
    
    first_item = line_items[0]
    properties = first_item.get("properties", [])
    
    form_first_name = None
    form_last_name = None
    
    for prop in properties:
        prop_name = prop.get("name", "").lower()
        if "first name" in prop_name:
            form_first_name = prop.get("value", "").strip()
        elif "last name" in prop_name:
            form_last_name = prop.get("value", "").strip()
    
    return form_first_name, form_last_name



def _extract_variant_title(order_data: Dict[str, Any]) -> Optional[str]:
    """Extract variant title from the first line item."""
    line_items = order_data.get("line_items", [])
    if not line_items:
        return None
    
    return line_items[0].get("variant_title")



def order_has_email_mismatch(contact_email: str, form_email: Optional[str]) -> bool:
    """
    Check if there's an email mismatch between contact email and form email.
    
    Returns True if both emails exist and are different (case insensitive comparison).
    """
    if not contact_email or not form_email:
        return False
    
    return contact_email.lower().strip() != form_email.lower().strip()



def order_is_waitlist_registration(variant_title: Optional[str]) -> bool:
    """
    Check if this is a waitlist registration.
    
    Returns True if 'waitlist' appears in the variant title (case insensitive).
    """
    if not variant_title:
        return False
    
    return "waitlist" in variant_title.lower()


# def _log_order_analysis(
#     order_number: Any,
#     customer_name: str,
#     contact_email: str,
#     form_email: Optional[str],
#     variant_title: Optional[str],
#     is_email_mismatch: bool,
#     is_waitlist_registration: bool
# ) -> None:
#     """Log detailed order analysis information."""
#     logger.info(f"📋 ORDER ANALYSIS: #{order_number} for {customer_name}")
#     logger.info(f"📧 Contact Email: {contact_email}")
#     logger.info(f"📝 Form Email: {form_email or 'Not provided'}")
#     logger.info(f"🏷️ Variant Title: {variant_title or 'Not available'}")
#     logger.info(f"⚠️ Email Mismatch: {'YES' if is_email_mismatch else 'NO'}")
#     logger.info(f"📋 Waitlist Registration: {'YES' if is_waitlist_registration else 'NO'}")
    
#     if is_email_mismatch:
#         logger.warning(f"🚨 EMAIL MISMATCH DETECTED for order #{order_number}")
#         logger.warning(f"   Contact: {contact_email}")
#         logger.warning(f"   Form: {form_email}")
    
#     if is_waitlist_registration:
#         logger.info(f"📋 WAITLIST REGISTRATION confirmed for order #{order_number}")


