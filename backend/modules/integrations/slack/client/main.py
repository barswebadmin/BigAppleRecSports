"""
Core Slack API methods.
Handles direct Slack API interactions: sending messages, updating messages, ephemeral messages.
"""

import time
import logging
from typing import Dict, Any, Optional, List, Union, Callable, TypeVar
from urllib3.exceptions import NameResolutionError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientError
from slack_sdk.models.blocks import Block, SectionBlock, MarkdownTextObject
from slack_sdk.webhook import WebhookClient

from config.main import SlackConfig

logger = logging.getLogger(__name__)

T = TypeVar('T')


def is_transient_error(exception: Exception) -> bool:
    """
    Check if an exception is a transient error that should be retried.
    
    Transient errors include:
    - DNS resolution failures
    - Network connectivity issues (connection refused, timeout, reset)
    - Slack API rate limiting (429)
    - Server errors (502, 503, 504)
    
    Non-transient errors (won't retry):
    - Authentication failures (invalid_auth, token_revoked)
    - Permission errors (missing_scope, not_in_channel)
    - Resource not found (channel_not_found, user_not_found)
    - Invalid parameters (invalid_arguments)
    
    Args:
        exception: The exception to check
        
    Returns:
        True if the error is transient and should be retried
    """
    # DNS resolution errors
    if isinstance(exception, NameResolutionError):
        return True
    
    # Slack API errors
    if isinstance(exception, SlackApiError):
        error_code = exception.response.get("error")
        status_code = exception.response.status_code
        
        # Rate limiting
        if error_code == "rate_limited" or status_code == 429:
            return True
        
        # Server errors (Slack's fault, not ours)
        if status_code in (502, 503, 504):
            return True
        
        # Non-transient Slack errors (fail fast)
        non_transient_errors = {
            "invalid_auth",
            "token_revoked",
            "token_expired",
            "account_inactive",
            "missing_scope",
            "not_authed",
            "invalid_arguments",
            "channel_not_found",
            "user_not_found",
            "not_in_channel",
        }
        if error_code in non_transient_errors:
            return False
    
    # Check error message for transient indicators
    error_str = str(exception).lower()
    transient_indicators = [
        "failed to resolve",
        "connection refused",
        "connection reset",
        "connection timeout",
        "read timeout",
        "rate limit",
        "429",
        "502",
        "503",
        "504"
    ]
    
    return any(indicator in error_str for indicator in transient_indicators)


class SlackClient:
    """Core Slack API methods for direct API interactions"""

    web_client = WebClient()
    def __init__(self):
        self.client = self.web_client
        self._timeout_seconds = 10
        self._max_retries = 3

    def _retry_with_backoff(
        self,
        func: Callable[[], T],
        max_retries: int,
        operation_name: str,
        initial_delay: float = 0.5,
        backoff_factor: float = 2.0
    ) -> T:
        """
        Retry a function with exponential backoff for transient errors.
        
        Only retries transient errors (rate limits, network issues, server errors).
        Non-transient errors (auth, permissions, not found) fail immediately.
        
        Args:
            func: The function to retry (no arguments)
            max_retries: Maximum number of retry attempts
            operation_name: Human-readable operation name for logging
            initial_delay: Initial delay in seconds (default: 0.5)
            backoff_factor: Multiplier for delay on each retry (default: 2.0)
            
        Returns:
            The result of the function call
            
        Raises:
            The last exception if all retries fail
        """
        delay = initial_delay
        
        for attempt in range(max_retries + 1):
            try:
                return func()
            except Exception as e:
                # Last attempt - always re-raise
                if attempt == max_retries:
                    logger.error(
                        f"❌ {operation_name} failed after {max_retries} retries: {e}"
                    )
                    raise
                
                # Check if error is transient
                if not is_transient_error(e):
                    logger.error(
                        f"❌ {operation_name} failed with non-transient error: {e}"
                    )
                    raise
                
                # Transient error - log and retry
                logger.warning(
                    f"⚠️  {operation_name} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
                delay *= backoff_factor
        
        raise RuntimeError(f"{operation_name} failed: unreachable code")

    def _execute_slack_api_call(
        self,
        api_method: Callable,
        payload: Optional[Dict[str, Any]] = None,
        operation_name: str = "Slack API call",
    ) -> Dict[str, Any]:
        """
        Execute a Slack API call with smart retry logic and error handling.
        
        Uses exponential backoff and only retries transient errors
        (rate limits, network issues, server errors). Fails fast for
        non-transient errors (auth, permissions, not found).
        
        Args:
            api_method: The Slack SDK method to call (e.g., client.chat_postMessage)
            payload: Optional payload to send to the API (defaults to empty dict)
            operation_name: Human-readable operation name for logging
            
        Returns:
            Dict containing success status and response data
        """
        try:
            def _api_call():
                return api_method(**(payload or {}), timeout=self._timeout_seconds)
            
            response = self._retry_with_backoff(
                _api_call,
                max_retries=self._max_retries,
                operation_name=operation_name
            )
            
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
            return {"success": False, "error": f"Slack API error: {e.response['error']}", "response": e.response}
        except SlackClientError as e:
            return {"success": False, "error": f"Slack client error: {str(e)}", "response": None}
        except Exception as e:
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

