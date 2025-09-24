"""
Slack utility methods.
Convenience methods and helpers for common Slack operations.
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class SlackUtilities:
    """Utility methods for common Slack operations"""

    def __init__(self, message_builder, message_parsers):
        self.message_builder = message_builder
        self.message_parsers = message_parsers

    def extract_sheet_link(self, message_text: str) -> str:
        """Extract sheet link from message text"""
        return self.message_parsers.extract_sheet_link(message_text)

    def extract_season_start_info(self, message_text: str) -> Dict[str, Optional[str]]:
        """Extract season start info from message text"""
        return self.message_parsers.extract_season_start_info(message_text)

    def extract_order_number(self, message_text: str) -> Optional[str]:
        """Extract order number from message text"""
        return self.message_parsers.extract_order_number(message_text)

    def extract_email(self, message_text: str) -> Optional[str]:
        """Extract email address from message text"""
        return self.message_parsers.extract_email(message_text)

    def extract_refund_amount(self, message_text: str) -> Optional[float]:
        """Extract refund amount from message text"""
        return self.message_parsers.extract_refund_amount(message_text)

    def _determine_message_type(self, action_buttons: Optional[List[Dict[str, Any]]]) -> str:
        """Determine the type of message based on action buttons"""
        if not action_buttons:
            return "STEP 4: Final Completion Message (No Buttons)"
        
        action_ids = [btn.get("action_id", "") for btn in action_buttons]
        
        if "process_refund" in action_ids and "custom_refund" in action_ids and "no_refund" in action_ids:
            return "STEP 2: Refund Decision (Process/Custom/No Refund)"
        elif "approve_refund" in action_ids and "deny_refund" in action_ids:
            return "STEP 3: Refund Approval (Approve/Deny)"
        else:
            return f"UNKNOWN: Action IDs {action_ids}"
