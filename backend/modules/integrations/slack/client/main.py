"""
Core Slack API methods.
Handles direct Slack API interactions: sending messages, updating messages, ephemeral messages.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union, Callable, TypeVar, Literal
from pydantic import BaseModel, field_serializer
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientError
from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler, ConnectionErrorRetryHandler
from slack_sdk.http_retry import RetryHandler, RetryState, HttpRequest, HttpResponse
from slack_sdk.models.blocks import Block, SectionBlock, MarkdownTextObject
from slack_sdk.webhook import WebhookClient

from config_old_deprecated.slack import SlackConfig
from shared.model_config import ApiModel

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseChatPayload(ApiModel):
    """Base payload fields shared across all chat API methods"""
    channel: str
    token: str
    blocks: List[Block]
    text: str
    metadata: Optional[Dict[str, Any]] = None
    
    @field_serializer('blocks')
    def serialize_blocks(self, blocks: List[Block]) -> List[Dict[str, Any]]:
        """Convert Block objects to dicts for JSON serialization"""
        return [block.to_dict() if isinstance(block, Block) else block for block in blocks]
    
    class Config:
        arbitrary_types_allowed = True


class ChatPostMessagePayload(BaseChatPayload):
    """Type-safe payload for chat.postMessage API"""
    thread_ts: Optional[str] = None


class ChatUpdatePayload(BaseChatPayload):
    """Type-safe payload for chat.update API"""
    ts: str


class ChatPostEphemeralPayload(BaseChatPayload):
    """Type-safe payload for chat.postEphemeral API"""
    user: str


class UserLookupByEmailPayload(ApiModel):
    """Type-safe payload for users.lookupByEmail API"""
    email: str


class UserListPayload(ApiModel):
    """Type-safe payload for users.list API"""
    limit: Optional[int] = None
    cursor: Optional[str] = None


class SlackUserIdentifier(ApiModel):
    """Type-safe identifier for Slack user lookups (email or user_id)"""
    email: Optional[str] = None
    user_id: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.email and not self.user_id:
            raise ValueError("SlackUserIdentifier must have either 'email' or 'user_id'")
        if self.email and self.user_id:
            raise ValueError("SlackUserIdentifier cannot have both 'email' and 'user_id'")


class ServerErrorRetryHandler(RetryHandler):
    """Custom retry handler for 5xx server errors (502, 503, 504)"""
    
    def can_retry(
        self,
        *,
        state: RetryState,
        request: HttpRequest,
        response: Optional[HttpResponse] = None,
        error: Optional[Exception] = None,
    ) -> bool:
        """Retry on 5xx server errors"""
        if response and response.status_code in (502, 503, 504):
            return True
        return False


class SlackClient(WebClient):
    """Core Slack API methods for direct API interactions - extends WebClient with convenience methods"""

    # Map common API methods to their required scopes
    _METHOD_SCOPE_MAP = {
        'users.profile.set': 'users.profile:write',
        'users.profile.get': 'users.profile:read',
        'users.info': 'users:read',
        'users.list': 'users:read',
        'users.lookupByEmail': 'users:read.email',
        'conversations.list': 'channels:read',
        'conversations.info': 'channels:read',
        'usergroups.list': 'usergroups:read',
        'usergroups.users.update': 'usergroups:write',
    }
    
    # Methods that require User Token (not Bot Token)
    _USER_TOKEN_METHODS = {
        'users.profile.set',
        'users.profile.get',
    }

    def __init__(self, timeout: int = 10, max_retries: int = 3, token: Optional[str] = None, user_token: Optional[str] = None, **kwargs):
        """
        Initialize Slack client with built-in retry handlers.
        
        Args:
            timeout: Request timeout in seconds (default: 10)
            max_retries: Maximum number of retry attempts for transient errors (default: 3)
            token: Bot token (if not provided, must be set later)
            user_token: Optional User Token for operations requiring User Token Scopes (e.g., users.profile:write)
            **kwargs: Additional arguments passed to WebClient constructor
        """
        # Initialize WebClient parent with token and timeout
        super().__init__(token=token, timeout=timeout, **kwargs)
        
        # Store User Token separately (not set on WebClient)
        self._user_token = user_token
        
        # Configure retry handlers if not already configured
        if not hasattr(self, 'retry_handlers') or not self.retry_handlers:
            self.retry_handlers = [
                RateLimitErrorRetryHandler(max_retry_count=max_retries),
                ConnectionErrorRetryHandler(max_retry_count=max_retries),
                ServerErrorRetryHandler(max_retry_count=max_retries),
            ]

    @classmethod
    def get_required_scope_for_error(cls, error_code: str, api_method: Optional[str] = None) -> Optional[str]:
        """
        Determine required scope based on error code and API method.
        
        Args:
            error_code: Slack API error code (e.g., 'missing_scope', 'not_allowed_token_type')
            api_method: Optional API method name (e.g., 'users.profile.set')
            
        Returns:
            Required scope name if known, None otherwise
        """
        if api_method and api_method in cls._METHOD_SCOPE_MAP:
            return cls._METHOD_SCOPE_MAP[api_method]
        
        # For not_allowed_token_type on users.profile.set, it's always users.profile:write
        if error_code == 'not_allowed_token_type' and api_method == 'users.profile.set':
            return 'users.profile:write'
        
        return None

    def _execute_slack_api_call(
        self,
        api_method: Callable,
        payload: Optional[Union[
            ChatPostMessagePayload,
            ChatUpdatePayload,
            ChatPostEphemeralPayload,
            UserListPayload,
            UserLookupByEmailPayload,
            SlackUserIdentifier,
            BaseModel,
            Dict[str, Any]
        ]] = None,
        operation_name: str = "Slack API call",
    ) -> Dict[str, Any]:
        """
        Execute a Slack API call with error handling.
        
        Automatically uses User Token if the API method requires it and one is available.
        
        Retry logic is handled automatically by the Slack SDK's built-in retry handlers:
        - RateLimitErrorRetryHandler: Handles 429 rate limits
        - ConnectionErrorRetryHandler: Handles connection errors
        - ServerErrorRetryHandler: Handles 5xx server errors
        
        Args:
            api_method: The Slack SDK method to call (e.g., client.chat_postMessage)
            payload: Optional payload to send to the API (defaults to empty dict)
            operation_name: Human-readable operation name for logging
            
        Returns:
            Dict containing success status and response data
        """
        try:
            # Convert Pydantic model to dict if needed
            if payload:
                if isinstance(payload, ApiModel):
                    # ApiModel - use to_dict_snake() to serialize (handles Block objects via field_serializer)
                    api_payload = payload.to_dict_snake()
                elif isinstance(payload, BaseModel):
                    # Other Pydantic model - use model_dump() to serialize
                    api_payload = payload.model_dump(exclude_none=True)
                elif isinstance(payload, dict):
                    # Already a dict, use as-is
                    api_payload = payload
                else:
                    raise TypeError(f"Payload must be a Pydantic model or dict, got {type(payload)}")
            else:
                api_payload = {}
            
            # Determine if this API method requires a User Token
            api_method_name = None
            if api_method:
                if hasattr(api_method, '__name__'):
                    method_name = api_method.__name__
                    api_method_name = method_name.replace('_', '.')
            
            # Use User Token if method requires it and we have one
            client_to_use = self
            if api_method_name and api_method_name in self._USER_TOKEN_METHODS:
                if self._user_token:
                    # Create a temporary WebClient with User Token for this call
                    # Copy retry handlers from main client to ensure consistent retry behavior
                    client_to_use = WebClient(token=self._user_token, timeout=self.timeout)
                    if hasattr(self, 'retry_handlers') and self.retry_handlers:
                        client_to_use.retry_handlers = self.retry_handlers
                    # Get the same method from the new client
                    method_name = api_method.__name__
                    api_method = getattr(client_to_use, method_name)
                    logger.info(f"✅ Using User Token for {api_method_name} (token: {self._user_token[:10]}...)")
                else:
                    logger.warning(f"⚠️  {api_method_name} requires User Token but none configured! Using Bot Token (may fail or have limited functionality)")
            
            # SDK handles retries automatically via retry_handlers
            # Log the actual payload being sent for debugging
            if api_method_name == 'users.profile.set':
                logger.info(f"users.profile.set - About to call API")
                logger.info(f"  Payload: {json.dumps(api_payload, indent=2, default=str)}")
                logger.info(f"  Token type: {'User' if client_to_use.token and client_to_use.token.startswith('xoxp-') else 'Bot' if client_to_use.token and client_to_use.token.startswith('xoxb-') else 'Unknown'}")
                logger.info(f"  Token (first 15): {client_to_use.token[:15] if client_to_use.token else 'None'}...")
                logger.info(f"  API method: {api_method}")
                logger.info(f"  Client type: {type(client_to_use)}")
            
            # Make the actual API call
            try:
                response = api_method(**api_payload)
            except Exception as e:
                logger.error(f"Exception during API call: {type(e).__name__}: {e}")
                raise
            
            # Log the raw response immediately
            if api_method_name == 'users.profile.set':
                logger.info(f"users.profile.set - API call completed")
                logger.info(f"  Response type: {type(response)}")
                if hasattr(response, 'data'):
                    response_dict = response.data
                    logger.info(f"  Response.data: {json.dumps(response_dict, indent=2, default=str)}")
                    # Check if there are custom fields
                    if isinstance(response_dict, dict) and 'profile' in response_dict:
                        profile = response_dict['profile']
                        if 'fields' in profile:
                            logger.info(f"  Custom fields in response: {json.dumps(profile['fields'], indent=2, default=str)}")
                else:
                    logger.info(f"  Response (dict): {json.dumps(dict(response) if hasattr(response, '__dict__') else response, indent=2, default=str)}")
            
            # Log response immediately after call
            if api_method_name == 'users.profile.set':
                logger.info(f"users.profile.set API call completed")
                logger.info(f"  Response type: {type(response)}")
                logger.info(f"  Response['ok']: {response.get('ok')}")
                logger.info(f"  Token used: {client_to_use.token[:10] if client_to_use.token else 'None'}... (type: {'User' if client_to_use.token and client_to_use.token.startswith('xoxp-') else 'Bot' if client_to_use.token and client_to_use.token.startswith('xoxb-') else 'Unknown'})")
                if response.get('ok'):
                    logger.info(f"  Response data: {json.dumps(response, indent=2, default=str)}")
                    # Check if title was actually updated
                    if 'profile' in response and 'title' in response['profile']:
                        requested_title = api_payload.get('profile', {}).get('title', 'N/A')
                        returned_title = response['profile'].get('title', 'N/A')
                        if requested_title != returned_title:
                            logger.warning(f"  ⚠️  Title mismatch! Requested: '{requested_title}', Returned: '{returned_title}'")
                        else:
                            logger.info(f"  ✅ Title matches: '{returned_title}'")
                else:
                    logger.error(f"  Response error: {response.get('error')}")
            
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
            # SDK retry handlers have already attempted retries for transient errors
            # If we get here, either retries were exhausted or it's a non-transient error
            error_response = e.response.data if hasattr(e.response, 'data') else dict(e.response) if hasattr(e.response, '__dict__') else {'error': str(e.response)}
            error_code = error_response.get("error") if isinstance(error_response, dict) else None
            
            # Extract API method name from callable for scope checking
            api_method_name = None
            if api_method:
                # Try to get method name from callable
                if hasattr(api_method, '__name__'):
                    method_name = api_method.__name__
                    # Convert SDK method names to API method names (e.g., 'users_profile_set' -> 'users.profile.set')
                    api_method_name = method_name.replace('_', '.')
                elif hasattr(api_method, '__qualname__'):
                    api_method_name = api_method.__qualname__.split('.')[-1].replace('_', '.')
            
            # Check for scope-related errors and include scope info
            scope_info = {}
            if error_code in ['missing_scope', 'not_allowed_token_type', 'invalid_auth']:
                try:
                    import requests
                    token = self.token
                    if token:
                        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
                        auth_response = requests.post('https://slack.com/api/auth.test', headers=headers, timeout=5)
                        scopes_str = auth_response.headers.get('x-oauth-scopes', '')
                        scopes = [s.strip() for s in scopes_str.split(',')] if scopes_str else []
                        # Detect token type (including Enterprise Grid tokens)
                        if token.startswith('xoxb-'):
                            token_type = 'Bot Token'
                        elif token.startswith('xoxp-'):
                            token_type = 'User Token'
                        elif token.startswith('xoxe.xoxb-'):
                            token_type = 'Enterprise Grid Bot Token'
                        elif token.startswith('xoxe.xoxp-'):
                            token_type = 'Enterprise Grid User Token'
                        else:
                            token_type = 'Unknown'
                        
                        # Determine required scope using class method
                        required_scope = self.get_required_scope_for_error(error_code, api_method_name)
                        
                        missing_scopes = []
                        if required_scope and required_scope not in scopes:
                            missing_scopes = [required_scope]
                        
                        scope_info = {
                            'token_type': token_type,
                            'current_scopes': scopes,
                            'missing_scopes': missing_scopes
                        }
                        if required_scope:
                            scope_info['required_scope'] = required_scope
                        if api_method_name:
                            scope_info['api_method'] = api_method_name
                except Exception:
                    pass  # Don't fail if scope checking fails
            
            error_msg = f"Slack API error: {error_code or str(e)}"
            if scope_info:
                logger.error(f"❌ {operation_name} failed: {error_code or str(e)}")
                logger.error(f"   Token Type: {scope_info.get('token_type', 'Unknown')}")
                logger.error(f"   Current Scopes: {', '.join(scope_info.get('current_scopes', []))}")
                if scope_info.get('missing_scopes'):
                    logger.error(f"   Missing Scopes: {', '.join(scope_info['missing_scopes'])}")
            else:
                logger.error(f"❌ {operation_name} failed: {error_code or str(e)}")
            
            result = {"success": False, "error": error_msg, "response": error_response}
            if scope_info:
                result["scope_info"] = scope_info
            return result
        except SlackClientError as e:
            logger.error(f"❌ {operation_name} failed: {str(e)}")
            return {"success": False, "error": f"Slack client error: {str(e)}", "response": None}
        except Exception as e:
            logger.error(f"❌ {operation_name} failed: {str(e)}")
            return {"success": False, "error": f"Unexpected error: {str(e)}", "response": None}

    def send_message(
        self,
        message_type: Literal["to_user", "to_channel", "reply", "ephemeral"],
        channel_id: str,
        bot_token: str,
        blocks: List[Block],
        metadata: Optional[Dict[str, Any]] = None,
        thread_ts: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a Slack message with explicit message type.
        
        Args:
            message_type: Type of message to send
                - 'to_user': Direct message to a user (DM)
                - 'to_channel': Regular message to a channel
                - 'reply': Reply in a thread (requires thread_ts)
                - 'ephemeral': Ephemeral message in a channel (only visible to user_id, requires user_id)
            channel_id: Slack channel ID (or user ID for DMs)
            bot_token: Bot token to use
            blocks: Slack blocks for rich formatting
            metadata: Optional metadata
            thread_ts: Thread timestamp (required for 'reply' type)
            user_id: User ID (required for 'ephemeral' type, optional for 'to_user')
            
        Returns:
            Dict containing success status and response data
        """
        payload: Union[ChatPostMessagePayload, ChatPostEphemeralPayload]
        
        if message_type == "ephemeral":
            if not user_id:
                raise ValueError("user_id is required for ephemeral messages")
            payload = ChatPostEphemeralPayload(
                channel=channel_id,
                token=bot_token,
                user=user_id,
                blocks=blocks,
                text="Message",
                metadata=metadata,
            )
            api_method = self.chat_postEphemeral
            operation_name = f"Ephemeral message sent to {user_id} in {channel_id}"
        elif message_type == "reply":
            if not thread_ts:
                raise ValueError("thread_ts is required for reply messages")
            payload = ChatPostMessagePayload(
                channel=channel_id,
                token=bot_token,
                blocks=blocks,
                text="Message",
                metadata=metadata,
                thread_ts=thread_ts,
            )
            api_method = self.chat_postMessage
            operation_name = f"Thread reply sent to {channel_id}"
        else:  # to_user or to_channel
            payload = ChatPostMessagePayload(
                channel=channel_id,
                token=bot_token,
                blocks=blocks,
                text="Message",
                metadata=metadata,
            )
            api_method = self.chat_postMessage
            operation_name = f"Message sent to {channel_id}" if message_type == "to_channel" else f"DM sent to {channel_id}"
        
        return self._execute_slack_api_call(
            api_method=api_method,
            payload=payload,
            operation_name=operation_name,
        )

    def update_message(
        self,
        update_type: Literal["direct", "ephemeral"],
        channel_id: str,
        bot_token: str,
        message_ts: Optional[str],
        blocks: List[Block],
        metadata: Optional[Dict[str, Any]] = None,
        response_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing Slack message.
        
        Args:
            update_type: Type of message to update
                - 'direct': Update a regular message via chat.update (requires message_ts)
                - 'ephemeral': Update an ephemeral message via response_url (requires response_url)
            channel_id: Slack channel ID
            bot_token: Bot token to use
            message_ts: Message timestamp (required for 'direct' type)
            blocks: Slack blocks for message content
            metadata: Optional metadata
            response_url: Response URL from interaction (required for 'ephemeral' type)
            
        Returns:
            Dict containing success status and response data
        """
        if update_type == "ephemeral":
            if not response_url:
                raise ValueError("response_url is required for ephemeral message updates")
            self.update_ephemeral_message(
                response_url=response_url,
                text="Message",
                blocks=blocks,
                show_loading=False,
            )
            return {"success": True, "response": None}
        else:  # direct
            if not message_ts:
                raise ValueError("message_ts is required for direct message updates")
            payload = ChatUpdatePayload(
                channel=channel_id,
                token=bot_token,
                ts=message_ts,
            blocks=blocks,
                text="Message",
            metadata=metadata,
            )
            return self._execute_slack_api_call(
                api_method=self.chat_update,
                payload=payload,
                operation_name=f"Message updated in {channel_id}",
            )

    def send_message_to_user(
        self,
        user_id: str,
        bot_token: str,
        blocks: List[Block],
        text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a direct message to a user by user_id.
        
        Convenience wrapper around send_message with type='to_user'.
        
        Args:
            user_id: Slack user ID (also used as channel for DM)
            bot_token: Bot token to use
            blocks: Slack blocks for message content
            text: Optional fallback text (not used, kept for API consistency)
            
        Returns:
            Dict containing success status and response data
        """
        return self.send_message(
            message_type="to_user",
            channel_id=user_id,
            bot_token=bot_token,
            blocks=blocks,
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

    def update_user_profile(
        self,
        user_id: str,
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a Slack user's profile with scope error handling.
        
        Wraps users_profile_set to use _execute_slack_api_call for consistent
        error handling including scope information.
        
        Args:
            user_id: Slack user ID
            profile: Profile fields to update (dict with field names and values)
            
        Returns:
            Dict containing success status and response data (includes scope_info on error)
        """
        payload = {'user': user_id, 'profile': profile}
        logger.debug(f"update_user_profile called with user_id={user_id}, profile={json.dumps(profile, indent=2, default=str)}")
        logger.debug(f"Full payload: {json.dumps(payload, indent=2, default=str)}")
        logger.debug(f"Using token type: {'User Token' if self._user_token else 'Bot Token'}")
        if self._user_token:
            logger.debug(f"User token (first 10): {self._user_token[:10]}...")
        else:
            logger.debug(f"Bot token (first 10): {self.token[:10] if self.token else 'None'}...")
        
        result = self._execute_slack_api_call(
            api_method=self.users_profile_set,
            payload=payload,
            operation_name=f"Update profile for user {user_id}"
        )
        
        logger.debug(f"update_user_profile result: success={result.get('success')}, error={result.get('error')}")
        if result.get("response"):
            response = result.get("response")
            if hasattr(response, 'data'):
                logger.debug(f"Response data: {json.dumps(response.data, indent=2, default=str)}")
            else:
                logger.debug(f"Response (no data attr): {response}")
        
        return result

