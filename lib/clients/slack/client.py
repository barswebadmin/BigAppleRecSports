"""
Core Slack API client, bot configs, and lightweight SlackBot wrapper.

SlackClient  — extends WebClient with send/update/lookup convenience methods.
BotConfig    — lazy env-var reader for a single bot's token + signing secret.
Bots         — named BotConfig instances for all BARS bots.
SlackBot     — lightweight wrapper (NOT Bolt) that pairs a BotConfig with a
               SlackClient and exposes send_message / lookup_* helpers.
               For Bolt/interactivity, see backend/modules/integrations/slack/bot_apps.
"""

import logging
import os
from typing import Any, Callable, Dict, List, Literal, Optional, TypedDict, TypeVar, Union

from pydantic import BaseModel, ConfigDict, field_serializer
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError, SlackClientError
from slack_sdk.http_retry import HttpRequest, HttpResponse, RetryHandler, RetryState
from slack_sdk.http_retry.builtin_handlers import (
    ConnectionErrorRetryHandler,
    RateLimitErrorRetryHandler,
)
from slack_sdk.models.blocks import Block, MarkdownTextObject, SectionBlock
from slack_sdk.webhook import WebhookClient

from shared_utilities.pydantic_config import DEFAULT_CONFIG_DICT

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ── TypedDicts ────────────────────────────────────────────────────────────────

class SlackScopeInfo(TypedDict, total=False):
    token_type: str
    current_scopes: List[str]
    missing_scopes: List[str]
    required_scope: Optional[str]
    api_method: Optional[str]


class SlackApiSuccessResponse(TypedDict):
    success: Literal[True]
    message_ts: Optional[str]
    channel: Optional[str]
    response: Dict[str, Any]


class SlackApiErrorResponse(TypedDict, total=False):
    success: Literal[False]
    error: str
    response: Optional[Dict[str, Any]]
    scope_info: Optional[SlackScopeInfo]


SlackApiResponse = Union[SlackApiSuccessResponse, SlackApiErrorResponse]


class SlackUserProfileUpdate(TypedDict, total=False):
    title: Optional[str]
    phone: Optional[str]
    skype: Optional[str]
    real_name: Optional[str]
    display_name: Optional[str]
    status_text: Optional[str]
    status_emoji: Optional[str]
    status_expiration: Optional[int]
    fields: Optional[Dict[str, Dict[str, Any]]]


# ── Pydantic payloads ─────────────────────────────────────────────────────────

class BaseChatPayload(BaseModel):
    model_config = ConfigDict(
        alias_generator=DEFAULT_CONFIG_DICT['alias_generator'],  # pyright: ignore[reportTypedDictNotRequiredAccess]
        populate_by_name=True,
        extra='ignore',
        arbitrary_types_allowed=True
    )
    
    channel: str
    token: str
    blocks: List[Block]
    text: str
    metadata: Optional[Dict[str, Any]] = None

    @field_serializer("blocks")
    def serialize_blocks(self, blocks: List[Block]) -> List[Dict[str, Any]]:
        return [b.to_dict() if isinstance(b, Block) else b for b in blocks]


class ChatPostMessagePayload(BaseChatPayload):
    thread_ts: Optional[str] = None


class ChatUpdatePayload(BaseChatPayload):
    ts: str


class ChatPostEphemeralPayload(BaseChatPayload):
    user: str


