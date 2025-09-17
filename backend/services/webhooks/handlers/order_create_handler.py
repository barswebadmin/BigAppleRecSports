"""
Order Create Webhook Handler

Handles Shopify order create webhooks specifically, including email mismatch detection
and waitlist registration identification.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from ...shopify.shopify_order_utils import build_shopify_order_url
from utils.date_utils import format_date_and_time

logger = logging.getLogger(__name__)


def evaluate_order_create_webhook(body: bytes) -> Dict[str, Any]:
    """
    Handle Shopify order create webhook with email mismatch and waitlist detection.
    
    Args:
        body: Raw webhook body containing order data
        
    Returns:
        Dict containing success status, analysis results, and detailed order information
    """
    try:
        order_data = json.loads(body.decode("utf-8"))

        # Extract basic order information
        order_number = order_data.get("order_number", "unknown")
        contact_email = order_data.get("contact_email", "")
        customer = order_data.get("customer", {})
        name_in_shopify = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        order_created_at = order_data.get("created_at", "")
        
        # Extract admin_graphql_api_id and parse order_id
        admin_graphql_api_id = order_data.get("admin_graphql_api_id", "")
        order_id = admin_graphql_api_id.split('/')[-1] if admin_graphql_api_id else ""
        
        # Extract form information from line item properties
        form_email = _extract_form_email(order_data)
        form_first_name, form_last_name = _extract_form_names(order_data)
        name_in_form = f"{form_first_name or ''} {form_last_name or ''}".strip()
        
        # Extract product title from first line item
        line_items = order_data.get("line_items", [])
        product_title = line_items[0].get("title", "") if line_items else ""
        variant_title = _extract_variant_title(order_data)
        
        # Perform analysis
        is_email_mismatch = _check_email_mismatch(contact_email, form_email)
        is_waitlist_registration = _check_waitlist_registration(variant_title)
        
        # Determine action needed and reasons
        action_needed = is_email_mismatch or is_waitlist_registration
        reasons = []
        if is_email_mismatch:
            reasons.append("email_mismatch")
        if is_waitlist_registration:
            reasons.append("waitlist_registration")
        
        # Log findings first
        _log_order_analysis(order_number, name_in_shopify, contact_email, form_email, 
                          variant_title, is_email_mismatch, is_waitlist_registration)
        
        # Build data structure
        data = {
            "order_id": order_id,
            "order_number": order_number,
            "shopify_email": contact_email,
            "name_in_shopify": name_in_shopify,
            "name_in_form": name_in_form,
            "form_email": form_email,
            "form_first_name": form_first_name,
            "order_created_at": order_created_at,
            "product_title": product_title
        }
        
        # Generate analysis with Slack blocks
        result = _generate_analysis(order_data, action_needed, reasons, data)
        
        return result

    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in order webhook body: {e}")
        return {"success": False, "error": "Invalid JSON payload"}
    except Exception as e:
        logger.error(f"💥 Error processing order create webhook: {e}")
        return {"success": False, "error": str(e)}

def _extract_form_email(order_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract email from line item properties.
    
    Looks for the first property where 'email' appears in the property name (case insensitive).
    """
    line_items = order_data.get("line_items", [])
    if not line_items:
        return None
    
    first_item = line_items[0]
    properties = first_item.get("properties", [])
    
    for prop in properties:
        prop_name = prop.get("name", "").lower()
        if "email" in prop_name:
            return prop.get("value", "").strip()
    
    return None


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


def _check_email_mismatch(contact_email: str, form_email: Optional[str]) -> bool:
    """
    Check if there's an email mismatch between contact email and form email.
    
    Returns True if both emails exist and are different (case insensitive comparison).
    """
    if not contact_email or not form_email:
        return False
    
    return contact_email.lower().strip() != form_email.lower().strip()


def _check_waitlist_registration(variant_title: Optional[str]) -> bool:
    """
    Check if this is a waitlist registration.
    
    Returns True if 'waitlist' appears in the variant title (case insensitive).
    """
    if not variant_title:
        return False
    
    return "waitlist" in variant_title.lower()


def _generate_analysis(
    order_data: Dict[str, Any],
    action_needed: bool,
    reasons: List[str],
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate Slack message blocks for order analysis."""
    order_number = data.get("order_number", "Unknown")
    order_id = data.get("order_id", "Unknown")
    name_in_shopify = data.get("name_in_shopify", "Unknown")
    
    # Build clickable order link
    if order_id != "Unknown":
        order_url = build_shopify_order_url(order_id)
        order_link = f"<{order_url}|#{order_number}>"
    else:
        order_link = f"#{order_number}"
    
    # Header section
    header_text = f"⚠️ Attention"
    
    # Status indicator
    if action_needed:
        status_emoji = "🚨"
        status_text = "Action Required"
        color = "#FF0000"  # Red
    else:
        status_emoji = "✅"
        status_text = "Standard Order"
        color = "#36a64f"  # Green
    
    # Build reason text
    reason_text = ""
    if "email_mismatch" in reasons:
        reason_text += "📧 Mismatching emails between Shopify profile and form fields - please reach out and confirm so the player does not miss email notifications\n"
    if "waitlist_registration" in reasons:
        reason_text += "📋 Player registered off the waitlist - please ensure you reach out and add them to a team\n"
    
    if not reason_text:
        reason_text = "No issues detected"
    
    # Create Slack blocks
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{header_text}*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{status_emoji} *{status_text}*\n\n*Customer:* {name_in_shopify}\n*Order:* {order_link}\n\n*Analysis:*\n{reason_text}"
            }
        }
    ]
    
    # Add order details section
    order_details = []
    if data.get("shopify_email"):
        order_details.append(f"*Shopify Email:* {data['shopify_email']}")
    if data.get("form_email"):
        order_details.append(f"*Form Email:* {data['form_email']}")
    if data.get("product_title"):
        order_details.append(f"*Product:* {data['product_title']}")
    if data.get("order_created_at"):
        formatted_date = format_date_and_time(data['order_created_at'])
        order_details.append(f"*Created:* {formatted_date}")
    
    if order_details:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(order_details)
            }
        })
    
    return {
        "action_needed": action_needed,
        "reason": reasons,
        "data": data,
        "slack_blocks": blocks
    }


def _log_order_analysis(
    order_number: Any,
    customer_name: str,
    contact_email: str,
    form_email: Optional[str],
    variant_title: Optional[str],
    is_email_mismatch: bool,
    is_waitlist_registration: bool
) -> None:
    """Log detailed order analysis information."""
    logger.info(f"📋 ORDER ANALYSIS: #{order_number} for {customer_name}")
    logger.info(f"📧 Contact Email: {contact_email}")
    logger.info(f"📝 Form Email: {form_email or 'Not provided'}")
    logger.info(f"🏷️ Variant Title: {variant_title or 'Not available'}")
    logger.info(f"⚠️ Email Mismatch: {'YES' if is_email_mismatch else 'NO'}")
    logger.info(f"📋 Waitlist Registration: {'YES' if is_waitlist_registration else 'NO'}")
    
    if is_email_mismatch:
        logger.warning(f"🚨 EMAIL MISMATCH DETECTED for order #{order_number}")
        logger.warning(f"   Contact: {contact_email}")
        logger.warning(f"   Form: {form_email}")
    
    if is_waitlist_registration:
        logger.info(f"📋 WAITLIST REGISTRATION confirmed for order #{order_number}")


