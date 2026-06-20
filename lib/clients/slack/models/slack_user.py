"""Slack User models for users.info API responses"""

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from shared_utilities.pydantic_config import DEFAULT_CONFIG_DICT


class SlackUserProfile(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
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


class SlackUser(BaseModel):
    model_config = ConfigDict(
        alias_generator=DEFAULT_CONFIG_DICT['alias_generator'],  # pyright: ignore[reportTypedDictNotRequiredAccess]
        populate_by_name=True,
        extra="allow"
    )

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

    def __init__(self, **data):
        if "id" in data:
            user_id = str(data["id"])
            if user_id.startswith("<@") and user_id.endswith(">"):
                data["id"] = user_id[2:-1]
        super().__init__(**data)

    @classmethod
    def create(cls, name: str, user_id: str, **kwargs) -> "SlackUser":
        return cls(name=name, id=user_id, **kwargs)

    @field_validator("id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not v:
            raise ValueError("User ID cannot be empty")
        if v.startswith("@") and not v.startswith("U"):
            return v
        if not v.startswith("U"):
            raise ValueError(f"Invalid Slack user ID: must start with 'U', got '{v}'")
        if len(v) < 3 or len(v) > 20:
            raise ValueError(f"Invalid Slack user ID length: {len(v)}")
        if not v.isalnum():
            raise ValueError(f"Invalid Slack user ID: must be alphanumeric, got '{v}'")
        return v

    @property
    def email(self) -> Optional[str]:
        return self.profile.email if self.profile else None

    @property
    def title(self) -> Optional[str]:
        return self.profile.title if self.profile else None

    @property
    def display_name(self) -> Optional[str]:
        return self.profile.display_name if self.profile else None

    @property
    def phone(self) -> Optional[str]:
        return self.profile.phone if self.profile else None

    @staticmethod
    def is_valid_user_id(user_id: str) -> bool:
        if not user_id or not isinstance(user_id, str):
            return False
        if user_id.startswith("@") and not user_id.startswith("U"):
            return True
        return user_id.startswith("U") and 3 <= len(user_id) <= 20 and user_id.isalnum()


# Constants
Joe = SlackUser.create("joe", "<@U0278M72535>")
Here = SlackUser.create("here", "@here")
