"""Slack User models for users.info API responses"""

from typing import List, Optional, Any
from pydantic import field_validator, ConfigDict
from backend.shared.model_config import ApiModel


class SlackUserProfile(ApiModel):
    """Slack user profile information from users.info API"""
    real_name: str
    display_name: str
    real_name_normalized: Optional[str] = None
    display_name_normalized: Optional[str] = None
    avatar_hash: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    pronouns: Optional[str] = None
    skype: Optional[str] = None
    team: Optional[str] = None
    image_24: Optional[str] = None
    image_32: Optional[str] = None
    image_48: Optional[str] = None
    image_72: Optional[str] = None
    image_192: Optional[str] = None
    image_512: Optional[str] = None
    image_1024: Optional[str] = None
    image_original: Optional[str] = None
    is_custom_image: Optional[bool] = None
    status_text: Optional[str] = None
    status_text_canonical: Optional[str] = None
    status_emoji: Optional[str] = None
    status_emoji_display_info: Optional[List[Any]] = None
    status_expiration: Optional[int] = None
    huddle_state: Optional[str] = None
    huddle_state_expiration_ts: Optional[int] = None


class SlackUser(ApiModel):
    """
    Slack user information from users.info API.
    
    Only essential fields are required. All other fields are optional without defaults,
    allowing distinction between API-provided values and default values.
    Extra fields from API responses are preserved via extra='allow'.
    
    Use model_fields_set to check which fields were actually provided in the API response.
    """
    model_config = ConfigDict(extra='allow')
    
    id: str
    name: str
    team_id: Optional[str] = None
    profile: Optional[SlackUserProfile] = None
    deleted: Optional[bool] = None
    is_bot: Optional[bool] = None
    color: Optional[str] = None
    real_name: Optional[str] = None
    tz: Optional[str] = None
    tz_label: Optional[str] = None
    tz_offset: Optional[int] = None
    is_admin: Optional[bool] = None
    is_owner: Optional[bool] = None
    is_primary_owner: Optional[bool] = None
    is_restricted: Optional[bool] = None
    is_ultra_restricted: Optional[bool] = None
    is_app_user: Optional[bool] = None
    is_email_confirmed: Optional[bool] = None
    who_can_share_contact_card: Optional[str] = None
    updated: Optional[int] = None
    
    # Nested accessors for common profile fields
    __nested_accessors__ = {
        'email': 'profile.email',
        'display_name': 'profile.display_name',
        'title': 'profile.title',
        'phone': 'profile.phone',
        'first_name': 'profile.first_name',
        'last_name': 'profile.last_name',
        'pronouns': 'profile.pronouns',
        'real_name_from_profile': 'profile.real_name',
    }
    
    def __init__(self, **data):
        """
        Initialize SlackUser with id and name.
        
        Args:
            **data: User data including 'id' and 'name'
                   - id: User ID or mention (e.g., "U0278M72535" or "<@U0278M72535>" or "@here")
                   - name: User name (e.g., "joe" or "here")
                   - Additional fields from API response
        """
        # Extract user ID from mention format if needed (e.g., "<@U0278M72535>" -> "U0278M72535")
        if 'id' in data:
            user_id = str(data['id'])
            # Handle mention format: "<@U0278M72535>" -> "U0278M72535"
            if user_id.startswith('<@') and user_id.endswith('>'):
                data['id'] = user_id[2:-1]
            # Handle @here, @channel, etc. - keep as-is
            elif user_id.startswith('@') and not user_id.startswith('U'):
                data['id'] = user_id
        
        super().__init__(**data)
    
    @classmethod
    def create(cls, name: str, user_id: str, **kwargs) -> 'SlackUser':
        """
        Factory method to create a SlackUser instance.
        
        Args:
            name: User name (e.g., "joe" or "here")
            user_id: User ID or mention (e.g., "U0278M72535" or "<@U0278M72535>" or "@here")
            **kwargs: Additional fields from API response
            
        Returns:
            SlackUser instance
            
        Example:
            >>> user = SlackUser.create("joe", "<@U0278M72535>")
            >>> user = SlackUser.create("here", "@here")
        """
        return cls(name=name, id=user_id, **kwargs)
    
    @field_validator('id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """
        Validate that user ID follows Slack format: starts with U, alphanumeric, reasonable length.
        Special cases like "@here" are allowed.
        """
        if not v:
            raise ValueError("User ID cannot be empty")
        # Allow special mentions like @here, @channel, etc.
        if v.startswith('@') and not v.startswith('U'):
            return v
        # Validate standard user ID format
        if not v.startswith('U'):
            raise ValueError(f"Invalid Slack user ID: must start with 'U' or be a special mention like '@here', got '{v}'")
        if len(v) < 3:
            raise ValueError(f"Invalid Slack user ID: too short (minimum 3 characters), got {len(v)} characters")
        if len(v) > 20:
            raise ValueError(f"Invalid Slack user ID: too long (maximum 20 characters), got {len(v)} characters")
        if not v.isalnum():
            raise ValueError(f"Invalid Slack user ID: must be alphanumeric, got '{v}'")
        return v
    
    @property
    def email(self) -> Optional[str]:
        """Safely access profile email."""
        return self.profile.email if self.profile else None
    
    @property
    def title(self) -> Optional[str]:
        """Safely access profile title."""
        return self.profile.title if self.profile else None
    
    @property
    def display_name(self) -> Optional[str]:
        """Safely access profile display_name."""
        return self.profile.display_name if self.profile else None
    
    @property
    def phone(self) -> Optional[str]:
        """Safely access profile phone."""
        return self.profile.phone if self.profile else None
    
    @staticmethod
    def is_valid_user_id(user_id: str) -> bool:
        """
        Check if a string is a valid Slack user ID format.
        
        Args:
            user_id: String to validate
            
        Returns:
            True if valid Slack user ID format, False otherwise
            
        Example:
            >>> SlackUser.is_valid_user_id("U03LZKQSHEU")
            True
            >>> SlackUser.is_valid_user_id("USLACKBOT")
            True
            >>> SlackUser.is_valid_user_id("@here")
            True
            >>> SlackUser.is_valid_user_id("invalid")
            False
        """
        if not user_id or not isinstance(user_id, str):
            return False
        # Allow special mentions like @here, @channel, etc.
        if user_id.startswith('@') and not user_id.startswith('U'):
            return True
        return (user_id.startswith('U') and 
                3 <= len(user_id) <= 20 and 
                user_id.isalnum())


# ============================================================================
# User Constants
# ============================================================================

Joe = SlackUser.create("joe", "<@U0278M72535>")
Here = SlackUser.create("here", "@here")

