"""
Slack message building utilities.
Extracted from the main SlackService to improve modularity.
"""

import hashlib
import time
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone
import logging
from shared.date_utils import format_date_and_time, parse_shopify_datetime
from modules.integrations.shopify.builders.shopify_url_builders import build_customer_url, build_order_url, build_product_url
from config import config
from config.slack import SlackGroup
from .message_builder_legacy import SlackMessageBuilderLegacy

logger = logging.getLogger(__name__)

slack_groups = SlackGroup()


class SlackMessageBuilder:
    """Helper class for building Slack messages with consistent formatting."""

    def __init__(self, sport_groups: dict[str, dict[str, str]]):
        self.sport_groups = slack_groups.all()
        self._legacy = SlackMessageBuilderLegacy(self)

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

    # === LEGACY REFUND MESSAGE METHODS (Thin wrappers to legacy module) ===
    
    def _get_order_created_time(self, order: Dict[str, Any]) -> str:
        """Extract and format order creation time from order data"""
        return self._legacy._get_order_created_time(order)

    def _create_cancel_order_button(self, order_id: str, order_number: str, requestor_name: Dict[str, str],
                                    requestor_email: str, refund_type: str, refund_amount: float,
                                    request_submitted_at: str = "") -> Dict[str, Any]:
        """Create the cancel order button (Step 1)"""
        return self._legacy._create_cancel_order_button(order_id, order_number, requestor_name, requestor_email,
                                                        refund_type, refund_amount, request_submitted_at)

    def _create_proceed_without_cancel_button(self, order_id: str, order_number: str, requestor_name: Dict[str, str],
                                             requestor_email: str, refund_type: str, refund_amount: float,
                                             request_submitted_at: str = "") -> Dict[str, Any]:
        """Create the proceed without canceling button (Step 1)"""
        return self._legacy._create_proceed_without_cancel_button(order_id, order_number, requestor_name,
                                                                  requestor_email, refund_type, refund_amount,
                                                                  request_submitted_at)

    def _create_deny_request_button(self, order_id: str, order_number: str, requestor_name: Dict[str, str],
                                   requestor_email: str, refund_type: str, refund_amount: float,
                                   request_submitted_at: str = "") -> Dict[str, Any]:
        """Create the deny request button (Step 1)"""
        return self._legacy._create_deny_request_button(order_id, order_number, requestor_name, requestor_email,
                                                        refund_type, refund_amount, request_submitted_at)

    def _create_process_refund_button(self, order_id: str, order_number: str, requestor_name: Dict[str, str],
                                     requestor_email: str, refund_type: str, refund_amount: float,
                                     order_cancelled: bool = False) -> Dict[str, Any]:
        """Create the process calculated refund button (Step 2)"""
        return self._legacy._create_process_refund_button(order_id, order_number, requestor_name, requestor_email,
                                                          refund_type, refund_amount, order_cancelled)

    def _create_custom_refund_button(self, order_id: str, order_number: str, requestor_name: Dict[str, str],
                                    requestor_email: str, refund_type: str, refund_amount: float,
                                    order_cancelled: bool = False) -> Dict[str, Any]:
        """Create the custom refund amount button (Step 2)"""
        return self._legacy._create_custom_refund_button(order_id, order_number, requestor_name, requestor_email,
                                                         refund_type, refund_amount, order_cancelled)

    def _create_no_refund_button(self, order_id: str, order_number: str, order_cancelled: bool = False,
                                requestor_name: Dict[str, str] = {}, requestor_email: str = "") -> Dict[str, Any]:
        """Create the no refund button (Step 2)"""
        return self._legacy._create_no_refund_button(order_id, order_number, order_cancelled, requestor_name,
                                                     requestor_email)

    def _create_edit_request_details_button(self, raw_order_number: str, requestor_name: Dict[str, str],
                                           requestor_email: str, refund_type: str, request_notes: str,
                                           current_time: str) -> Dict[str, Any]:
        """Create the edit request details button for email mismatch"""
        return self._legacy._create_edit_request_details_button(raw_order_number, requestor_name, requestor_email,
                                                                refund_type, request_notes, current_time)

    def _create_deny_email_mismatch_button(self, raw_order_number: str, requestor_name: Dict[str, str],
                                          requestor_email: str, refund_type: str, current_time: str) -> Dict[str, Any]:
        """Create the deny request button for email mismatch"""
        return self._legacy._create_deny_email_mismatch_button(raw_order_number, requestor_name, requestor_email,
                                                               refund_type, current_time)

    def create_refund_decision_message(self, order_data: Dict[str, Any], requestor_name: Dict[str, str],
                                      requestor_email: str, refund_type: str, sport_mention: str,
                                      sheet_link: str = "", order_cancelled: bool = False,
                                      slack_user_id: str = "Unknown User",
                                      original_timestamp: Optional[str] = None) -> Dict[str, Any]:
        """Create message for refund decision step"""
        return self._legacy.create_refund_decision_message(order_data, requestor_name, requestor_email, refund_type,
                                                           sport_mention, sheet_link, order_cancelled, slack_user_id,
                                                           original_timestamp)

    def _build_inventory_text(self, order_data: Dict[str, Any], product_title: str,
                             season_start_date: str) -> str:
        """Build the inventory status text for Slack messages"""
        return self._legacy._build_inventory_text(order_data, product_title, season_start_date)

    def build_success_message(self, order_data: Dict[str, Any], refund_calculation: Dict[str, Any],
                             requestor_info: Dict[str, Any], sheet_link: str,
                             request_initiated_at: Optional[str] = None, slack_channel_name: Optional[str] = None,
                             mention_strategy: Optional[str] = None) -> Dict[str, Any]:
        """Build a successful refund request message with action buttons"""
        return self._legacy.build_success_message(order_data, refund_calculation, requestor_info, sheet_link,
                                                  request_initiated_at, slack_channel_name, mention_strategy)

    def build_fallback_message(self, order_data: Dict[str, Any], requestor_info: Dict[str, Any], sheet_link: str,
                              error_message: str = "", refund_calculation: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build a fallback message when season info is missing"""
        return self._legacy.build_fallback_message(order_data, requestor_info, sheet_link, error_message,
                                                   refund_calculation)

    def build_error_message(self, error_type: str, requestor_info: Dict[str, Any], sheet_link: str,
                          raw_order_number: str = "", order_customer_email: str = "",
                          order_data: Optional[Dict[str, Any]] = None, customer_orders_url: Optional[str] = None,
                          existing_refunds_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build an error message for various error scenarios"""
        return self._legacy.build_error_message(error_type, requestor_info, sheet_link, raw_order_number,
                                               order_customer_email, order_data, customer_orders_url,
                                               existing_refunds_data)

    def build_email_mismatch_message(self, requestor_info: Dict[str, Any], raw_order_number: str,
                                    order_customer_email: str, sheet_link: str, order_data: Dict[str, Any],
                                    customer_orders_url: Optional[str] = None) -> Dict[str, Any]:
        """Build Slack message for email mismatch scenario with action buttons"""
        return self._legacy.build_email_mismatch_message(requestor_info, raw_order_number, order_customer_email,
                                                         sheet_link, order_data, customer_orders_url)

    def build_duplicate_refund_message(self, requestor_info: Dict[str, Any], raw_order_number: str, sheet_link: str,
                                      order_data: Optional[Dict[str, Any]] = None,
                                      existing_refunds_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build a message for duplicate refund requests with options to update or deny"""
        return self._legacy.build_duplicate_refund_message(requestor_info, raw_order_number, sheet_link, order_data,
                                                           existing_refunds_data)

    def _create_update_refund_details_button(self, order_number: str, requestor_name: Union[str, Dict[str, str]],
                                            requestor_email: str, refund_type: str, current_time: str) -> Dict[str, Any]:
        """Create an 'Update Refund Details' button for duplicate refund scenarios"""
        return self._legacy._create_update_refund_details_button(order_number, requestor_name, requestor_email,
                                                                 refund_type, current_time)

    def _create_deny_duplicate_refund_button(self, order_number: str, requestor_name: Union[str, Dict[str, str]],
                                            requestor_email: str, refund_type: str, current_time: str) -> Dict[str, Any]:
        """Create a 'Deny Duplicate Refund' button for duplicate refund scenarios"""
        return self._legacy._create_deny_duplicate_refund_button(order_number, requestor_name, requestor_email,
                                                                 refund_type, current_time)


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
    
    def build_refund_request_metadata(
        self,
        refund_request: Any,  # Type: Slack.RefundNotification
        order_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build metadata for refund request messages.
        
        Args:
            refund_request: Slack.RefundNotification Pydantic model instance
            order_data: Optional order data dict
        
        Returns:
            Dict with metadata fields
        """
        try:
            from models.slack import SlackMessageType
            
            metadata = {
                "order_number": refund_request.order_number,
                "requestor_email": refund_request.requestor_email,
                "refund_type": refund_request.refund_type.value,
                "message_type": SlackMessageType.REFUND_REQUEST.value,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            if order_data:
                order = order_data.get("order", {})
                metadata.update({
                    "order_id": order.get("id"),
                    "order_total": order.get("totalPrice"),
                    "order_status": order.get("fulfillmentStatus")
                })
            
            return metadata
        except ImportError:
            logger.warning("models.slack not available, returning basic metadata")
            return {
                "order_number": str(refund_request.order_number if hasattr(refund_request, 'order_number') else 'unknown'),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    
    def build_confirmation_metadata(self, confirmation: Any) -> Dict[str, Any]:
        """
        Build metadata for refund confirmation messages.
        
        Args:
            confirmation: Slack.RefundConfirmation Pydantic model instance
        
        Returns:
            Dict with metadata fields
        """
        try:
            from models.slack import SlackMessageType
            
            return {
                "order_number": confirmation.order_number,
                "refund_amount": str(confirmation.refund_amount),
                "processed_by": confirmation.processed_by,
                "message_type": SlackMessageType.REFUND_CONFIRMATION.value,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "shopify_refund_id": confirmation.shopify_refund_id
            }
        except ImportError:
            logger.warning("models.slack not available, returning basic metadata")
            return {
                "order_number": str(confirmation.order_number if hasattr(confirmation, 'order_number') else 'unknown'),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    
    def build_denial_metadata(self, denial: Any) -> Dict[str, Any]:
        """
        Build metadata for refund denial messages.
        
        Args:
            denial: Slack.RefundDenial Pydantic model instance
        
        Returns:
            Dict with metadata fields
        """
        try:
            from models.slack import SlackMessageType
            
            return {
                "order_number": denial.order_number,
                "denial_reason": denial.denial_reason,
                "denied_by": denial.denied_by,
                "message_type": SlackMessageType.REFUND_DENIAL.value,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        except ImportError:
            logger.warning("models.slack not available, returning basic metadata")
            return {
                "order_number": str(denial.order_number if hasattr(denial, 'order_number') else 'unknown'),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
    
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
