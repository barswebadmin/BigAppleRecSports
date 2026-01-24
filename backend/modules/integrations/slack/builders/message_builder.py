"""
Slack message building utilities.
Extracted from the main SlackService to improve modularity.
"""

import hashlib
import time
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
import logging
from shared.date_utils import format_date_and_time, parse_shopify_datetime
# Add backend to path early
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Lazy import Shopify URL builders to avoid circular dependencies
def _get_shopify_url_builders():
    """Lazy import of Shopify URL builders to avoid circular dependencies."""
    from modules.integrations.shopify.builders.shopify_url_builders import (
        build_customer_url,
        build_order_url,
        build_product_url
    )
    return build_customer_url, build_order_url, build_product_url
from config_old_deprecated.slack import SlackGroup
logger = logging.getLogger(__name__)

slack_groups = SlackGroup()


class SlackMessageBuilder:
    """Helper class for building Slack messages with consistent formatting."""

    def __init__(self, sport_groups: dict[str, dict[str, str]]):
        self.sport_groups = slack_groups.all()

    def build_header_block(self, header_text: str) -> Dict[str, Any]:
        """Build a header block for Slack"""
        return {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text}
        }

    def build_section_block(self, text: str) -> Dict[str, Any]:
        """Build a section block for Slack"""
        return {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text}
        }
    
    def get_group_mention(self, text: str) -> str:
        """Resolve a group mention using SlackConfig.Group mapping; fallback to @here.

        Attempts exact key match first, then substring match on known keys.
        """
        try:
            if not isinstance(text, str) or not text.strip():
                return "@here"

            target = text.lower().strip()

            group_info = SlackGroup.get(target)
            return group_info["id"] if "id" in group_info else "@here"
        except Exception:
            return "@here"

    def build_hyperlink(self, url: str, text: str) -> str:
        """Build a hyperlink for Slack"""
        return f"<{url}|{text}>"

    def _get_request_type_text(self, refund_type: str) -> str:
        """Get detailed request type text for messages"""
        if refund_type.lower() == "refund":
            return "💵 Refund back to original form of payment"
        elif refund_type.lower() == "credit":
            return "🎟️ Store Credit to use toward a future order"
        else:
            return f"❓ {refund_type.title()}"

    def _get_optional_request_notes(self, request_notes: str) -> str:
        """Get formatted optional request notes"""
        try:
            if (
                request_notes
                and isinstance(request_notes, str)
                and request_notes.strip()
            ):
                return f"*Notes provided by requestor*: {request_notes}\n\n"
            return ""
        except Exception:
            return ""

    def _get_requestor_line(
        self,
        requestor_name: Dict[str, str],
        requestor_email: str,
        customer_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Get formatted requestor line with optional customer profile hyperlink"""
        try:
            if isinstance(requestor_name, dict):
                first_name = requestor_name.get("first", "")
                last_name = requestor_name.get("last", "")
                full_name = f"{first_name} {last_name}".strip()

                if full_name and customer_data and customer_data.get("id"):
                    # Create hyperlinked name to customer profile
                    build_customer_url, _, _ = _get_shopify_url_builders()
                    customer_url = self.build_hyperlink(build_customer_url(customer_data["id"]), full_name)
                    return f"📧 *Requested by:* <{customer_url}|{full_name}> ({requestor_email})\n\n"
                elif full_name:
                    # Fallback to plain text name
                    return f"📧 *Requested by:* {full_name} ({requestor_email})\n\n"
            return f"📧 *Requested by:* {requestor_email}\n\n"
        except Exception:
            return f"📧 *Requested by:* {requestor_email}\n\n"

    def _get_sheet_link_line(self, sheet_link: Optional[str]) -> str:
        """Get formatted sheet link line"""
        try:
            if sheet_link and isinstance(sheet_link, str) and sheet_link.strip():
                return f"\n \n 🔗 *<{sheet_link}|View Request in Google Sheets>*\n\n"
            return ""
        except Exception:
            return ""

    # === REFUND MESSAGE METHODS ===
    
    def _get_order_created_time(self, order: Dict[str, Any]) -> str:
        """Extract and format order creation time from order data"""
        try:
            created_at_fields = [
                "created_at",
                "createdAt",
                "orderCreatedAt",
                "order_created_at",
                "processedAt",
                "processed_at",
            ]

            for field in created_at_fields:
                if field in order and order[field]:
                    created_at = parse_shopify_datetime(order[field])
                    if created_at:
                        return format_date_and_time(created_at)

            return "Unknown"

        except Exception:
            return "Unknown"

    def _create_cancel_order_button(
        self,
        order_id: str,
        order_number: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        refund_type: str,
        refund_amount: float,
        request_submitted_at: str = "",
    ) -> Dict[str, Any]:
        """Create the cancel order button (Step 1)"""
        try:
            first_name = requestor_name.get("first", "")
            last_name = requestor_name.get("last", "")

            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Cancel Order → Proceed"},
                "style": "primary",
                "action_id": "cancel_order",
                "value": f"rawOrderNumber={order_number}|refundType={refund_type}|requestorEmail={requestor_email}|first={first_name}|last={last_name}|email={requestor_email}|requestSubmittedAt={request_submitted_at}",
                "confirm": {
                    "title": {"type": "plain_text", "text": "Cancel Order"},
                    "text": {
                        "type": "plain_text",
                        "text": f"Cancel order {order_number} in Shopify? This will show refund options next.",
                    },
                    "confirm": {"type": "plain_text", "text": "Yes, cancel order"},
                    "deny": {"type": "plain_text", "text": "No, keep order"},
                },
            }
        except Exception:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Cancel Order → Proceed"},
                "style": "primary",
                "action_id": "cancel_order",
                "value": f"rawOrderNumber={order_number}",
            }

    def _create_proceed_without_cancel_button(
        self,
        order_id: str,
        order_number: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        refund_type: str,
        refund_amount: float,
        request_submitted_at: str = "",
    ) -> Dict[str, Any]:
        """Create the proceed without canceling button (Step 1)"""
        try:
            first_name = requestor_name.get("first", "")
            last_name = requestor_name.get("last", "")

            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "➡️ Do Not Cancel → Proceed"},
                "action_id": "proceed_without_cancel",
                "value": f"rawOrderNumber={order_number}|refundType={refund_type}|requestorEmail={requestor_email}|first={first_name}|last={last_name}|email={requestor_email}|requestSubmittedAt={request_submitted_at}",
                "confirm": {
                    "title": {
                        "type": "plain_text",
                        "text": "Proceed Without Canceling",
                    },
                    "text": {
                        "type": "plain_text",
                        "text": f"Keep order {order_number} active and proceed to refund options?",
                    },
                    "confirm": {"type": "plain_text", "text": "Yes, proceed"},
                    "deny": {"type": "plain_text", "text": "Cancel"},
                },
            }
        except Exception:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "➡️ Do Not Cancel → Proceed"},
                "action_id": "proceed_without_cancel",
                "value": f"rawOrderNumber={order_number}",
                "confirm": {
                    "title": {
                        "type": "plain_text",
                        "text": "Proceed Without Canceling",
                    },
                    "text": {
                        "type": "plain_text",
                        "text": f"Keep order {order_number} active and proceed to refund options?",
                    },
                    "confirm": {"type": "plain_text", "text": "Yes, proceed"},
                    "deny": {"type": "plain_text", "text": "Cancel"},
                },
            }

    def _create_deny_request_button(
        self,
        order_id: str,
        order_number: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        refund_type: str,
        refund_amount: float,
        request_submitted_at: str = "",
    ) -> Dict[str, Any]:
        """Create the deny request button (Step 1)"""
        try:
            first_name = requestor_name.get("first", "")
            last_name = requestor_name.get("last", "")

            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "🚫 Deny Request"},
                "style": "danger",
                "action_id": "deny_refund_request_show_modal",
                "value": f"rawOrderNumber={order_number}|refundType={refund_type}|requestorEmail={requestor_email}|first={first_name}|last={last_name}|email={requestor_email}|requestSubmittedAt={request_submitted_at}",
            }
        except Exception:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "🚫 Deny Request"},
                "style": "danger",
                "action_id": "deny_refund_request_show_modal",
                "value": f"rawOrderNumber={order_number}",
            }


    def _create_edit_request_details_button(
        self,
        raw_order_number: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        refund_type: str,
        request_notes: str,
        current_time: str,
    ) -> Dict[str, Any]:
        """Create the edit request details button for email mismatch"""
        try:
            first_name = requestor_name.get("first", "")
            last_name = requestor_name.get("last", "")
            full_name = f"{first_name} {last_name}".strip()

            order_number = (
                raw_order_number
                if raw_order_number.startswith("#")
                else f"#{raw_order_number}"
            )

            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "✏️ Edit Request Details"},
                "style": "primary",
                "action_id": "edit_request_details",
                "value": f"orderName={order_number}|requestorName={full_name}|requestorEmail={requestor_email}|refundType={refund_type}|submittedAt={current_time}",
            }
        except Exception:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "✏️ Edit Request Details"},
                "style": "primary",
                "action_id": "edit_request_details",
                "value": f"rawOrderNumber={raw_order_number}|requestorEmail={requestor_email}",
            }

    def _create_deny_email_mismatch_button(
        self,
        raw_order_number: str,
        requestor_name: Dict[str, str],
        requestor_email: str,
        refund_type: str,
        current_time: str,
    ) -> Dict[str, Any]:
        """Create the deny request button for email mismatch"""
        try:
            first_name = requestor_name.get("first", "")
            last_name = requestor_name.get("last", "")

            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "🚫 Deny Request"},
                "style": "danger",
                "action_id": "deny_refund_request_show_modal",
                "value": f"rawOrderNumber={raw_order_number}|refundType={refund_type}|requestorEmail={requestor_email}|first={first_name}|last={last_name}|requestSubmittedAt={current_time}",
            }
        except Exception:
            return {
                "type": "button",
                "text": {"type": "plain_text", "text": "🚫 Deny Request"},
                "style": "danger",
                "action_id": "deny_refund_request_show_modal",
                "value": f"rawOrderNumber={raw_order_number}|requestorEmail={requestor_email}",
            }


    def _build_inventory_text(
        self, order_data: Dict[str, Any], product_title: str, season_start_date: str
    ) -> str:
        """Build the inventory status text for Slack messages"""
        try:
            inventory_summary = order_data.get("inventory_summary", {})

            if not inventory_summary.get("success"):
                return "📦 *Inventory information unavailable*"

            inventory_list = inventory_summary.get("inventory_list", {})
            inventory_order = ["veteran", "early", "open", "waitlist"]

            order = order_data.get("order", {})
            product = order.get("product", {})
            product.get("productId", "")

            text = "*Current Inventory:*\n"

            for key in inventory_order:
                if (
                    key in inventory_list
                    and inventory_list[key].get("inventory") is not None
                ):
                    variant_info = inventory_list[key]
                    inventory_count = variant_info.get("inventory", 0)
                    variant_name = variant_info.get("name", key.title())

                    if isinstance(inventory_count, (int, float)):
                        inventory_text = f"{int(inventory_count)} spots available"
                    else:
                        inventory_text = "Error fetching current inventory"

                    text += f"• *{variant_name}*: {inventory_text}\n"

            return text.rstrip()

        except Exception as e:
            return f"📦 *Error fetching inventory information: {str(e)}*"




class SlackCacheManager:
    """
    Utility class for managing Slack message deduplication cache.
    Handles cache operations, expiration, and cleanup.
    """
    
    def __init__(self, cache_expiry_seconds: int = 300):
        """
        Initialize the cache manager.
        
        Args:
            cache_expiry_seconds: How long to keep cache entries (default: 5 minutes)
        """
        self._cache = {}
        self._cache_expiry_seconds = cache_expiry_seconds
    
    def generate_message_hash(self, order_data: Dict[str, Any], requestor_info: Dict[str, Any]) -> str:
        """Generate a unique hash for deduplication based on order and requestor info."""
        try:
            order = order_data.get("order", {}) if order_data else {}
            order_number = (
                order.get("orderNumber")
                or order.get("orderName")
                or order.get("name")
                or "unknown"
            )
            requestor_email = requestor_info.get("email", "unknown")
            refund_type = requestor_info.get("refund_type", "refund")

            # Create deduplication key from critical fields
            dedup_string = f"{order_number}|{requestor_email}|{refund_type}"
            return hashlib.md5(dedup_string.encode()).hexdigest()

        except Exception as e:
            logger.warning(f"Failed to generate message hash: {e}")
            return str(time.time())  # Fallback to timestamp
    
    def is_duplicate_message(self, message_hash: str) -> bool:
        """Check if this message has already been sent recently."""
        try:
            self._clean_expired_cache()
            
            if message_hash in self._cache:
                logger.info(f"Duplicate message detected: {message_hash}")
                return True
            
            # Add to cache
            self._cache[message_hash] = time.time()
            return False

        except Exception as e:
            logger.warning(f"Failed to check duplicate message: {e}")
            return False
    
    def _clean_expired_cache(self):
        """Remove expired entries from the cache."""
        try:
            current_time = time.time()
            expired_keys = [
                key
                for key, timestamp in self._cache.items()
                if current_time - timestamp > self._cache_expiry_seconds
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.info(f"Cleaned {len(expired_keys)} expired cache entries")

        except Exception as e:
            logger.warning(f"Failed to clean cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return {
            "total_entries": len(self._cache),
            "cache_expiry_seconds": self._cache_expiry_seconds,
            "oldest_entry": min(self._cache.values()) if self._cache else None,
            "newest_entry": max(self._cache.values()) if self._cache else None
        }


class SlackMetadataBuilder:
    """
    Utility class for building consistent Slack message metadata.
    Handles metadata creation for different message types.
    
    Note: This class uses Pydantic models from models.slack which may need
    to be updated if you're not using those models in your workflow.
    """
    
    
    def build_order_update_metadata(self, update: Any) -> Dict[str, Any]:
        """
        Build metadata for order update messages.
        
        Args:
            update: Slack.OrderUpdate Pydantic model instance
        
        Returns:
            Dict with metadata fields
        """
        try:
            from models.slack import SlackMessageType
            
            return {
                "order_number": update.order_number,
                "update_type": update.update_type,
                "updated_by": update.updated_by,
                "message_type": SlackMessageType.ORDER_UPDATE.value,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "old_status": update.old_status,
                "new_status": update.new_status
            }
        except ImportError:
            logger.warning("models.slack not available, returning basic metadata")
            return {
                "order_number": str(update.order_number if hasattr(update, 'order_number') else 'unknown'),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    
    def build_leadership_metadata(self, notification: Any) -> Dict[str, Any]:
        """
        Build metadata for leadership notification messages.
        
        Args:
            notification: Slack.LeadershipNotification Pydantic model instance
        
        Returns:
            Dict with metadata fields
        """
        try:
            from models.slack import SlackMessageType
            
            return {
                "notification_type": notification.notification_type,
                "processed_by": notification.processed_by,
                "message_type": SlackMessageType.LEADERSHIP_NOTIFICATION.value,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "year": notification.year,
                "records_processed": notification.records_processed
            }
        except ImportError:
            logger.warning("models.slack not available, returning basic metadata")
            return {
                "notification_type": str(notification.notification_type if hasattr(notification, 'notification_type') else 'unknown'),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
