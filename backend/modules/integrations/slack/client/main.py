"""
Core Slack API methods.
Handles direct Slack API interactions: sending messages, updating messages, ephemeral messages.
"""

import logging
from typing import Dict, Any, Optional, List, Union, Callable
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientError
from slack_sdk.models.blocks import Block, SectionBlock, MarkdownTextObject
from slack_sdk.webhook import WebhookClient

from config.main import SlackConfig

logger = logging.getLogger(__name__)


class SlackClient:
    """Core Slack API methods for direct API interactions"""

    web_client = WebClient()
    def __init__(self):
        self.client = self.web_client
        self._timeout_seconds = 10
        self._max_retries = 3

    def _execute_slack_api_call(
        self,
        api_method: Callable,
        payload: Dict[str, Any],
        operation_name: str,
    ) -> Dict[str, Any]:
        """
        Execute a Slack API call with retry logic and error handling.
        
        Args:
            api_method: The Slack SDK method to call (e.g., client.chat_postMessage)
            payload: The payload to send to the API
            operation_name: Human-readable operation name for logging
            
        Returns:
            Dict containing success status and response data
        """
        try:
            last_error = None
            for attempt in range(1, self._max_retries + 1):
                try:
                    response = api_method(**payload, timeout=self._timeout_seconds)
                    break
                except Exception as e:
                    last_error = e
                    if attempt < self._max_retries:
                        logger.warning(f"⚠️ Retry {attempt}/{self._max_retries} for {operation_name}: {str(e)}")
            else:
                logger.error(f"❌ All {self._max_retries} retries failed for {operation_name}: {str(last_error)}")
                return {"success": False, "error": f"Unexpected error: {str(last_error)}", "response": None}
            
            if response["ok"]:
                logger.info(f"✅ {operation_name}")
                return {
                    "success": True,
                    "message_ts": response.get("message_ts"),
                    "channel": response.get("channel"),
                    "response": response
                }
            return {"success": False, "error": response.get("error", "Unknown error"), "response": response}
                
        except SlackApiError as e:
            logger.error(f"❌ Slack API error: {e.response['error']}")
            return {"success": False, "error": f"Slack API error: {e.response['error']}", "response": e.response}
        except SlackClientError as e:
            logger.error(f"❌ Slack client error: {str(e)}")
            return {"success": False, "error": f"Slack client error: {str(e)}", "response": None}
        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")
            return {"success": False, "error": f"Unexpected error: {str(e)}", "response": None}

    def send_message(
        self,
        channel: "SlackConfig.Channels._Channel",
        bot: "SlackConfig.Bots._Bot",
        blocks: List[Block],
        metadata: Optional[Dict[str, Any]] = None,
        thread_ts: Optional[str] = None,
        message_ts: Optional[str] = None,
        user: Optional["SlackConfig.Users._User"] = None,
    ) -> Dict[str, Any]:
        """
        Send or update a Slack message (dispatcher method).
        
        Routes to the appropriate Slack API based on parameters:
        - message_ts present → update existing message (chat_update)
        - user present → send ephemeral message (chat_postEphemeral)
        - thread_ts present → reply in thread (chat_postMessage)
        - none of above → send new message (chat_postMessage)
        
        Args:
            channel: Slack channel
            bot: Slack bot
            blocks: Slack blocks for rich formatting
            metadata: Optional metadata
            thread_ts: Thread timestamp (for replies)
            message_ts: Message timestamp (for updates)
            user: Slack user (for ephemeral messages)
            
        Returns:
            Dict containing success status and response data
        """
        blocks_dicts = [block.to_dict() for block in blocks]
        
        payload = {
            "channel": channel.id,
            "token": bot.token,
            "blocks": blocks_dicts,
            "text": "Message",
            "metadata": metadata,
            "thread_ts": thread_ts,
        }
        
        if message_ts:
            payload["ts"] = message_ts
            api_method = self.client.chat_update
            operation_name = f"Message updated in {channel.name}"
        elif user:
            payload["user"] = user.id
            api_method = self.client.chat_postEphemeral
            operation_name = f"Ephemeral message sent to {user.name} in {channel.name}"
        else:
            operation_name = f"Thread reply sent to {channel.name}" if thread_ts else f"Message sent to {channel.name}"
            api_method = self.client.chat_postMessage
        
        return self._execute_slack_api_call(
            api_method=api_method,
            payload=payload,
            operation_name=operation_name,
        )

    def reply_in_thread(
        self,
        channel: "SlackConfig.Channels._Channel",
        bot: "SlackConfig.Bots._Bot",
        thread_ts: str,
        blocks: List[Block],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Reply to an existing message thread.
        
        Args:
            channel: Slack channel
            bot: Slack bot
            thread_ts: Parent message timestamp to reply to
            blocks: Slack blocks for rich formatting
            metadata: Optional metadata
            
        Returns:
            Dict containing success status and response data
        """
        return self.send_message(
            channel=channel,
            bot=bot,
            blocks=blocks,
            metadata=metadata,
            thread_ts=thread_ts,
        )

    def update_message(
        self,
        channel: "SlackConfig.Channels._Channel",
        bot: "SlackConfig.Bots._Bot",
        message_ts: str,
        blocks: List[Block],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing Slack message.
        
        Args:
            channel: Slack channel
            bot: Slack bot
            message_ts: Message timestamp to update
            blocks: Slack blocks for message content
            metadata: Optional metadata
            
        Returns:
            Dict containing success status and response data
        """
        return self.send_message(
            channel=channel,
            bot=bot,
            blocks=blocks,
            metadata=metadata,
            message_ts=message_ts,
        )

    def send_ephemeral_message(
        self,
        user: "SlackConfig.Users._User",
        bot: "SlackConfig.Bots._Bot",
        channel: "SlackConfig.Channels._Channel",
        blocks: List[Block],
    ) -> Dict[str, Any]:
        """
        Send an ephemeral message to a user in a channel.
        
        Args:
            user: Slack user
            bot: Slack bot
            channel: Slack channel
            blocks: Slack blocks for message content
            
        Returns:
            Dict containing success status and response data
        """
        return self.send_message(
            channel=channel,
            bot=bot,
            blocks=blocks,
            user=user,
        )

    def update_ephemeral_message(
        self,
        response_url: str,
        text: str,
        blocks: List[Block],
        show_loading: bool = True,
        loading_message: str = "Processing..."
    ) -> None:
        """
        Update an ephemeral message via response_url using Slack SDK.
        
        Flow:
        1. User submits something (e.g., clicks button) → Slack provides response_url
        2. First update (optional): Show loading with replace_original=True
        3. Second update: Show final message with replace_original=True
        
        Both updates target the SAME ephemeral message. If loading fails, we still
        attempt to send the final message.
        
        Args:
            response_url: The response_url from Slack interaction
            text: Fallback text for the message
            blocks: List of typed Block objects (final state)
            show_loading: Whether to show loading state first (default True)
            loading_message: Loading message text (default "Processing...")
        """
        webhook = WebhookClient(response_url, timeout=10)
        
        # Step 1: Show loading state (if requested, failures are logged but don't stop execution)
        if show_loading:
            try:
                self._show_loading_state_ephemeral(webhook, loading_message)
            except Exception as e:
                logger.warning(f"Loading state failed, continuing to final message: {e}")
        
        # Step 2: Always attempt to send final message (updates the same ephemeral message)
        try:
            response = webhook.send(
                text=text,
                blocks=blocks,
                replace_original=True
            )
            
            if response.status_code != 200:
                logger.error(f"Error updating ephemeral message: {response.body}")
            
        except Exception as e:
            logger.error(f"Failed to send final message: {e}")

    def _show_loading_state_ephemeral(self, webhook: WebhookClient, loading_message: str) -> None:
        """
        Show a loading state to the user immediately.
        Uses replace_original=True to update the same ephemeral message.
        """
        loading_block = SectionBlock(
            text=MarkdownTextObject(text=f"⏳ *{loading_message}*")
        )
        
        response = webhook.send(
            text=loading_message,
            blocks=[loading_block],
            replace_original=True
        )
        
        if response.status_code != 200:
            logger.warning(f"Loading state returned non-200: {response.body}")

