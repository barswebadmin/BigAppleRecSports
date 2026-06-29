"""Slack Channel models for conversations.info API responses"""

from typing import Any, List, Optional

from pydantic import BaseModel, field_validator

from shared_utilities.pydantic_config import DEFAULT_CONFIG_DICT


class SlackChannelPurpose(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    value: str
    creator: str
    last_set: int


class SlackChannelTopic(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    value: str
    creator: str
    last_set: int


class SlackChannelTab(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    type: str
    label: Optional[str] = None
    id: Optional[str] = None


class SlackChannelProperties(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    tabs: Optional[List[SlackChannelTab]] = None
    tabz: Optional[List[SlackChannelTab]] = None


class SlackChannel(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    id: str
    name: str
    name_normalized: Optional[str] = None
    created: Optional[int] = None
    creator: Optional[str] = None
    is_channel: Optional[bool] = None
    is_group: Optional[bool] = None
    is_im: Optional[bool] = None
    is_mpim: Optional[bool] = None
    is_private: Optional[bool] = None
    is_archived: Optional[bool] = None
    is_general: Optional[bool] = None
    is_shared: Optional[bool] = None
    is_org_shared: Optional[bool] = None
    is_ext_shared: Optional[bool] = None
    is_pending_ext_shared: Optional[bool] = None
    is_member: Optional[bool] = None
    context_team_id: Optional[str] = None
    updated: Optional[int] = None
    unlinked: Optional[int] = None
    parent_conversation: Optional[str] = None
    shared_team_ids: Optional[List[str]] = None
    pending_shared: Optional[List[Any]] = None
    pending_connected_team_ids: Optional[List[str]] = None
    last_read: Optional[str] = None
    previous_names: Optional[List[str]] = None
    purpose: Optional[SlackChannelPurpose] = None
    topic: Optional[SlackChannelTopic] = None
    properties: Optional[SlackChannelProperties] = None

    def __init__(self, **data):
        if "channel_id" in data and "id" not in data:
            data["id"] = data.pop("channel_id")
        if "name" in data:
            normalized = str(data["name"]).lstrip("#")
            data["name"] = normalized
            if "name_normalized" not in data:
                data["name_normalized"] = normalized
        super().__init__(**data)

    @classmethod
    def create(cls, name: str, channel_id: str, **kwargs) -> "SlackChannel":
        return cls(name=name, id=channel_id, **kwargs)

    @field_validator("id")
    @classmethod
    def validate_channel_id(cls, v: str) -> str:
        if not v:
            raise ValueError("Channel ID cannot be empty")
        if not v.startswith("C"):
            raise ValueError(f"Invalid Slack channel ID: must start with 'C', got '{v}'")
        if not (9 <= len(v) <= 13):
            raise ValueError(f"Invalid Slack channel ID length: {len(v)}")
        if not v.isalnum():
            raise ValueError(f"Invalid Slack channel ID: must be alphanumeric, got '{v}'")
        return v

    @staticmethod
    def is_valid_channel_id(channel_id: str) -> bool:
        if not channel_id or not isinstance(channel_id, str):
            return False
        return channel_id.startswith("C") and len(channel_id) == 11 and channel_id.isalnum()


# Constants
JoeTest = SlackChannel.create("#joe-test", "C092RU7R6PL")
Registrations = SlackChannel.create("#registrations", "C08J1EN7SFR")
RegistrationRefunds = SlackChannel.create("#registration-refunds", "C08J1EN7SFR")
Web = SlackChannel.create("#web", "C02KAENF6")