class UserLookupByEmailPayload(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    email: str


class UserListPayload(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    limit: Optional[int] = None
    cursor: Optional[str] = None


class SlackUserIdentifier(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    email: Optional[str] = None
    user_id: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.email and not self.user_id:
            raise ValueError("SlackUserIdentifier must have either 'email' or 'user_id'")
        if self.email and self.user_id:
            raise ValueError("SlackUserIdentifier cannot have both 'email' and 'user_id'")


# ── Retry handler ─────────────────────────────────────────────────────────────

class ServerErrorRetryHandler(RetryHandler):
    def can_retry(
        self,
        *,
        state: RetryState,
        request: HttpRequest,
        response: Optional[HttpResponse] = None,
        error: Optional[Exception] = None,
    ) -> bool:
        return bool(response and response.status_code in (502, 503, 504))


# ── SlackClient ───────────────────────────────────────────────────────────────

class SlackClient(WebClient):
    """WebClient extended with convenience send/update/lookup methods."""

    _METHOD_SCOPE_MAP = {
        "users.profile.set": "users.profile:write",
        "users.profile.get": "users.profile:read",
        "users.info": "users:read",
        "users.list": "users:read",
        "users.lookupByEmail": "users:read.email",
        "conversations.list": "channels:read,groups:read",  # groups:read for private channels
        "conversations.info": "channels:read,groups:read",  # groups:read for private channels
        "usergroups.list": "usergroups:read",
        "usergroups.users.update": "usergroups:write",
    }

    _USER_TOKEN_METHODS = {"users.profile.set", "users.profile.get"}

    def __init__(
        self,
        timeout: int = 10,
        max_retries: int = 3,
        token: Optional[str] = None,
        user_token: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(token=token, timeout=timeout, **kwargs)
        self._user_token = user_token
        if not getattr(self, "retry_handlers", None):
            self.retry_handlers = [
                RateLimitErrorRetryHandler(max_retry_count=max_retries),
                ConnectionErrorRetryHandler(max_retry_count=max_retries),
                ServerErrorRetryHandler(max_retry_count=max_retries),
            ]

    @classmethod
    def get_required_scope_for_error(cls, error_code: str, api_method: Optional[str] = None) -> Optional[str]:
        if api_method and api_method in cls._METHOD_SCOPE_MAP:
            return cls._METHOD_SCOPE_MAP[api_method]
        if error_code == "not_allowed_token_type" and api_method == "users.profile.set":
            return "users.profile:write"
        return None

    def _execute_slack_api_call(
        self,
        api_method: Callable,
        payload: Optional[Union[BaseChatPayload, UserListPayload, UserLookupByEmailPayload, SlackUserIdentifier, BaseModel, Dict[str, Any]]] = None,
        operation_name: str = "Slack API call",
    ) -> SlackApiResponse:
        try:
            if payload:
                if isinstance(payload, BaseModel):
                    api_payload = payload.model_dump(exclude_none=True)
                elif isinstance(payload, dict):
                    api_payload = payload
                else:
                    raise TypeError(f"Payload must be a Pydantic model or dict, got {type(payload)}")
            else:
                api_payload = {}

            api_method_name = None
            if api_method and hasattr(api_method, "__name__"):
                api_method_name = api_method.__name__.replace("_", ".")

            client_to_use = self
            if api_method_name and api_method_name in self._USER_TOKEN_METHODS and self._user_token:
                client_to_use = WebClient(token=self._user_token, timeout=self.timeout)
                if getattr(self, "retry_handlers", None):
                    client_to_use.retry_handlers = self.retry_handlers
                api_method = getattr(client_to_use, api_method.__name__)

            log_payload = {k: (f"...{v[-4:]}" if k == "token" else v) for k, v in api_payload.items()}
            print(f"→ Slack {operation_name} | url: https://slack.com/api/{api_method_name or 'unknown'} | payload: {log_payload}")

            response = api_method(**api_payload)

            print(
                f"← Slack {operation_name} | status: {getattr(response, 'status_code', '?')} | "
                f"body: {dict(response.data) if hasattr(response, 'data') else str(response)}"
            )

            if response["ok"]:
                logger.info("✅ %s", operation_name)
                return SlackApiSuccessResponse(
                    success=True,
                    message_ts=response.get("message_ts"),
                    channel=response.get("channel"),
                    response=response,
                )
            return SlackApiErrorResponse(
                success=False,
                error=response.get("error", "Unknown error"),
                response=response,
            )

        except SlackApiError as e:
            error_response = (
                e.response.data if hasattr(e.response, "data")
                else dict(e.response) if hasattr(e.response, "__dict__")
                else {"error": str(e.response)}
            )
            error_code = error_response.get("error") if isinstance(error_response, dict) else None
            api_method_name = None
            if api_method and hasattr(api_method, "__name__"):
                api_method_name = api_method.__name__.replace("_", ".")

            print(
                f"← Slack {operation_name} | status: {getattr(e.response, 'status_code', '?')} | "
                f"error body: {error_response}"
            )

            scope_info: Dict[str, Any] = {}
            if error_code in ("missing_scope", "not_allowed_token_type", "invalid_auth"):
                try:
                    import requests as _req
                    token = self.token
                    if token:
                        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                        auth_resp = _req.post("https://slack.com/api/auth.test", headers=headers, timeout=5)
                        scopes = [s.strip() for s in auth_resp.headers.get("x-oauth-scopes", "").split(",") if s.strip()]
                        required = self.get_required_scope_for_error(error_code, api_method_name)
                        scope_info = {
                            "token_type": "User Token" if token.startswith("xoxp-") else "Bot Token",
                            "current_scopes": scopes,
                            "missing_scopes": [required] if required and required not in scopes else [],
                        }
                        if required:
                            scope_info["required_scope"] = required
                        if api_method_name:
                            scope_info["api_method"] = api_method_name
                except Exception:
                    pass

            logger.error("❌ %s failed: %s", operation_name, error_code or str(e))
            result: SlackApiErrorResponse = {
                "success": False,
                "error": f"Slack API error: {error_code or str(e)}",
                "response": error_response,
            }
            if scope_info:
                result["scope_info"] = scope_info  # type: ignore[typeddict-item]
            return result

        except SlackClientError as e:
            logger.error("❌ %s failed: %s", operation_name, str(e))
            return SlackApiErrorResponse(success=False, error=f"Slack client error: {str(e)}", response=None)
        except Exception as e:
            logger.error("❌ %s failed: %s", operation_name, str(e))
            return SlackApiErrorResponse(success=False, error=f"Unexpected error: {str(e)}", response=None)

    def send_message(
        self,
        message_type: Literal["to_user", "to_channel", "reply", "ephemeral"],
        channel_id: str,
        bot_token: str,
        blocks: List[Block],
        metadata: Optional[Dict[str, Any]] = None,
        thread_ts: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> SlackApiResponse:
        if message_type == "ephemeral":
            if not user_id:
                raise ValueError("user_id is required for ephemeral messages")
            payload: Union[ChatPostMessagePayload, ChatPostEphemeralPayload] = ChatPostEphemeralPayload(
                channel=channel_id, token=bot_token, user=user_id, blocks=blocks, text="Message", metadata=metadata
            )
            api_method = self.chat_postEphemeral
            op = f"Ephemeral message sent to {user_id} in {channel_id}"
        elif message_type == "reply":
            if not thread_ts:
                raise ValueError("thread_ts is required for reply messages")
            payload = ChatPostMessagePayload(
                channel=channel_id, token=bot_token, blocks=blocks, text="Message", metadata=metadata, thread_ts=thread_ts
            )
            api_method = self.chat_postMessage
            op = f"Thread reply sent to {channel_id}"
        else:
            payload = ChatPostMessagePayload(
                channel=channel_id, token=bot_token, blocks=blocks, text="Message", metadata=metadata
            )
            api_method = self.chat_postMessage
            op = f"Message sent to {channel_id}" if message_type == "to_channel" else f"DM sent to {channel_id}"
        return self._execute_slack_api_call(api_method=api_method, payload=payload, operation_name=op)

    def send_message_to_user(self, user_id: str, bot_token: str, blocks: List[Block], text: Optional[str] = None) -> SlackApiResponse:
        return self.send_message(message_type="to_user", channel_id=user_id, bot_token=bot_token, blocks=blocks)

    def update_message(
        self,
        update_type: Literal["direct", "ephemeral"],
        channel_id: str,
        bot_token: str,
        message_ts: Optional[str],
        blocks: List[Block],
        metadata: Optional[Dict[str, Any]] = None,
        response_url: Optional[str] = None,
    ) -> SlackApiResponse:
        if update_type == "ephemeral":
            if not response_url:
                raise ValueError("response_url is required for ephemeral message updates")
            self.update_ephemeral_message(response_url=response_url, text="Message", blocks=blocks, show_loading=False)
            return SlackApiSuccessResponse(success=True, message_ts=None, channel=None, response={})
        if not message_ts:
            raise ValueError("message_ts is required for direct message updates")
        payload = ChatUpdatePayload(channel=channel_id, token=bot_token, ts=message_ts, blocks=blocks, text="Message", metadata=metadata)
        return self._execute_slack_api_call(api_method=self.chat_update, payload=payload, operation_name=f"Message updated in {channel_id}")

    def update_ephemeral_message(self, response_url: str, text: str, blocks: List[Block], show_loading: bool = True, loading_message: str = "Processing...") -> None:
        webhook = WebhookClient(response_url, timeout=10)
        if show_loading:
            try:
                loading_block = SectionBlock(text=MarkdownTextObject(text=f"⏳ *{loading_message}*"))
                webhook.send(text=loading_message, blocks=[loading_block], replace_original=True)
            except Exception as exc:
                logger.warning("Loading state failed: %s", exc)
        try:
            resp = webhook.send(text=text, blocks=blocks, replace_original=True)
            if resp.status_code != 200:
                logger.error("Error updating ephemeral message: %s", resp.body)
        except Exception as exc:
            logger.error("Failed to send final message: %s", exc)

    def update_user_profile(self, user_id: str, profile: SlackUserProfileUpdate) -> SlackApiResponse:
        payload = {"user": user_id, "profile": profile}
        return self._execute_slack_api_call(
            api_method=self.users_profile_set,
            payload=payload,
            operation_name=f"Update profile for user {user_id}",
        )


# ── BotConfig + Bots ──────────────────────────────────────────────────────────

def _env(key: str) -> str:
    return os.environ.get(key, "")


class BotConfig:
    """Lazily reads env vars at access time."""

    def __init__(
        self,
        token_env: str,
        secret_env: str,
        user_token_env: Optional[str] = None,
        channel_id_env: Optional[str] = None,
    ):
        self._token_env = token_env
        self._secret_env = secret_env
        self._user_token_env = user_token_env
        self._channel_id_env = channel_id_env

    @property
    def token(self) -> str:
        v = _env(self._token_env)
        if not v:
            raise RuntimeError(f"Missing env: {self._token_env}")
        return v

    @property
    def signing_secret(self) -> str:
        v = _env(self._secret_env)
        if not v:
            raise RuntimeError(f"Missing env: {self._secret_env}")
        return v

    @property
    def user_token(self) -> Optional[str]:
        return _env(self._user_token_env) if self._user_token_env else None

    @property
    def channel_id(self) -> Optional[str]:
        return _env(self._channel_id_env) if self._channel_id_env else None


class Bots:
    """Named BotConfig instances for all BARS Slack bots."""
    Dev               = BotConfig("SLACK__DEV_BOT__TOKEN",               "SLACK__DEV_BOT__SIGNING_SECRET",               channel_id_env="SLACK__DEV_BOT__CHANNEL_ID")
    Exec              = BotConfig("SLACK__EXEC_BOT__TOKEN",               "SLACK__EXEC_BOT__SIGNING_SECRET",               channel_id_env="SLACK__EXEC_BOT__CHANNEL_ID")
    Leadership        = BotConfig("SLACK__LEADERSHIP_BOT__TOKEN",         "SLACK__LEADERSHIP_BOT__SIGNING_SECRET",         user_token_env="SLACK__LEADERSHIP_BOT__USER_TOKEN", channel_id_env="SLACK__LEADERSHIP_BOT__CHANNEL_ID")
    PaymentAssistance = BotConfig("SLACK__PAYMENT_ASSISTANCE_BOT__TOKEN", "SLACK__PAYMENT_ASSISTANCE_BOT__SIGNING_SECRET")
    Refunds           = BotConfig("SLACK__REFUNDS_BOT__TOKEN",            "SLACK__REFUNDS_BOT__SIGNING_SECRET",            channel_id_env="SLACK__REFUNDS_BOT__CHANNEL_ID")
    Registrations     = BotConfig("SLACK__REGISTRATIONS_BOT__TOKEN",      "SLACK__REGISTRATIONS_BOT__SIGNING_SECRET",      channel_id_env="SLACK__REGISTRATIONS_BOT__CHANNEL_ID")
    Web               = BotConfig("SLACK__WEB_BOT__TOKEN",                "SLACK__WEB_BOT__SIGNING_SECRET",                channel_id_env="SLACK__WEB_BOT__CHANNEL_ID")


# ── Lightweight SlackBot (no Bolt) ────────────────────────────────────────────

class SlackBot:
    """
    Lightweight Slack bot wrapper — NOT a Bolt App.

    Pairs a BotConfig with a SlackClient. Use this in Lambda and anywhere
    you only need to send outgoing messages / do lookups.

    For Bolt/interactivity (slash commands, actions, events), use
    backend/modules/integrations/slack/bot_apps/bot_apps.py instead.
    """

    def __init__(self, bot_config: BotConfig):
        self.bot_config = bot_config
        self.client = SlackClient(token=bot_config.token, user_token=bot_config.user_token)

    @property
    def token(self) -> str:
        return self.bot_config.token

    @property
    def signing_secret(self) -> str:
        return self.bot_config.signing_secret

    def send_message(
        self,
        message_type: Literal["to_user", "to_channel", "reply", "ephemeral"],
        channel_id: str,
        blocks: List[Block],
        metadata: Optional[Dict[str, Any]] = None,
        thread_ts: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> SlackApiResponse:
        """Send a message to a Slack channel or user.

        Args:
            channel_id: Channel ID (C...), channel name (#channel), or user ID (U...)
                       If a channel name is provided, it will be resolved to an ID first.

        Note: If channel resolution fails, the original identifier is used as fallback.
        """
        # If it looks like a channel name (not an ID), try to resolve it to an ID
        from shared_utilities.clients.slack.models.slack_channel import SlackChannel
        resolved_channel = channel_id

        if message_type in ("to_channel", "reply", "ephemeral"):
            # Check if it's already a valid ID
            if not SlackChannel.is_valid_channel_id(channel_id):
                # Try to resolve channel name to ID
                channel_data = self.lookup_channel(channel_id)
                if channel_data:
                    resolved_channel = channel_data.get("id", channel_id)
                    print(f"✅ Resolved channel '{channel_id}' → {resolved_channel}")
                else:
                    print(f"⚠️ Could not resolve channel '{channel_id}', using as-is (may fail)")

        return self.client.send_message(
            message_type=message_type,
            channel_id=resolved_channel,
            bot_token=self.token,
            blocks=blocks,
            metadata=metadata,
            thread_ts=thread_ts,
            user_id=user_id,
        )

    def lookup_user(self, identifier: Union[str, "SlackUserIdentifier"]) -> Optional[Dict[str, Any]]:
        from shared_utilities.clients.slack.user_lookup import lookup_user as _lookup
        if isinstance(identifier, str):
            identifier = SlackUserIdentifier(email=identifier) if "@" in identifier else SlackUserIdentifier(user_id=identifier)
        return _lookup(self.client, identifier)

    def lookup_channel(self, identifier: str, include_private: bool = False) -> Optional[Dict[str, Any]]:
        """Lookup a Slack channel by ID or name.

        Args:
            identifier: Channel ID (C...) or channel name (#channel-name or channel-name)
            include_private: Also search private channels. Requires the bot to have
                `groups:read` scope. Defaults to False because most bots only have
                `channels:read`, and requesting private channels without the scope
                makes the entire conversations.list call fail.

        Returns:
            Channel dict if found, None otherwise
        """
        from shared_utilities.clients.slack.models.slack_channel import SlackChannel
        if SlackChannel.is_valid_channel_id(identifier):
            try:
                resp = self.client.conversations_info(channel=identifier)
                return resp.get("channel") if resp.get("ok") else None
            except Exception:
                return None

        # Lookup by name
        channel_name = identifier.lstrip("#").lower()
        scope_label = "public + private" if include_private else "public"
        print(f"🔍 Looking up channel by name: '{channel_name}' ({scope_label})")

        channels = self._list_all_channels(include_private=include_private)
        print(f"   Found {len(channels)} accessible channels ({scope_label})")

        result = next((c for c in channels if c.get("name", "").lower() == channel_name), None)

        if result:
            print(f"   ✅ Found: {result.get('name')} ({result.get('id')})")
        else:
            # Debug: show similar channel names
            similar = [c.get("name") for c in channels if channel_name in c.get("name", "").lower()][:5]
            if similar:
                print(f"   ⚠️ Not found. Similar channels: {similar}")
            else:
                print(f"   ⚠️ Not found. No similar channels detected.")

        return result

    def lookup_group(self, identifier: str) -> Optional[Dict[str, Any]]:
        from shared_utilities.clients.slack.services.usergroup_service import UsergroupService
        svc = UsergroupService(self.client)
        if identifier.startswith("S") and len(identifier) == 11 and identifier.isalnum():
            return svc.get_group_by_id(identifier)
        return svc.get_group_by_handle(identifier.lstrip("@"))

    def _list_all_channels(self, include_archived: bool = False, include_private: bool = True) -> List[Dict[str, Any]]:
        """List all channels the bot has access to.

        Args:
            include_archived: Include archived channels (default: False)
            include_private: Include private channels (default: True)

        Returns:
            List of channel dictionaries
        """
        channels: List[Dict[str, Any]] = []
        cursor = None

        # Types to fetch: public channels + private channels (if enabled)
        types = "public_channel,private_channel" if include_private else "public_channel"

        while True:
            try:
                resp = self.client.conversations_list(types=types, cursor=cursor, limit=200)
                if resp.get("ok"):
                    channels.extend(resp.get("channels", []))
                    cursor = resp.get("response_metadata", {}).get("next_cursor")
                    if not cursor:
                        break
                else:
                    print(f"   ⚠️ conversations.list returned not-ok: {resp.get('error')!r}")
                    break
            except Exception as e:
                print(f"   ⚠️ conversations.list failed: {type(e).__name__}: {e}")
                break
        if not include_archived:
            channels = [c for c in channels if not c.get("is_archived")]
        return channels
