"""
Core Slack API methods.
Handles direct Slack API interactions: sending messages, updating messages, ephemeral messages.
"""

import logging
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientError

from config import config

if TYPE_CHECKING:
    from .mock_client import MockSlackClient

logger = logging.getLogger(__name__)


class SlackClient():
    """Core Slack API methods for direct API interactions"""
    
    def __init__(self):
        self.config = config.slack
        self.web_client = WebClient()
        self.client = self.web_client
        self._timeout_seconds = 10
        self._max_retries = 3

    def send_message(
        self,
        channel: "config.slack.Channels._Channel",
        bot: "config.slack.Bots._Bot",
        blocks: List[Dict[str, Any]],
        action_buttons: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a Slack channel (blocks required).
        
        Args:
            channel: Slack channel
            bot: Slack bot (to get its token)
            blocks: Slack blocks for rich formatting
            action_buttons: Optional action buttons
            metadata: Optional metadata
            thread_ts: Optional thread timestamp
            
        Returns:
            Dict containing success status and response data
        """
        try:
            # Optionally append action buttons
            if action_buttons:
                blocks = blocks + [{"type": "actions", "elements": action_buttons}]
            
            # Prepare the message payload
            payload = {
                "channel": channel.id,
                "token": bot.token,
                "blocks": blocks,
            }
            
            # Add optional parameters
            if metadata:
                payload["metadata"] = metadata
            if thread_ts:
                payload["thread_ts"] = thread_ts
            
            # Send the message
            # Retry wrapper for unexpected responses
            last_error = None
            for _ in range(self._max_retries):
                try:
                    response = self.client.chat_postMessage(**payload, timeout=self._timeout_seconds)
                    break
                except Exception as e:
                    last_error = e
            else:
                return {"success": False, "error": f"Unexpected error: {str(last_error)}", "response": None}
            
            if response["ok"]:
                logger.info(f"✅ Message sent to {channel.name}")
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
        channel: "config.slack.Channels._Channel",
        bot: "config.slack.Bots._Bot",
        message_ts: str,
        message_text_short: str = "Fallback Short Message",
        message_text: str = "Fallback Message",
        action_buttons: Optional[List[Dict[str, Any]]] = None,
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
                "channel": channel.id,
                "token": bot.token,
                "ts": message_ts,
                "text": message_text_short or message_text,
                "blocks": blocks,
            }
            
            # Add optional parameters
            if metadata:
                payload["metadata"] = metadata
            
            # Update the message
            last_error = None
            for _ in range(self._max_retries):
                try:
                    response = self.client.chat_update(**payload, timeout=self._timeout_seconds)
                    break
                except Exception as e:
                    last_error = e
            else:
                return {"success": False, "error": f"Unexpected error: {str(last_error)}", "response": None}
            
            if response["ok"]:
                logger.info(f"✅ Message updated in {channel.name}")
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

    def update_message_blocks(
        self,
        channel: "config.slack.Channels._Channel",
        bot: "config.slack.Bots._Bot",
        message_ts: str,
        blocks: List[Dict[str, Any]],
        *,
        metadata: Optional[Dict[str, Any]] = None,
        text_fallback: str = "Updated message",
    ) -> Dict[str, Any]:
        """Update an existing message using pre-built blocks (preferred)."""
        try:
            payload = {
                "channel": channel.id,
                "token": bot.token,
                "ts": message_ts,
                "text": text_fallback,
                "blocks": blocks,
            }
            if metadata:
                payload["metadata"] = metadata

            last_error = None
            for _ in range(self._max_retries):
                try:
                    response = self.client.chat_update(**payload, timeout=self._timeout_seconds)
                    break
                except Exception as e:
                    last_error = e
            else:
                return {"success": False, "error": f"Unexpected error: {str(last_error)}", "response": None}
            if response["ok"]:
                logger.info(f"✅ Message updated in {channel.name}")
                return {"success": True, "message_ts": response["message_ts"], "channel": response["channel"], "response": response}
            return {"success": False, "error": response.get("error", "Unknown error"), "response": response}
        except SlackApiError as e:
            logger.error(f"❌ Slack API error updating message: {e.response['error']}")
            return {"success": False, "error": f"Slack API error: {e.response['error']}", "response": e.response}
        except SlackClientError as e:
            logger.error(f"❌ Slack client error updating message: {str(e)}")
            return {"success": False, "error": f"Slack client error: {str(e)}", "response": None}
        except Exception as e:
            logger.error(f"❌ Unexpected error updating message: {str(e)}")
            return {"success": False, "error": f"Unexpected error: {str(e)}", "response": None}

    def send_ephemeral_message(
        self,
        user: "config.slack.Users._User",
        bot: "config.slack.Bots._Bot",
        message_text_short: str = "Fallback Short Message",
        message_text: str = "Fallback Message",
        channel: Optional["config.slack.Channels._Channel"] = None,
        action_buttons: Optional[List[Dict[str, Any]]] = None,
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
            if not channel:
                raise ValueError("channel is required for ephemeral messages")
            payload = {
                "channel": channel.id,
                "user": user.id,
                "text": message_text or message_text_short,
                "blocks": blocks,
            }
            
            # Send the ephemeral message
            last_error = None
            for _ in range(self._max_retries):
                try:
                    response = self.client.chat_postEphemeral(**payload, timeout=self._timeout_seconds)
                    break
                except Exception as e:
                    last_error = e
            else:
                return {"success": False, "error": f"Unexpected error: {str(last_error)}", "response": None}
            
            if response["ok"]:
                logger.info(f"✅ Ephemeral message sent to {user.name} in {channel.name}")
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

    def send_ephemeral_blocks(
        self,
        user: "config.slack.Users._User",
        bot: "config.slack.Bots._Bot",
        channel: "config.slack.Channels._Channel",
        blocks: List[Dict[str, Any]],
        *,
        text_fallback: str = "Ephemeral message",
    ) -> Dict[str, Any]:
        """Send an ephemeral message using pre-built blocks (preferred)."""
        try:
            payload = {
                "channel": channel.id,
                "user": user.id,
                "text": text_fallback,
                "blocks": blocks,
            }
            last_error = None
            for _ in range(self._max_retries):
                try:
                    response = self.client.chat_postEphemeral(**payload, timeout=self._timeout_seconds)
                    break
                except Exception as e:
                    last_error = e
            else:
                return {"success": False, "error": f"Unexpected error: {str(last_error)}", "response": None}
            if response["ok"]:
                logger.info(f"✅ Ephemeral message sent to {user.name} in {channel.name}")
                return {"success": True, "message_ts": response.get("message_ts"), "channel": response["channel"], "response": response}
            return {"success": False, "error": response.get("error", "Unknown error"), "response": response}
        except SlackApiError as e:
            logger.error(f"❌ Slack API error sending ephemeral message: {e.response['error']}")
            return {"success": False, "error": f"Slack API error: {e.response['error']}", "response": e.response}
        except SlackClientError as e:
            logger.error(f"❌ Slack client error sending ephemeral message: {str(e)}")
            return {"success": False, "error": f"Slack client error: {str(e)}", "response": None}
        except Exception as e:
            logger.error(f"❌ Unexpected error sending ephemeral message: {str(e)}")
            return {"success": False, "error": f"Unexpected error: {str(e)}", "response": None}

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
