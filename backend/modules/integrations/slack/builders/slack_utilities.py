"""
Utility classes for common Slack operations.
Provides reusable functionality for message building, caching, and formatting.
"""

import hashlib
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from models.slack import Slack, RefundType, SlackMessageType

logger = logging.getLogger(__name__)


class SlackMessageBuilder:
    """
    Utility class for building Slack messages with consistent formatting.
    Handles message text, action buttons, and metadata.
    """
    
    def __init__(self):
        """Initialize the message builder."""
        pass
    
    def build_refund_request_message(
        self,
        refund_request: Slack.RefundNotification,
        order_data: Optional[Dict[str, Any]] = None,
        refund_calculation: Optional[Dict[str, Any]] = None,
        error_type: Optional[str] = None
    ) -> str:
        """Build message text for a refund request notification."""
        requestor_name = self._format_requestor_name(refund_request.requestor_name)
        
        if error_type:
            return self._build_error_message(refund_request, error_type, requestor_name)
        elif refund_calculation and refund_calculation.get("success"):
            return self._build_success_message(refund_request, refund_calculation, requestor_name)
        else:
            return self._build_basic_message(refund_request, requestor_name)
    
    def build_refund_confirmation_message(self, confirmation: Slack.RefundConfirmation) -> str:
        """Build message text for a refund confirmation."""
        return (
            f"✅ *Refund Confirmed* for {confirmation.order_number}\n\n"
            f"**Customer:** {confirmation.customer_name}\n"
            f"**Email:** {confirmation.customer_email}\n"
            f"**Amount:** ${confirmation.refund_amount:.2f}\n"
            f"**Type:** {confirmation.refund_type.value.title()}\n"
            f"**Processed by:** {confirmation.processed_by}\n"
            f"**Processed at:** {self._format_timestamp(confirmation.processed_at)}"
            + (f"\n**Notes:** {confirmation.notes}" if confirmation.notes else "")
        )
    
    def build_refund_denial_message(self, denial: Slack.RefundDenial) -> str:
        """Build message text for a refund denial."""
        return (
            f"❌ *Refund Denied* for {denial.order_number}\n\n"
            f"**Customer:** {denial.customer_name}\n"
            f"**Email:** {denial.customer_email}\n"
            f"**Reason:** {denial.denial_reason}\n"
            f"**Denied by:** {denial.denied_by}\n"
            f"**Denied at:** {self._format_timestamp(denial.denied_at)}"
            + (f"\n**Notes:** {denial.notes}" if denial.notes else "")
        )
    
    def build_order_update_message(self, update: Slack.OrderUpdate) -> str:
        """Build message text for an order update."""
        status_change = ""
        if update.old_status and update.new_status:
            status_change = f"**Status:** {update.old_status} → {update.new_status}\n"
        
        return (
            f"📦 *Order Update* for {update.order_number}\n\n"
            f"**Customer:** {update.customer_name}\n"
            f"{status_change}"
            f"**Update Type:** {update.update_type}\n"
            f"**Updated by:** {update.updated_by}\n"
            f"**Updated at:** {self._format_timestamp(update.updated_at)}"
            + (f"\n**Notes:** {update.notes}" if update.notes else "")
        )
    
    def build_leadership_notification_message(self, notification: Slack.LeadershipNotification) -> str:
        """Build message text for a leadership notification."""
        records_info = ""
        if notification.records_processed:
            records_info = f"**Records processed:** {notification.records_processed}"
            if notification.records_added:
                records_info += f" ({notification.records_added} added"
                if notification.records_updated:
                    records_info += f", {notification.records_updated} updated"
                records_info += ")"
        
        return (
            f"👥 *Leadership Update*: {notification.notification_type}\n\n"
            f"**Title:** {notification.spreadsheet_title or 'N/A'}\n"
            f"**Year:** {notification.year or 'N/A'}\n"
            f"{records_info}\n"
            f"**Processed by:** {notification.processed_by}\n"
            f"**Processed at:** {self._format_timestamp(notification.processed_at)}"
            + (f"\n**Notes:** {notification.notes}" if notification.notes else "")
        )
    
    def build_action_buttons(
        self,
        refund_request: Slack.RefundNotification,
        order_data: Optional[Dict[str, Any]] = None,
        error_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Build action buttons for refund notifications."""
        buttons = []
        
        if error_type:
            buttons.extend([
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Edit Details"},
                    "action_id": "edit_request_details",
                    "value": refund_request.order_number
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Deny Request"},
                    "action_id": "deny_refund_request",
                    "value": refund_request.order_number,
                    "style": "danger"
                }
            ])
        else:
            buttons.extend([
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Process Refund"},
                    "action_id": "process_refund",
                    "value": refund_request.order_number,
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Custom Amount"},
                    "action_id": "custom_refund_amount",
                    "value": refund_request.order_number
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "No Refund"},
                    "action_id": "no_refund",
                    "value": refund_request.order_number,
                    "style": "danger"
                }
            ])
        
        return buttons
    
    def _format_requestor_name(self, requestor_name) -> str:
        """Format requestor name consistently."""
        if isinstance(requestor_name, dict):
            first = requestor_name.get('first', '')
            last = requestor_name.get('last', '')
            return f"{first} {last}".strip()
        else:
            return str(requestor_name)
    
    def _format_timestamp(self, timestamp: str) -> str:
        """Format timestamp for display."""
        try:
            if timestamp:
                # Try to parse and format the timestamp
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            pass
        return timestamp or "Unknown"
    
    def _build_error_message(self, refund_request: Slack.RefundNotification, error_type: str, requestor_name: str) -> str:
        """Build error message."""
        return (
            f"❌ *Error Processing Refund Request* for {refund_request.order_number}\n\n"
            f"**Requestor:** {requestor_name}\n"
            f"**Email:** {refund_request.requestor_email}\n"
            f"**Error Type:** {error_type}\n"
            f"**Refund Type:** {refund_request.refund_type.value.title()}"
            + (f"\n**Notes:** {refund_request.notes}" if refund_request.notes else "")
        )
    
    def _build_success_message(self, refund_request: Slack.RefundNotification, refund_calculation: Dict[str, Any], requestor_name: str) -> str:
        """Build success message with calculated refund."""
        amount = refund_calculation.get("refund_amount", "Unknown")
        return (
            f"💰 *Refund Request* for {refund_request.order_number}\n\n"
            f"**Requestor:** {requestor_name}\n"
            f"**Email:** {refund_request.requestor_email}\n"
            f"**Refund Amount:** ${amount}\n"
            f"**Type:** {refund_request.refund_type.value.title()}"
            + (f"\n**Notes:** {refund_request.notes}" if refund_request.notes else "")
        )
    
    def _build_basic_message(self, refund_request: Slack.RefundNotification, requestor_name: str) -> str:
        """Build basic refund request message."""
        return (
            f"📋 *Refund Request* for {refund_request.order_number}\n\n"
            f"**Requestor:** {requestor_name}\n"
            f"**Email:** {refund_request.requestor_email}\n"
            f"**Type:** {refund_request.refund_type.value.title()}"
            + (f"\n**Notes:** {refund_request.notes}" if refund_request.notes else "")
        )


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
    """
    
    def build_refund_request_metadata(
        self,
        refund_request: Slack.RefundNotification,
        order_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build metadata for refund request messages."""
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
    
    def build_confirmation_metadata(self, confirmation: Slack.RefundConfirmation) -> Dict[str, Any]:
        """Build metadata for refund confirmation messages."""
        return {
            "order_number": confirmation.order_number,
            "refund_amount": str(confirmation.refund_amount),
            "processed_by": confirmation.processed_by,
            "message_type": SlackMessageType.REFUND_CONFIRMATION.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "shopify_refund_id": confirmation.shopify_refund_id
        }
    
    def build_denial_metadata(self, denial: Slack.RefundDenial) -> Dict[str, Any]:
        """Build metadata for refund denial messages."""
        return {
            "order_number": denial.order_number,
            "denial_reason": denial.denial_reason,
            "denied_by": denial.denied_by,
            "message_type": SlackMessageType.REFUND_DENIAL.value,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    def build_order_update_metadata(self, update: Slack.OrderUpdate) -> Dict[str, Any]:
        """Build metadata for order update messages."""
        return {
            "order_number": update.order_number,
            "update_type": update.update_type,
            "updated_by": update.updated_by,
            "message_type": SlackMessageType.ORDER_UPDATE.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "old_status": update.old_status,
            "new_status": update.new_status
        }
    
    def build_leadership_metadata(self, notification: Slack.LeadershipNotification) -> Dict[str, Any]:
        """Build metadata for leadership notification messages."""
        return {
            "notification_type": notification.notification_type,
            "processed_by": notification.processed_by,
            "message_type": SlackMessageType.LEADERSHIP_NOTIFICATION.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "year": notification.year,
            "records_processed": notification.records_processed
        }
