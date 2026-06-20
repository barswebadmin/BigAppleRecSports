"""Slack Channel models for conversations.info API responses"""

from typing import List, Optional, Any
from pydantic import BaseModel, field_validator
from shared_utilities.pydantic_config import DEFAULT_CONFIG_DICT


class SlackChannelPurpose(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Slack channel purpose information"""
    value: str
    creator: str
    last_set: int


class SlackChannelTopic(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Slack channel topic information"""
    value: str
    creator: str
    last_set: int


class SlackChannelTab(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Slack channel tab information"""
    type: str
    label: Optional[str] = None
    id: Optional[str] = None


class SlackChannelProperties(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Slack channel properties"""
    tabs: Optional[List[SlackChannelTab]] = None
    tabz: Optional[List[SlackChannelTab]] = None


class SlackChannel(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Slack channel information from conversations.info API"""
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
        """
        Initialize SlackChannel with name and id.
        
        Args:
            **data: Channel data including 'name' and 'id' (or 'channel_id')
                   - name: Channel name (with or without leading '#')
                   - id or channel_id: Channel ID
                   - Additional fields from API response
        """
        # Handle both 'id' and 'channel_id' parameter names
        if 'channel_id' in data and 'id' not in data:
            data['id'] = data.pop('channel_id')
        
        # Normalize name (remove leading # if present)
        if 'name' in data:
            normalized_name = str(data['name']).lstrip('#')
            data['name'] = normalized_name
            
            # Set name_normalized if not provided
            if 'name_normalized' not in data:
                data['name_normalized'] = normalized_name
        
        super().__init__(**data)
    
    @classmethod
    def create(cls, name: str, channel_id: str, **kwargs) -> 'SlackChannel':
        """
        Factory method to create a SlackChannel instance.
        
        Args:
            name: Channel name (with or without leading '#')
            channel_id: Channel ID
            **kwargs: Additional fields from API response
            
        Returns:
            SlackChannel instance
            
        Example:
            >>> channel = SlackChannel.create("#joe-test", "C092RU7R6PL")
        """
        return cls(name=name, id=channel_id, **kwargs)
    
    @field_validator('id')
    @classmethod
    def validate_channel_id(cls, v: str) -> str:
        """Validate that channel ID follows Slack format: starts with C, 11 chars, alphanumeric."""
        if not v:
            raise ValueError("Channel ID cannot be empty")
        if not v.startswith('C'):
            raise ValueError(f"Invalid Slack channel ID: must start with 'C', got '{v}'")
        if len(v) < 9 or len(v) > 13:
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


# ============================================================================
# Channel Constants
# ============================================================================

JoeTest = SlackChannel.create("#joe-test", "C092RU7R6PL")
Registrations = SlackChannel.create("#registrations", "C08J1EN7SFR")
RegistrationRefunds = SlackChannel.create("#registration-refunds", "C08J1EN7SFR")
Web = SlackChannel.create("#web", "C02KAENF6")

