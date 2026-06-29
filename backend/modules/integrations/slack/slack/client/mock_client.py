"""
Mock Slack client for testing purposes.
Provides mock implementations of Slack API methods.
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class MockSlackClient:
    """Mock Slack client for testing purposes."""
    
    def __init__(self, token: str, channel_id: str):
        self.token = token
        self.channel_id = channel_id
        logger.info(f"🧪 MockSlackClient initialized with token: {token[:10]}...")

    def chat_postMessage(self, **kwargs):
        """Mock implementation of chat.postMessage"""
        channel = kwargs.get("channel", self.channel_id)
        text = kwargs.get("text", "")
        blocks = kwargs.get("blocks", [])
        metadata = kwargs.get("metadata", {})
        thread_ts = kwargs.get("thread_ts")
        
        # Determine message type for logging
        action_buttons = []
        if blocks:
            for block in blocks:
                if block.get("type") == "actions":
                    action_buttons = block.get("elements", [])
        
        message_type = self._determine_message_type(action_buttons)
        
        print(f"🧪 === MOCK SLACK MESSAGE SEND ===")
        print(f"📋 Message Type: {message_type}")
        print(f"📍 Channel: {channel}")
        print(f"🔘 Action Buttons: {len(action_buttons)}")
        if thread_ts:
            print(f"🧵 Thread: {thread_ts}")
        print(f"🧪 === END MOCK SLACK MESSAGE SEND ===")
        
        return {
            "ok": True,
            "ts": "1234567890.123456",
            "message_ts": "1234567890.123456",
            "channel": channel,
            "message": {
                "text": text,
                "blocks": blocks
            }
        }

    def chat_update(self, **kwargs):
        """Mock implementation of chat.update"""
        channel = kwargs.get("channel", self.channel_id)
        ts = kwargs.get("ts", "1234567890.123456")
        text = kwargs.get("text", "")
        blocks = kwargs.get("blocks", [])
        metadata = kwargs.get("metadata", {})
        
        # Determine message type for logging
        action_buttons = []
        if blocks:
            for block in blocks:
                if block.get("type") == "actions":
                    action_buttons = block.get("elements", [])
        
        message_type = self._determine_message_type(action_buttons)
        
        print(f"🧪 === MOCK SLACK MESSAGE UPDATE ===")
        print(f"📋 Message Type: {message_type}")
        print(f"📍 Channel: {channel}")
        print(f"⏰ Message TS: {ts}")
        print(f"🔘 Action Buttons: {len(action_buttons)}")
        print(f"🧪 === END MOCK SLACK MESSAGE UPDATE ===")
        
        return {
            "ok": True,
            "ts": ts,
            "message_ts": ts,
            "channel": channel,
            "message": {
                "text": text,
                "blocks": blocks
            }
        }

    def chat_postEphemeral(self, **kwargs):
        """Mock implementation of chat.postEphemeral"""
        channel = kwargs.get("channel", self.channel_id)
        user = kwargs.get("user", "U1234567890")
        text = kwargs.get("text", "")
        blocks = kwargs.get("blocks", [])
        
        # Determine message type for logging
        action_buttons = []
        if blocks:
            for block in blocks:
                if block.get("type") == "actions":
                    action_buttons = block.get("elements", [])
        
        message_type = self._determine_message_type(action_buttons)
        
        print(f"🧪 === MOCK SLACK EPHEMERAL MESSAGE ===")
        print(f"📋 Message Type: {message_type}")
        print(f"📍 Channel: {channel}")
        print(f"👤 User: {user}")
        print(f"🔘 Action Buttons: {len(action_buttons)}")
        print(f"🧪 === END MOCK SLACK EPHEMERAL MESSAGE ===")
        
        return {
            "ok": True,
            "message_ts": "1234567890.123456",
            "channel": channel
        }

    def _determine_message_type(self, action_buttons: List[Dict[str, Any]]) -> str:
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
