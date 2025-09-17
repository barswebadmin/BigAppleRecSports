"""
Simplified Slack refunds utilities.
Contains only essential methods that are actually used.
All other functionality has been moved to appropriate services.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from .builders import SlackMessageBuilder
except ImportError:
    from builders import SlackMessageBuilder

logger = logging.getLogger(__name__)


class SlackRefundsUtils:
    """
    Simplified utility class for Slack refund operations.
    Only contains methods that are actually used and don't belong elsewhere.
    """

    def __init__(self, orders_service, settings, message_builder=None):
        self.orders_service = orders_service
        self.settings = settings

        # Use provided message builder or create a fallback one
        if message_builder:
            self.message_builder = message_builder
        else:
            # Fallback for tests or direct usage - use empty sport groups
            self.message_builder = SlackMessageBuilder({})

        logger.info("🔧 SlackRefundsUtils initialized (simplified version)")

    def build_comprehensive_no_refund_message(
        self,
        order_data: Dict[str, Any],
        raw_order_number: str,
        order_cancelled: bool,
        requestor_name: Dict[str, str],
        requestor_email: str,
        processor_user: str,
        thread_ts: str,
        current_message_full_text: str,
    ) -> Dict[str, Any]:
        """
        Build comprehensive no refund message.
        This is a complex message building method that's specific to refunds workflow.
        """
        try:
            # Extract relevant information
            order = order_data.get("order", {})
            line_items = order.get("line_items", [])
            first_item = line_items[0] if line_items else {}
            
            # Build the message
            message_parts = [
                f"❌ *No Refund Approved* for {raw_order_number}",
                "",
                f"**Customer:** {requestor_name.get('first', '')} {requestor_name.get('last', '')}",
                f"**Email:** {requestor_email}",
                f"**Product:** {first_item.get('title', 'Unknown')}",
                f"**Order Status:** {'Cancelled' if order_cancelled else 'Active'}",
                "",
                f"**Processed by:** {processor_user}",
                f"**Processed at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ]
            
            # Add reason if available
            if "no refund reason" in current_message_full_text.lower():
                message_parts.append("")
                message_parts.append("**Reason:** No refund policy applies")
            
            message_text = "\n".join(message_parts)
            
            return {
                "text": message_text,
                "action_buttons": []  # No action buttons for final messages
            }
            
        except Exception as e:
            logger.error(f"Error building comprehensive no refund message: {str(e)}")
            return {
                "text": f"❌ No refund approved for {raw_order_number} (Error building message: {str(e)})",
                "action_buttons": []
            }

    def get_sport_group_mention(self, product_title: str) -> str:
        """Get sport group mention for a product (delegates to message builder)"""
        return self.message_builder.get_sport_group_mention(product_title)

    def get_order_url(self, order_id: str, order_number: str) -> str:
        """Get formatted order URL (delegates to message builder)"""
        return self.message_builder.get_order_url(order_id, order_number)

    def get_product_url(self, product_id: str) -> str:
        """Get formatted product URL (delegates to message builder)"""
        return self.message_builder.get_product_url(product_id)

    def build_comprehensive_success_message(self, *args, **kwargs):
        """Deprecated method - refund functionality removed."""
        logger.warning("build_comprehensive_success_message is deprecated - refund functionality removed")
        return {"text": "Refund functionality removed", "blocks": []}

    def build_completion_message_after_restocking(self, *args, **kwargs):
        """Deprecated method - refund functionality removed.""" 
        logger.warning("build_completion_message_after_restocking is deprecated - refund functionality removed")
        return {"text": "Refund functionality removed", "blocks": []}
