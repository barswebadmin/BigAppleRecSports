"""Shared Slack client utilities — outgoing messages, models, builders, lookups."""

from .client import SlackClient, BotConfig, Bots, SlackBot
from .client import (
    SlackApiResponse,
    SlackApiSuccessResponse,
    SlackApiErrorResponse,
    SlackUserProfileUpdate,
    BaseChatPayload,
    ChatPostMessagePayload,
    ChatUpdatePayload,
    ChatPostEphemeralPayload,
    UserLookupByEmailPayload,
    UserListPayload,
    SlackUserIdentifier,
)

__all__ = [
    "SlackClient",
    "BotConfig",
    "Bots",
    "SlackBot",
    "SlackApiResponse",
    "SlackApiSuccessResponse",
    "SlackApiErrorResponse",
    "SlackUserProfileUpdate",
    "BaseChatPayload",
    "ChatPostMessagePayload",
    "ChatUpdatePayload",
    "ChatPostEphemeralPayload",
    "UserLookupByEmailPayload",
    "UserListPayload",
    "SlackUserIdentifier",
]
