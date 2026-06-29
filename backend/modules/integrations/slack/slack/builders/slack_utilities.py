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
