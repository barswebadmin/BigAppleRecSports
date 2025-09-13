"""
Slack API client utilities.
Handles the low-level Slack API communication.
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


class MockSlackApiClient:
    """Mock Slack API client for testing purposes."""

    def __init__(self, bearer_token: str, channel_id: str):
        self.bearer_token = bearer_token
        self.channel_id = channel_id
        logger.info("🧪 Using MockSlackApiClient - no real Slack requests will be made")

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

    def send_message(
        self,
        message_text: str,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        slack_text: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Mock send_message that logs but doesn't make real requests"""
        message_type = self._determine_message_type(action_buttons)
        logger.info(
            f"🧪 MOCK SENDING SLACK MESSAGE: {message_type} to {self.channel_id}"
        )
        print("\n🧪 === MOCK SLACK MESSAGE SEND ===")
        print(f"📋 Message Type: {message_type}")
        print(f"📍 Channel: {self.channel_id}")
        print(f"🔘 Action Buttons: {len(action_buttons) if action_buttons else 0}")
        print("🧪 === END MOCK SLACK MESSAGE SEND ===\n")

        return {
            "success": True,
            "message": "Mock message sent successfully",
            "ts": "1234567890.123456",
            "channel": self.channel_id,
            "slack_response": {"ok": True, "ts": "1234567890.123456"},
        }

    def update_message(
        self,
        message_ts: str,
        message_text: str,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        slack_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mock update_message that logs but doesn't make real requests"""
        message_type = self._determine_message_type(action_buttons)
        logger.info(
            f"🧪 MOCK UPDATING SLACK MESSAGE: {message_type} (ts: {message_ts}) in {self.channel_id}"
        )
        print("\n🧪 === MOCK SLACK MESSAGE UPDATE ===")
        print(f"📋 Message Type: {message_type}")
        print(f"📍 Channel: {self.channel_id}")
        print(f"🆔 Message TS: {message_ts}")
        print(f"🔘 Action Buttons: {len(action_buttons) if action_buttons else 0}")
        print("🧪 === END MOCK SLACK MESSAGE UPDATE ===\n")

        return {
            "success": True,
            "message": "Mock message updated successfully",
            "ts": message_ts,
            "channel": self.channel_id,
        }

    def send_ephemeral_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Mock send_ephemeral_message that logs but doesn't make real requests"""
        user_id = payload.get("user", "unknown")
        channel_id = payload.get("channel", "unknown")
        logger.info(
            f"🧪 MOCK: Would send ephemeral message to user {user_id} in channel {channel_id}"
        )

        return {
            "success": True,
            "message": "Mock ephemeral message sent successfully",
            "slack_response": {"ok": True},
        }

    def send_modal(self, trigger_id: str, modal_view: Dict[str, Any]) -> Dict[str, Any]:
        """Mock send_modal that logs but doesn't make real requests"""
        logger.info(
            f"🧪 MockSlackApiClient - Would open modal with trigger_id {trigger_id}"
        )
        logger.debug(
            f"🧪 Modal content: {modal_view.get('title', {}).get('text', 'Unknown title')}"
        )
        return {
            "success": True,
            "message": "Mock modal opened",
            "view_id": "mock.view.123",
        }

    def _create_standard_blocks(
        self, text: str, action_buttons: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Create standard Slack message blocks (mock version)"""
        blocks = [
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        ]

        # Add action buttons if provided
        if action_buttons:
            # Remove any None buttons and ensure we have a valid list
            filtered_buttons = [btn for btn in action_buttons if btn is not None]
            if filtered_buttons:  # Only add actions if we have valid buttons
                blocks.append({"type": "actions", "elements": filtered_buttons})

        blocks.append({"type": "divider"})
        return blocks


class SlackApiClient:
    """Helper class for Slack API communication."""

    def __init__(self, bearer_token: str, channel_id: str):
        self.bearer_token = bearer_token
        self.channel_id = channel_id
        self.base_url = "https://slack.com/api"

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

    def send_message(
        self,
        message_text: str,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        slack_text: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to the configured Slack channel with optional action buttons

        Args:
            message_text: The message content to send
            action_buttons: Optional list of action buttons to include
            slack_text: Optional short text for notifications

        Returns:
            Dict containing success status and details
        """
        # FIX: Ensure SSL certificates are properly configured for Render (Ubuntu)
        # Only set Ubuntu SSL paths if we're in a production/cloud environment
        import os

        if os.getenv("ENVIRONMENT") == "production" and not os.path.exists(
            "/opt/homebrew"
        ):
            if not os.getenv("SSL_CERT_FILE") or not os.path.exists(
                os.getenv("SSL_CERT_FILE", "")
            ):
                os.environ["SSL_CERT_FILE"] = "/etc/ssl/certs/ca-certificates.crt"
            if not os.getenv("REQUESTS_CA_BUNDLE") or not os.path.exists(
                os.getenv("REQUESTS_CA_BUNDLE", "")
            ):
                os.environ["REQUESTS_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"
            if not os.getenv("CURL_CA_BUNDLE") or not os.path.exists(
                os.getenv("CURL_CA_BUNDLE", "")
            ):
                os.environ["CURL_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"

        if not self.bearer_token:
            logger.error("No Slack bearer token configured")
            return {"success": False, "error": "No Slack bearer token configured"}

        try:
            # Prepare the request
            url = f"{self.base_url}/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json",
            }

            # Create blocks structure for rich formatting
            blocks = self._create_standard_blocks(message_text, action_buttons)

            payload = {
                "channel": self.channel_id,
                "text": slack_text or message_text,  # Fallback text for notifications
                "blocks": blocks,
                "unfurl_links": False,
                "unfurl_media": False,
            }

            # Add metadata if provided (Slack stores this in the message)
            if metadata:
                payload["metadata"] = {
                    "event_type": "refund_request",
                    "event_payload": metadata,
                }

            # Determine message type based on action buttons
            message_type = self._determine_message_type(action_buttons)
            logger.info(
                f"📤 SENDING SLACK MESSAGE: {message_type} to channel {self.channel_id}"
            )
            print("\n📤 === SLACK MESSAGE SEND ===")
            print(f"📋 Message Type: {message_type}")
            print(f"📍 Channel: {self.channel_id}")
            print(f"🔘 Action Buttons: {len(action_buttons) if action_buttons else 0}")
            print("📤 === END SLACK MESSAGE SEND ===\n")

            # Send the request with explicit SSL certificate bundle
            cert_bundle = (
                "/etc/ssl/certs/ca-certificates.crt"
                if os.getenv("ENVIRONMENT") == "production"
                else True
            )

            try:
                response = requests.post(
                    url, headers=headers, data=json.dumps(payload), verify=cert_bundle
                )
                response_data = response.json()
            except requests.exceptions.SSLError as ssl_error:
                logger.warning(
                    f"SSL Error with Slack API - trying with system default: {ssl_error}"
                )
                # Fallback: try with system default SSL verification
                response = requests.post(
                    url, headers=headers, data=json.dumps(payload), verify=True
                )
                response_data = response.json()

            if response.status_code == 200 and response_data.get("ok"):
                logger.info("Slack message sent successfully")
                return {
                    "success": True,
                    "message": "Message sent successfully",
                    "ts": response_data.get("ts"),
                    "channel": response_data.get("channel"),
                    "slack_response": response_data,
                }
            else:
                error_msg = response_data.get("error", "Unknown error")
                logger.error(f"Slack API error: {error_msg}")
                return {
                    "success": False,
                    "error": f"Slack API error: {error_msg}",
                    "slack_response": response_data,
                }

        except requests.RequestException as e:
            logger.error(f"Request error sending Slack message: {str(e)}")
            return {"success": False, "error": f"Request error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error sending Slack message: {str(e)}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def update_message(
        self,
        message_ts: str,
        message_text: str,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        slack_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing Slack message

        Args:
            message_ts: Timestamp of the message to update
            message_text: New message content
            action_buttons: Optional list of action buttons to include
            slack_text: Optional short text for notifications

        Returns:
            Dict containing success status and details
        """
        if not self.bearer_token:
            logger.error("No Slack bearer token configured")
            return {"success": False, "error": "No Slack bearer token configured"}

        try:
            url = f"{self.base_url}/chat.update"
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json",
            }

            # Create blocks structure for rich formatting
            blocks = self._create_standard_blocks(message_text, action_buttons)

            # 🐛 DEBUG: Print blocks for Slack Block Kit Builder testing
            print("\n🔍 === SLACK BLOCKS DEBUG ===")
            print(f"📝 Message text length: {len(message_text)}")
            print(
                f"🔘 Number of action buttons: {len(action_buttons) if action_buttons else 0}"
            )
            print(f"📦 Number of blocks: {len(blocks)}")
            print("🧱 Raw blocks JSON for Block Kit Builder:")
            import json

            print(json.dumps(blocks, indent=2))
            print("=== END SLACK BLOCKS DEBUG ===\n")

            payload = {
                "channel": self.channel_id,
                "ts": message_ts,
                "text": slack_text or message_text,  # Fallback text for notifications
                "blocks": blocks,
            }

            # Determine message type based on action buttons
            message_type = self._determine_message_type(action_buttons)
            logger.info(
                f"🔄 UPDATING SLACK MESSAGE: {message_type} (ts: {message_ts}) in channel {self.channel_id}"
            )
            print("\n🔄 === SLACK MESSAGE UPDATE ===")
            print(f"📋 Message Type: {message_type}")
            print(f"📍 Channel: {self.channel_id}")
            print(f"🆔 Message TS: {message_ts}")
            print(f"🔘 Action Buttons: {len(action_buttons) if action_buttons else 0}")
            print("🔄 === END SLACK MESSAGE UPDATE ===\n")

            # Use explicit SSL certificate bundle
            cert_bundle = (
                "/etc/ssl/certs/ca-certificates.crt"
                if os.getenv("ENVIRONMENT") == "production"
                else True
            )

            try:
                response = requests.post(
                    url, headers=headers, data=json.dumps(payload), verify=cert_bundle
                )
                response_data = response.json()
            except requests.exceptions.SSLError as ssl_error:
                logger.warning(
                    f"SSL Error with Slack API update - trying with system default: {ssl_error}"
                )
                # Fallback: try with system default SSL verification
                response = requests.post(
                    url, headers=headers, data=json.dumps(payload), verify=True
                )
                response_data = response.json()

            if response.status_code == 200 and response_data.get("ok"):
                logger.info("Slack message updated successfully")
                return {
                    "success": True,
                    "message": "Message updated successfully",
                    "ts": response_data.get("ts"),
                    "slack_response": response_data,
                }
            else:
                error_msg = response_data.get("error", "Unknown error")
                logger.error(f"Slack update error: {error_msg}")
                return {
                    "success": False,
                    "error": f"Slack update error: {error_msg}",
                    "slack_response": response_data,
                }

        except Exception as e:
            logger.error(f"Error updating Slack message: {str(e)}")
            return {"success": False, "error": f"Update error: {str(e)}"}

    def send_ephemeral_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send an ephemeral message to a specific user in a channel.

        Args:
            payload: Dictionary containing 'user' and 'channel' keys.

        Returns:
            Dict containing success status and details.
        """
        if not self.bearer_token:
            logger.error("No Slack bearer token configured")
            return {"success": False, "error": "No Slack bearer token configured"}

        try:
            url = f"{self.base_url}/chat.postEphemeral"
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json",
            }

            request_payload = {
                "channel": payload.get("channel"),
                "user": payload.get("user"),
                "text": payload.get("text", ""),
                "blocks": payload.get("blocks", []),
            }

            logger.info(
                f"Sending ephemeral message to user {request_payload['user']} in channel {request_payload['channel']}"
            )
            logger.debug(
                f"Ephemeral message content: {request_payload['text'][:100]}..."
            )

            # Use explicit SSL certificate bundle
            cert_bundle = (
                "/etc/ssl/certs/ca-certificates.crt"
                if os.getenv("ENVIRONMENT") == "production"
                else True
            )

            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(request_payload),
                verify=cert_bundle,
            )
            response_data = response.json()

            if response.status_code == 200 and response_data.get("ok"):
                logger.info("Ephemeral message sent successfully")
                return {
                    "success": True,
                    "message": "Ephemeral message sent successfully",
                    "slack_response": response_data,
                }
            else:
                error_msg = response_data.get("error", "Unknown error")
                logger.error(f"Slack ephemeral message error: {error_msg}")
                return {
                    "success": False,
                    "error": f"Slack ephemeral message error: {error_msg}",
                    "slack_response": response_data,
                }

        except requests.RequestException as e:
            logger.error(f"Request error sending ephemeral message: {str(e)}")
            return {"success": False, "error": f"Request error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error sending ephemeral message: {str(e)}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def send_modal(self, trigger_id: str, modal_view: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a modal dialog to a specific user.

        Args:
            trigger_id: The ID of the interaction that triggered the modal.
            modal_view: The modal view definition.

        Returns:
            Dict containing success status and details.
        """
        if not self.bearer_token:
            logger.error("No Slack bearer token configured")
            return {"success": False, "error": "No Slack bearer token configured"}

        try:
            url = f"{self.base_url}/views.open"
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json",
            }

            payload = {"trigger_id": trigger_id, "view": modal_view}

            logger.info(f"Sending modal dialog to user with trigger_id {trigger_id}")
            logger.debug(
                f"Modal content: {modal_view.get('title', {}).get('text', 'Unknown title')}"
            )

            # Send the request with explicit SSL certificate bundle
            cert_bundle = (
                "/etc/ssl/certs/ca-certificates.crt"
                if os.getenv("ENVIRONMENT") == "production"
                else True
            )

            try:
                response = requests.post(
                    url, headers=headers, data=json.dumps(payload), verify=cert_bundle
                )
                response_data = response.json()
            except requests.exceptions.SSLError as ssl_error:
                logger.warning(
                    f"SSL Error with Slack API - trying with system default: {ssl_error}"
                )
                # Fallback: try with system default SSL verification
                response = requests.post(
                    url, headers=headers, data=json.dumps(payload), verify=True
                )
                response_data = response.json()

            # Debug: Log full response details
            logger.info(f"Slack API Response - Status: {response.status_code}")
            logger.info(f"Slack API Response - Headers: {dict(response.headers)}")
            logger.info(f"Slack API Response - Body: {response_data}")

            if response.status_code == 200 and response_data.get("ok"):
                logger.info("Modal dialog sent successfully")
                return {
                    "success": True,
                    "message": "Modal dialog sent successfully",
                    "slack_response": response_data,
                }
            else:
                error_msg = response_data.get(
                    "error", f"Unknown error - Status: {response.status_code}"
                )
                error_details = response_data.get("response_metadata", {})
                logger.error(f"Slack modal dialog error: {error_msg}")
                logger.error(f"Slack error details: {error_details}")
                return {
                    "success": False,
                    "error": f"Slack modal dialog error: {error_msg}",
                    "slack_response": response_data,
                }

        except requests.RequestException as e:
            logger.error(f"Request error sending modal dialog: {str(e)}")
            return {"success": False, "error": f"Request error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error sending modal dialog: {str(e)}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def _create_standard_blocks(
        self, text: str, action_buttons: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Create standard Slack message blocks matching the old implementation"""
        blocks = [
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        ]

        # Add action buttons if provided
        if action_buttons:
            # Remove any None buttons and ensure we have a valid list
            filtered_buttons = [btn for btn in action_buttons if btn is not None]
            if filtered_buttons:  # Only add actions if we have valid buttons
                blocks.append({"type": "actions", "elements": filtered_buttons})

        blocks.append({"type": "divider"})
        return blocks
