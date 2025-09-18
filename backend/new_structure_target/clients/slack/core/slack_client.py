"""
Core Slack API methods.
Handles direct Slack API interactions: sending messages, updating messages, ephemeral messages.
"""

import logging
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientError

if TYPE_CHECKING:
    from .mock_client import MockSlackClient

logger = logging.getLogger(__name__)


class SlackClient:
    """Core Slack API methods for direct API interactions"""

    def __init__(self, client: Union[WebClient, "MockSlackClient"]):
        self.client = client

    def send_message_with_blocks(
        self,
        channel_id: str,
        blocks: List[Dict[str, Any]],
        fallback_text: str = "Message",
        slack_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a message with custom Slack blocks.
        
        Args:
            channel_id: Slack channel ID
            blocks: Slack blocks for rich formatting
            fallback_text: Fallback text for notifications
            slack_text: Optional alternative slack text
            metadata: Optional metadata
            thread_ts: Optional thread timestamp
            
        Returns:
            Dict containing success status and response details
        """
        try:
            # Prepare the message payload
            payload = {
                "channel": channel_id,
                "text": slack_text or fallback_text,
                "blocks": blocks,
            }
            
            # Add optional parameters
            if metadata:
                payload["metadata"] = metadata
            if thread_ts:
                payload["thread_ts"] = thread_ts
            
            # Send the message
            response = self.client.chat_postMessage(**payload)
            
            if response["ok"]:
                logger.info(f"✅ Message with blocks sent to {channel_id}")
                return {
                    "success": True,
                    "message_ts": response["message_ts"],
                    "channel": response["channel"],
                    "response": response
                }
            else:
                logger.error(f"❌ Failed to send message with blocks: {response['error']}")
                return {"success": False, "error": response["error"]}
                
        except Exception as e:
            logger.error(f"💥 Error sending message with blocks to {channel_id}: {e}")
            return {"success": False, "error": str(e)}

    def send_message(
        self,
        channel_id: str,
        message_text: str,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        slack_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a Slack channel.
        
        Args:
            channel_id: Slack channel ID
            message_text: Main message text
            action_buttons: Optional action buttons
            slack_text: Optional fallback text
            metadata: Optional metadata
            thread_ts: Optional thread timestamp
            
        Returns:
            Dict containing success status and response data
        """
        try:
            # Build blocks for the message
            blocks = self._build_message_blocks(message_text, action_buttons)
            
            # Prepare the message payload
            payload = {
                "channel": channel_id,
                "text": slack_text or message_text,
                "blocks": blocks,
            }
            
            # Add optional parameters
            if metadata:
                payload["metadata"] = metadata
            if thread_ts:
                payload["thread_ts"] = thread_ts
            
            # Send the message
            response = self.client.chat_postMessage(**payload)
            
            if response["ok"]:
                logger.info(f"✅ Message sent to {channel_id}")
                return {
                    "success": True,
                    "message_ts": response["message_ts"],
                    "channel": response["channel"],
                    "response": response
                }
            else:
                logger.error(f"❌ Failed to send message: {response.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": response.get("error", "Unknown error"),
                    "response": response
                }
                
        except SlackApiError as e:
            logger.error(f"❌ Slack API error sending message: {e.response['error']}")
            return {
                "success": False,
                "error": f"Slack API error: {e.response['error']}",
                "response": e.response
            }
        except SlackClientError as e:
            logger.error(f"❌ Slack client error sending message: {str(e)}")
            return {
                "success": False,
                "error": f"Slack client error: {str(e)}",
                "response": None
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error sending message: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "response": None
            }

    def update_message(
        self,
        channel_id: str,
        message_ts: str,
        message_text: str,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        slack_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing Slack message.
        
        Args:
            channel_id: Slack channel ID
            message_ts: Message timestamp to update
            message_text: New message text
            action_buttons: Optional new action buttons
            slack_text: Optional fallback text
            metadata: Optional metadata
            
        Returns:
            Dict containing success status and response data
        """
        try:
            # Build blocks for the message
            blocks = self._build_message_blocks(message_text, action_buttons)
            
            # Prepare the update payload
            payload = {
                "channel": channel_id,
                "ts": message_ts,
                "text": slack_text or message_text,
                "blocks": blocks,
            }
            
            # Add optional parameters
            if metadata:
                payload["metadata"] = metadata
            
            # Update the message
            response = self.client.chat_update(**payload)
            
            if response["ok"]:
                logger.info(f"✅ Message updated in {channel_id}")
                return {
                    "success": True,
                    "message_ts": response["message_ts"],
                    "channel": response["channel"],
                    "response": response
                }
            else:
                logger.error(f"❌ Failed to update message: {response.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": response.get("error", "Unknown error"),
                    "response": response
                }
                
        except SlackApiError as e:
            logger.error(f"❌ Slack API error updating message: {e.response['error']}")
            return {
                "success": False,
                "error": f"Slack API error: {e.response['error']}",
                "response": e.response
            }
        except SlackClientError as e:
            logger.error(f"❌ Slack client error updating message: {str(e)}")
            return {
                "success": False,
                "error": f"Slack client error: {str(e)}",
                "response": None
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error updating message: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "response": None
            }

    def send_ephemeral_message(
        self,
        channel_id: str,
        user_id: str,
        message_text: str,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        slack_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an ephemeral message to a user in a channel.
        
        Args:
            channel_id: Slack channel ID
            user_id: Slack user ID
            message_text: Message text
            action_buttons: Optional action buttons
            slack_text: Optional fallback text
            
        Returns:
            Dict containing success status and response data
        """
        try:
            # Build blocks for the message
            blocks = self._build_message_blocks(message_text, action_buttons)
            
            # Prepare the ephemeral message payload
            payload = {
                "channel": channel_id,
                "user": user_id,
                "text": slack_text or message_text,
                "blocks": blocks,
            }
            
            # Send the ephemeral message
            response = self.client.chat_postEphemeral(**payload)
            
            if response["ok"]:
                logger.info(f"✅ Ephemeral message sent to {user_id} in {channel_id}")
                return {
                    "success": True,
                    "message_ts": response["message_ts"],
                    "channel": response["channel"],
                    "response": response
                }
            else:
                logger.error(f"❌ Failed to send ephemeral message: {response.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": response.get("error", "Unknown error"),
                    "response": response
                }
                
        except SlackApiError as e:
            logger.error(f"❌ Slack API error sending ephemeral message: {e.response['error']}")
            return {
                "success": False,
                "error": f"Slack API error: {e.response['error']}",
                "response": e.response
            }
        except SlackClientError as e:
            logger.error(f"❌ Slack client error sending ephemeral message: {str(e)}")
            return {
                "success": False,
                "error": f"Slack client error: {str(e)}",
                "response": None
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error sending ephemeral message: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "response": None
            }

    def _build_message_blocks(self, message_text: str, action_buttons: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Build Slack blocks for a message with optional action buttons"""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message_text
                }
            }
        ]
        
        if action_buttons:
            blocks.append({
                "type": "actions",
                "elements": action_buttons
            })
        
        return blocks
