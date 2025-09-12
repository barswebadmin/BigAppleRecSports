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

    def send_message(
        self,
        message_text: str,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        slack_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mock send_message that logs but doesn't make real requests"""
        logger.info(f"🧪 MOCK: Would send Slack message to {self.channel_id}")
        logger.debug(f"🧪 MOCK: Message content: {message_text[:100]}...")

        # 🐛 DEBUG: Print blocks for testing even in mock mode
        blocks = self._create_standard_blocks(message_text, action_buttons)
        print("\n🔍 === MOCK SLACK BLOCKS DEBUG (SEND) ===")
        print(f"📝 Message text length: {len(message_text)}")
        print(
            f"🔘 Number of action buttons: {len(action_buttons) if action_buttons else 0}"
        )
        print(f"📦 Number of blocks: {len(blocks)}")
        print("🧱 Raw blocks JSON for Block Kit Builder:")
        import json

        print(json.dumps(blocks, indent=2))
        print("=== END MOCK SLACK BLOCKS DEBUG (SEND) ===\n")

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
        logger.info(
            f"🧪 MOCK: Would update Slack message {message_ts} in {self.channel_id}"
        )

        # 🐛 DEBUG: Print blocks for testing even in mock mode
        blocks = self._create_standard_blocks(message_text, action_buttons)
        print("\n🔍 === MOCK SLACK BLOCKS DEBUG (UPDATE) ===")
        print(f"📝 Message text length: {len(message_text)}")
        print(
            f"🔘 Number of action buttons: {len(action_buttons) if action_buttons else 0}"
        )
        print(f"📦 Number of blocks: {len(blocks)}")
        print("🧱 Raw blocks JSON for Block Kit Builder:")
        import json

        print(json.dumps(blocks, indent=2))
        print("=== END MOCK SLACK BLOCKS DEBUG (UPDATE) ===\n")

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

    def send_message(
        self,
        message_text: str,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        slack_text: Optional[str] = None,
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

            # 🐛 DEBUG: Print blocks for Slack Block Kit Builder testing
            print("\n🔍 === SLACK BLOCKS DEBUG (SEND) ===")
            print(f"📝 Message text length: {len(message_text)}")
            print(
                f"🔘 Number of action buttons: {len(action_buttons) if action_buttons else 0}"
            )
            print(f"📦 Number of blocks: {len(blocks)}")
            print("🧱 Raw blocks JSON for Block Kit Builder:")
            import json

            print(json.dumps(blocks, indent=2))
            print("=== END SLACK BLOCKS DEBUG (SEND) ===\n")

            payload = {
                "channel": self.channel_id,
                "text": slack_text or message_text,  # Fallback text for notifications
                "blocks": blocks,
                "unfurl_links": False,
                "unfurl_media": False,
            }

            logger.info(f"Sending Slack message to channel {self.channel_id}")
            logger.debug(f"Message content: {message_text[:100]}...")

            # Send the request
            try:
                response = requests.post(
                    url, headers=headers, data=json.dumps(payload), verify=True
                )
                response_data = response.json()
            except requests.exceptions.SSLError as ssl_error:
                logger.warning(
                    f"SSL Error with Slack API - trying without verification: {ssl_error}"
                )
                # Fallback: try without SSL verification (for development)
                response = requests.post(
                    url, headers=headers, data=json.dumps(payload), verify=False
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

            try:
                response = requests.post(
                    url, headers=headers, data=json.dumps(payload), verify=True
                )
                response_data = response.json()
            except requests.exceptions.SSLError as ssl_error:
                logger.warning(
                    f"SSL Error with Slack API update - trying without verification: {ssl_error}"
                )
                # Fallback: try without SSL verification (for development)
                response = requests.post(
                    url, headers=headers, data=json.dumps(payload), verify=False
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

            response = requests.post(
                url, headers=headers, data=json.dumps(request_payload)
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

            # Send the request with SSL verification fallback
            try:
                response = requests.post(
                    url, headers=headers, data=json.dumps(payload), verify=True
                )
                response_data = response.json()
            except requests.exceptions.SSLError as ssl_error:
                logger.warning(
                    f"SSL Error with Slack API - trying without verification: {ssl_error}"
                )
                # Fallback: try without SSL verification (for development)
                response = requests.post(
                    url, headers=headers, data=json.dumps(payload), verify=False
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
