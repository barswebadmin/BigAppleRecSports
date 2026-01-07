"""Slack Channel models for conversations.info API responses"""

from typing import List, Optional, Any
from pydantic import field_validator
from shared.model_config import ApiModel


class SlackChannelPurpose(ApiModel):
    """Slack channel purpose information"""
    value: str
    creator: str
    last_set: int


class SlackChannelTopic(ApiModel):
    """Slack channel topic information"""
    value: str
    creator: str
    last_set: int


class SlackChannelTab(ApiModel):
    """Slack channel tab information"""
    type: str
    label: Optional[str] = None
    id: Optional[str] = None


class SlackChannelProperties(ApiModel):
    """Slack channel properties"""
    tabs: Optional[List[SlackChannelTab]] = None
    tabz: Optional[List[SlackChannelTab]] = None


class SlackChannel(ApiModel):
    """Slack channel information from conversations.info API"""
    id: str
    name: str
    name_normalized: str
    created: int
    creator: str
    is_channel: bool
    is_group: bool
    is_im: bool
    is_mpim: bool
    is_private: bool
    is_archived: bool
    is_general: bool
    is_shared: bool
    is_org_shared: bool
    is_ext_shared: bool
    is_pending_ext_shared: bool
    is_member: bool
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
    
    @field_validator('id')
    @classmethod
    def validate_channel_id(cls, v: str) -> str:
        """Validate that channel ID follows Slack format: starts with C, 11 chars, alphanumeric."""
        if not v:
            raise ValueError("Channel ID cannot be empty")
        if not v.startswith('C'):
            raise ValueError(f"Invalid Slack channel ID: must start with 'C', got '{v}'")
        if len(v) != 11:
            raise ValueError(f"Invalid Slack channel ID: must be 11 characters, got {len(v)} characters")
        if not v.isalnum():
            raise ValueError(f"Invalid Slack channel ID: must be alphanumeric, got '{v}'")
        return v
    
    @staticmethod
    def is_valid_channel_id(channel_id: str) -> bool:
        """
        Check if a string is a valid Slack channel ID format.
        
        Args:
            channel_id: String to validate
            
        Returns:
            True if valid Slack channel ID format, False otherwise
            
        Example:
            >>> SlackChannel.is_valid_channel_id("C092RU7R6PL")
            True
            >>> SlackChannel.is_valid_channel_id("invalid")
            False
        """
        if not channel_id or not isinstance(channel_id, str):
            return False
        return channel_id.startswith('C') and len(channel_id) == 11 and channel_id.isalnum()

