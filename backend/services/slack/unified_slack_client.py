"""
Unified Slack Client - Single point of entry for all Slack API operations.

This replaces the fragmented approach of multiple API clients, dynamic clients,
and inconsistent call patterns with a single, configurable interface.

DESIGN PRINCIPLES:
1. Single method for sending messages with all parameters explicit
2. Single method for updating messages with all parameters explicit
3. Automatic SSL certificate handling based on environment
4. Automatic mock/real client switching based on test mode
5. Consistent error handling and logging across all operations
6. Clear separation of concerns: this handles API calls, not message building
"""

import requests
import json
import sys
import os
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


def _is_test_mode() -> bool:
    """
    Detect if we're running in test mode.
    Returns True if pytest is running or if TESTING environment variable is set.
    """
    # Check if pytest is running
    if "pytest" in sys.modules:
        return True

    # Check if we're running via pytest command
    if any("pytest" in arg for arg in sys.argv):
        return True

    # Check for explicit TESTING environment variable
    if os.getenv("TESTING", "").lower() in ("true", "1", "yes"):
        return True

    # Check if we're running test files
    if any("test_" in arg or arg.endswith("_test.py") for arg in sys.argv):
        return True

    return False


class UnifiedSlackClient:
    """
    Unified Slack API client that handles all Slack operations consistently.

    This replaces the fragmented SlackApiClient/MockSlackApiClient pattern
    with a single interface that automatically handles:
    - Test mode vs production mode
    - SSL certificate configuration
    - Error handling and retries
    - Consistent logging and debugging
    """

    def __init__(self):
        self.base_url = "https://slack.com/api"
        self.is_test_mode = _is_test_mode()

        # Configure SSL certificate handling based on environment
        self.ssl_cert_bundle = (
            "/etc/ssl/certs/ca-certificates.crt"
            if os.getenv("ENVIRONMENT") == "production"
            else True
        )

        logger.info(
            f"🔧 UnifiedSlackClient initialized - test_mode={self.is_test_mode}, "
            f"ssl_bundle={'production_path' if self.ssl_cert_bundle is not True else 'system_default'}"
        )

    def _determine_message_type(
        self, action_buttons: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Determine the message type and workflow step based on action buttons"""
        if not action_buttons:
            return "STEP 4: Final Completion Message (No Buttons)"

        # Extract action IDs from buttons
        action_ids = []
        for button in action_buttons:
            if isinstance(button, dict) and "action_id" in button:
                action_ids.append(button["action_id"])

        # Determine workflow step based on button combinations
        if "cancel_order" in action_ids and "proceed_without_cancel" in action_ids:
            return "STEP 1: Initial Refund Request (Cancel/Proceed/Deny)"
        elif "process_refund" in action_ids and "custom_refund_amount" in action_ids:
            return "STEP 2: Refund Decision (Process/Custom/No Refund)"
        elif any("restock" in action_id for action_id in action_ids):
            return "STEP 3: Inventory Decision (Restock/Don't Restock)"
        elif "edit_request_details" in action_ids:
            return "ERROR: Email Mismatch (Edit Details/Deny)"
        elif "deny_duplicate_refund_request" in action_ids:
            return "ERROR: Duplicate Refund Request (Update/Deny)"
        else:
            return f"UNKNOWN: Action IDs {action_ids}"

    def _create_standard_blocks(
        self, text: str, action_buttons: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Create standard Slack Block Kit structure"""
        blocks = [{"type": "divider"}]

        # Add main content block
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text}})

        # Add action buttons if provided
        if action_buttons:
            blocks.append({"type": "actions", "elements": action_buttons})

        blocks.append({"type": "divider"})
        return blocks

    def _make_slack_request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        bearer_token: str,
        operation_name: str = "Slack API call",
    ) -> Dict[str, Any]:
        """
        Make a Slack API request with consistent error handling and SSL configuration.

        Args:
            endpoint: Slack API endpoint (e.g., 'chat.postMessage')
            payload: Request payload
            bearer_token: Slack bot token
            operation_name: Human-readable operation name for logging

        Returns:
            Dict with 'success', 'error', and response data
        """
        if not bearer_token:
            return {"success": False, "error": "No Slack bearer token provided"}

        try:
            url = f"{self.base_url}/{endpoint}"
            headers = {
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json",
            }

            logger.info(f"🔗 Making {operation_name} to {endpoint}")

            try:
                response = requests.post(
                    url,
                    headers=headers,
                    data=json.dumps(payload),
                    verify=self.ssl_cert_bundle,
                )
                response_data = response.json()
            except requests.exceptions.SSLError as ssl_error:
                logger.warning(
                    f"SSL Error with {operation_name} - trying with system default: {ssl_error}"
                )
                # Fallback: try with system default SSL verification
                response = requests.post(
                    url, headers=headers, data=json.dumps(payload), verify=True
                )
                response_data = response.json()

            if response.status_code == 200 and response_data.get("ok"):
                logger.info(f"✅ {operation_name} successful")
                return {
                    "success": True,
                    "message": f"{operation_name} successful",
                    "slack_response": response_data,
                    "ts": response_data.get("ts"),
                    "channel": response_data.get("channel"),
                }
            else:
                error_msg = response_data.get("error", "Unknown error")
                logger.error(f"❌ {operation_name} failed: {error_msg}")
                return {
                    "success": False,
                    "error": f"Slack API error: {error_msg}",
                    "slack_response": response_data,
                }

        except requests.RequestException as e:
            logger.error(f"❌ Request error in {operation_name}: {str(e)}")
            return {"success": False, "error": f"Request error: {str(e)}"}
        except Exception as e:
            logger.error(f"❌ Unexpected error in {operation_name}: {str(e)}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def send_message(
        self,
        channel_id: str,
        bearer_token: str,
        message_text: str,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        slack_text: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a Slack message with explicit parameters.

        Args:
            channel_id: Slack channel ID (e.g., 'C092RU7R6PL')
            bearer_token: Slack bot token
            message_text: Main message content (markdown supported)
            action_buttons: Optional list of action button dictionaries
            slack_text: Optional fallback text for notifications
            metadata: Optional metadata to attach to message
            thread_ts: Optional thread timestamp to reply in thread

        Returns:
            Dict with 'success', 'error', 'ts', 'channel', and 'slack_response'
        """
        # Handle test mode
        if self.is_test_mode:
            message_type = self._determine_message_type(action_buttons)
            logger.info(
                f"🧪 MOCK SENDING SLACK MESSAGE: {message_type} to {channel_id}"
            )
            print("\n🧪 === MOCK SLACK MESSAGE SEND ===")
            print(f"📋 Message Type: {message_type}")
            print(f"📍 Channel: {channel_id}")
            print(f"🔘 Action Buttons: {len(action_buttons) if action_buttons else 0}")
            print(f"🧵 Thread: {thread_ts or 'None'}")
            print("🧪 === END MOCK SLACK MESSAGE SEND ===\n")

            return {
                "success": True,
                "message": "Mock message sent successfully",
                "ts": "1234567890.123456",
                "channel": channel_id,
                "slack_response": {"ok": True, "ts": "1234567890.123456"},
            }

        # Create blocks structure for rich formatting
        blocks = self._create_standard_blocks(message_text, action_buttons)

        payload = {
            "channel": channel_id,
            "text": slack_text or message_text,  # Fallback text for notifications
            "blocks": blocks,
            "unfurl_links": False,
            "unfurl_media": False,
        }

        # Add thread timestamp if provided
        if thread_ts:
            payload["thread_ts"] = thread_ts

        # Add metadata if provided (Slack stores this in the message)
        if metadata:
            payload["metadata"] = {
                "event_type": "refund_request",
                "event_payload": metadata,
            }

        # Log message details for debugging
        message_type = self._determine_message_type(action_buttons)
        logger.info(f"📤 SENDING SLACK MESSAGE: {message_type} to channel {channel_id}")
        print("\n📤 === SLACK MESSAGE SEND ===")
        print(f"📋 Message Type: {message_type}")
        print(f"📍 Channel: {channel_id}")
        print(f"🔘 Action Buttons: {len(action_buttons) if action_buttons else 0}")
        print(f"🧵 Thread: {thread_ts or 'None'}")
        print("📤 === END SLACK MESSAGE SEND ===\n")

        return self._make_slack_request(
            endpoint="chat.postMessage",
            payload=payload,
            bearer_token=bearer_token,
            operation_name="Send Slack Message",
        )

    def update_message(
        self,
        channel_id: str,
        bearer_token: str,
        message_ts: str,
        message_text: str,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        slack_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing Slack message with explicit parameters.

        Args:
            channel_id: Slack channel ID (e.g., 'C092RU7R6PL')
            bearer_token: Slack bot token
            message_ts: Timestamp of message to update
            message_text: New message content (markdown supported)
            action_buttons: Optional list of action button dictionaries
            slack_text: Optional fallback text for notifications

        Returns:
            Dict with 'success', 'error', 'ts', 'channel', and 'slack_response'
        """
        # Handle test mode
        if self.is_test_mode:
            message_type = self._determine_message_type(action_buttons)
            logger.info(
                f"🧪 MOCK UPDATING SLACK MESSAGE: {message_type} (ts: {message_ts}) in channel {channel_id}"
            )
            print("\n🧪 === MOCK SLACK MESSAGE UPDATE ===")
            print(f"📋 Message Type: {message_type}")
            print(f"📍 Channel: {channel_id}")
            print(f"🆔 Message TS: {message_ts}")
            print(f"🔘 Action Buttons: {len(action_buttons) if action_buttons else 0}")
            print("🧪 === END MOCK SLACK MESSAGE UPDATE ===\n")

            return {
                "success": True,
                "message": "Mock message updated successfully",
                "ts": message_ts,
                "channel": channel_id,
                "slack_response": {"ok": True, "ts": message_ts},
            }

        # Create blocks structure for rich formatting
        blocks = self._create_standard_blocks(message_text, action_buttons)

        payload = {
            "channel": channel_id,
            "ts": message_ts,
            "text": slack_text or message_text,  # Fallback text for notifications
            "blocks": blocks,
        }

        # Log message details for debugging
        message_type = self._determine_message_type(action_buttons)
        logger.info(
            f"🔄 UPDATING SLACK MESSAGE: {message_type} (ts: {message_ts}) in channel {channel_id}"
        )
        print("\n🔄 === SLACK MESSAGE UPDATE ===")
        print(f"📋 Message Type: {message_type}")
        print(f"📍 Channel: {channel_id}")
        print(f"🆔 Message TS: {message_ts}")
        print(f"🔘 Action Buttons: {len(action_buttons) if action_buttons else 0}")
        print("🔄 === END SLACK MESSAGE UPDATE ===\n")

        return self._make_slack_request(
            endpoint="chat.update",
            payload=payload,
            bearer_token=bearer_token,
            operation_name="Update Slack Message",
        )

    def send_modal(
        self,
        trigger_id: str,
        bearer_token: str,
        modal_view: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Open a Slack modal with explicit parameters.

        Args:
            trigger_id: Slack trigger ID from interaction
            bearer_token: Slack bot token
            modal_view: Modal view definition

        Returns:
            Dict with 'success', 'error', and 'slack_response'
        """
        # Handle test mode
        if self.is_test_mode:
            logger.info(f"🧪 MOCK OPENING SLACK MODAL with trigger {trigger_id}")
            print("\n🧪 === MOCK SLACK MODAL OPEN ===")
            print(f"🎯 Trigger ID: {trigger_id}")
            print(
                f"📋 Modal Title: {modal_view.get('title', {}).get('text', 'Unknown')}"
            )
            print("🧪 === END MOCK SLACK MODAL OPEN ===\n")

            return {
                "success": True,
                "message": "Mock modal opened successfully",
                "slack_response": {"ok": True},
            }

        payload = {
            "trigger_id": trigger_id,
            "view": modal_view,
        }

        logger.info(f"📋 OPENING SLACK MODAL with trigger {trigger_id}")
        print("\n📋 === SLACK MODAL OPEN ===")
        print(f"🎯 Trigger ID: {trigger_id}")
        print(f"📋 Modal Title: {modal_view.get('title', {}).get('text', 'Unknown')}")
        print("📋 === END SLACK MODAL OPEN ===\n")

        return self._make_slack_request(
            endpoint="views.open",
            payload=payload,
            bearer_token=bearer_token,
            operation_name="Open Slack Modal",
        )


# Global singleton instance
slack_client = UnifiedSlackClient()
