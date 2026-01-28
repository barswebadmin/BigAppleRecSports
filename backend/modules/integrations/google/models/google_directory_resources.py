from typing import Optional, Annotated, Literal, TYPE_CHECKING, Any, List
from dataclasses import dataclass
from pydantic import PlainSerializer

from backend.shared.model_config import ApiModel


class EnumField(str):
    """Single enum class with title case conversion."""
    
    @classmethod
    def serialize(cls, value: str) -> str:
        """Serialize enum value to title case string."""
        return value.replace('_', ' ').title()
    
    @classmethod
    def create(cls, *allowed_values: str):
        """Create a validated enum field type with Literal validation."""
        return Annotated[Literal[tuple(allowed_values)], PlainSerializer(cls.serialize)]


class UserName(ApiModel):
    """Google Admin SDK Directory API User name structure."""
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    full_name: Optional[str] = None


class UserEmail(ApiModel):
    """Google Admin SDK Directory API User email structure."""
    address: Optional[str] = None
    primary: Optional[bool] = None


class MemberResource(ApiModel):
    """Google Admin SDK Directory API Member resource structure."""
    kind: str  # 'admin#directory#member'
    etag: str
    id: str
    email: str
    role: EnumField.create('MEMBER', 'OWNER', 'MANAGER')  # type: ignore[misc]
    type: EnumField.create('USER', 'GROUP', 'CUSTOMER', 'EXTERNAL')  # type: ignore[misc]
    status: EnumField.create('ACTIVE', 'ARCHIVED', 'INACTIVE', 'PENDING')  # type: ignore[misc]
    delivery_settings: Optional[EnumField.create('ALL_MAIL', 'DAILY', 'DIGEST', 'NONE', 'DISABLED')] = None  # type: ignore[misc]


class MemberslistResponse(ApiModel):
    """Google Admin SDK Directory API Members list response structure."""
    kind: Optional[str] = None  # 'admin#directory#members'
    etag: Optional[str] = None
    members: Optional[list[MemberResource]] = None
    next_page_token: Optional[str] = None


class GroupResource(ApiModel):
    """Google Admin SDK Directory API Group resource structure."""
    kind: str  # 'admin#directory#group'
    id: str
    etag: str
    email: str
    name: str
    description: str  # Can be empty string
    admin_created: bool
    direct_members_count: str
    aliases: Optional[list[str]] = None  # Can be None or empty list


class GroupslistResponse(ApiModel):
    """Google Admin SDK Directory API Groups list response structure."""
    kind: Optional[str] = None  # 'admin#directory#groups'
    etag: Optional[str] = None
    groups: Optional[list[GroupResource]] = None
    next_page_token: Optional[str] = None


@dataclass
class GroupWithMembers:
    """Result of get_group() containing group and its members."""
    group: GroupResource
    members: list[MemberResource]


class UserResource(ApiModel):
    """Google Admin SDK Directory API User resource structure."""
    kind: Optional[str] = None  # 'admin#directory#user'
    id: Optional[str] = None
    etag: Optional[str] = None
    primary_email: Optional[str] = None
    name: Optional[UserName] = None
    emails: Optional[list[UserEmail]] = None
    aliases: Optional[list[str]] = None
    suspended: Optional[bool] = None
    archived: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_delegated_admin: Optional[bool] = None
    creation_time: Optional[str] = None
    last_login_time: Optional[str] = None
    org_unit_path: Optional[str] = None
    customer_id: Optional[str] = None


class UserslistResponse(ApiModel):
    """Google Admin SDK Directory API Users list response structure."""
    kind: Optional[str] = None  # 'admin#directory#users'
    etag: Optional[str] = None
    users: Optional[list[UserResource]] = None
    next_page_token: Optional[str] = None