"""Slack User models for users.info API responses"""

from typing import List, Optional, Any
from .slack import SlackBase


class SlackUserProfile(SlackBase):
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


class SlackUser(SlackBase):
    """Slack user information from users.info API"""
    id: str
    name: str
    team_id: str
    profile: SlackUserProfile
    deleted: bool = False
    color: Optional[str] = None
    real_name: Optional[str] = None
    tz: Optional[str] = None
    tz_label: Optional[str] = None
    tz_offset: Optional[int] = None
    is_admin: bool = False
    is_owner: bool = False
    is_primary_owner: bool = False
    is_restricted: bool = False
    is_ultra_restricted: bool = False
    is_bot: bool = False
    is_app_user: bool = False
    is_email_confirmed: Optional[bool] = None
    who_can_share_contact_card: Optional[str] = None
    updated: Optional[int] = None
    
    @property
    def email(self) -> Optional[str]:
        """Convenience property for profile.email"""
        return self.profile.email
    
    @property
    def display_name(self) -> str:
        """Convenience property for profile.display_name"""
        return self.profile.display_name

