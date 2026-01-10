"""
Google Directory API Client.

Handles authentication and managing Google Workspace directory resources (groups, users, members)
using Service Account credentials with domain-wide delegation.
"""

import logging
from typing import Optional, Annotated, Literal
from dataclasses import dataclass

from pydantic import PlainSerializer
from googleapiclient.errors import HttpError

from backend.shared.model_config import ApiModel

from .base_client import GoogleAPIClient, GoogleServiceAccountInfo, handle_http_errors


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

logger = logging.getLogger(__name__)


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


class GoogleDirectoryClient(GoogleAPIClient):
    """Client for interacting with Google Admin SDK Directory API (groups, users, members)."""
    
    def __init__(self, service_account_info: Optional[GoogleServiceAccountInfo] = None, subject: Optional[str] = None):
        """
        Initialize Google Directory client with service account credentials.
        
        Args:
            service_account_info: Service account JSON dict.
                                If None, uses config.GOOGLE.SERVICE_ACCOUNT.
            subject: Email address of the user to impersonate (required for domain-wide delegation).
                    If None, uses service account directly (may have limited permissions).
        
        Raises:
            ValueError: If credentials are missing or invalid
        
        Note:
            For Google Workspace group management, you typically need:
            1. Service account with domain-wide delegation enabled
            2. Admin to authorize scopes in Google Admin Console
            3. Subject parameter set to an admin user email
        """
        self.scopes = [
            'https://www.googleapis.com/auth/admin.directory.group',
            'https://www.googleapis.com/auth/admin.directory.group.member',
            'https://www.googleapis.com/auth/admin.directory.user.readonly',
        ]
        if subject is None:
            logger.warning(
                "⚠️ No subject provided for domain-wide delegation. "
                "Set GOOGLE.SUBJECT in your .env file or add 'subject' field to google-service-account.json. "
                "Some operations may fail without proper delegation."
            )
        super().__init__(service_account_info=service_account_info, subject=subject)
        self.service = self._build_service('admin', 'directory_v1')
    
    @handle_http_errors
    def list_all_users(
        self,
        max_results: int = 500
    ) -> list[UserResource]:
        """
        list all users in the organization.
        
        Args:
            max_results: Maximum number of results per page (default: 500, max: 500)
        
        Returns:
            list of UserResource Pydantic models, each with primary_email, name, id, etc.
        
        Raises:
            HttpError: For Google API errors
        
        Example:
            >>> client = GoogleDirectoryClient(subject="admin@example.com")
            >>> users = client.list_all_users()
            >>> print(f"Found {len(users)} users")
            >>> for user in users:
            ...     print(f"{user.primary_email}: {user.name.full_name if user.name else 'N/A'}")
        """
        params = {
            'customer': 'my_customer',
            'maxResults': min(max_results, 500)
        }
        
        users_dicts = self._paginate_api_call(
            self.service.users().list,
            result_key='users',
            **params
        )
        
        # Convert dicts to Pydantic models
        users = [UserResource(**user_dict) for user_dict in users_dicts]
        
        logger.info(f"✅ Found {len(users)} users")
        
        return users
    
    @handle_http_errors
    def get_user(
        self,
        user_email: str
    ) -> UserResource:
        """
        Get a Google Workspace user by email address.
        
        Args:
            user_email: Email address of the user (e.g., "user@example.com")
        
        Returns:
            UserResource Pydantic model with user information (primary_email, name, id, etc.)
        
        Raises:
            HttpError: For Google API errors (including 404 if user not found)
        
        Example:
            >>> client = GoogleDirectoryClient(subject="admin@example.com")
            >>> user = client.get_user("user@example.com")
            >>> print(f"User: {user.primary_email} - {user.name.full_name if user.name else 'N/A'}")
        """
        user_dict = self.service.users().get(userKey=user_email).execute()  # type: ignore[attr-defined]
        user = UserResource(**user_dict)
        
        logger.info(f"✅ Found user: {user.primary_email}")
        
        return user
    
    @handle_http_errors
    def list_all_groups(
        self
    ) -> list[GroupResource]:
        """
        list all groups in the organization.
        
        Returns:
            list of GroupResource Pydantic models, each with email, name, id, etc.
        
        Raises:
            HttpError: For Google API errors
        
        Example:
            >>> client = GoogleDirectoryClient(subject="admin@example.com")
            >>> groups = client.list_all_groups()
            >>> print(f"Found {len(groups)} groups")
            >>> for group in groups:
            ...     print(f"{group.email}: {group.name}")
        """
        params = {'customer': 'my_customer'}
        
        groups_dicts = self._paginate_api_call(
            self.service.groups().list,
            result_key='groups',
            **params
        )
        
        # Convert dicts to Pydantic models
        groups = [GroupResource(**group_dict) for group_dict in groups_dicts]
        
        logger.info(f"✅ Found {len(groups)} groups")
        
        return groups
    
    @handle_http_errors
    def get_group(
        self,
        group_email: str,
        include_members: bool = True
    ) -> GroupWithMembers:
        """
        Get a Google Group by email address, optionally including members.
        
        Args:
            group_email: Email address of the group (e.g., "team@example.com")
            include_members: If True, also fetch and include group members (default: True)
        
        Returns:
            GroupWithMembers dataclass containing:
            - group: GroupResource Pydantic model
            - members: list of MemberResource objects (empty list if include_members=False or error)
        
        Raises:
            HttpError: For Google API errors
        
        Example:
            >>> client = GoogleDirectoryClient(subject="admin@example.com")
            >>> result = client.get_group("team@example.com")
            >>> group = result.group
            >>> members = result.members
            >>> print(f"Group {group.email} has {len(members)} members")
        """
        # Get group using Google Directory API
        group_dict = self.service.groups().get(groupKey=group_email).execute()  # type: ignore[attr-defined]
        group = GroupResource(**group_dict)
        
        # Get members if requested
        members: list[MemberResource] = []
        if include_members:
            try:
                members = self.list_group_members(group_email)
            except Exception as e:
                # Log but don't fail if member listing fails
                logger.warning(f"⚠️  Could not list members for {group_email}: {e}")
                members = []
        
        return GroupWithMembers(group=group, members=members)
    
    @handle_http_errors
    def list_group_members(
        self,
        group_email: str,
        roles: Optional[list[str]] = None
    ) -> list[MemberResource]:
        """
        list all members of a Google Group (with pagination).
        
        Args:
            group_email: Email address of the group (e.g., "team@example.com")
            roles: Optional list of roles to filter by: "MEMBER", "OWNER", "MANAGER"
                  If None, returns all members regardless of role
        
        Returns:
            list of MemberResource Pydantic models, each with email, role, type, etc.
        
        Raises:
            HttpError: For Google API errors
        
        Example:
            >>> client = GoogleDirectoryClient(subject="admin@example.com")
            >>> members = client.list_all_members("team@example.com")
            >>> print(f"Group has {len(members)} members")
            >>> owners = client.list_all_members("team@example.com", roles=["OWNER"])
        """
        params = {'groupKey': group_email}
        if roles:
            params['roles'] = ','.join(roles)
        
        members_dicts = self._paginate_api_call(
            self.service.members().list,
            result_key='members',
            **params
        )
        
        # Convert dicts to Pydantic models
        members = [MemberResource(**member_dict) for member_dict in members_dicts]
        
        logger.info(
            f"✅ Found {len(members)} members in group {group_email}"
        )
        
        return members
    
    @handle_http_errors
    def add_member_to_group(
        self,
        group_email: str,
        user_email: str,
        role: str = 'MEMBER'
    ) -> MemberResource:
        """
        Add a user to a Google Group.
        
        Args:
            group_email: Email address of the group (e.g., "team@example.com")
            user_email: Email address of the user to add
            role: Member role - "MEMBER", "OWNER", or "MANAGER" (default: "MEMBER")
        
        Returns:
            MemberResource Pydantic model with member information (email, role, id, etc.)
        
        Raises:
            HttpError: For Google API errors
        
        Example:
            >>> client = GoogleDirectoryClient(subject="admin@example.com")
            >>> result = client.add_member_to_group("team@example.com", "user@example.com")
            >>> print(f"Added {result.email} to group")
        """
        member_body = {
            'email': user_email,
            'role': role
        }
        
        result_dict = self.service.members().insert(
            groupKey=group_email,
            body=member_body
        ).execute()
        
        # Convert dict to Pydantic model
        result = MemberResource(**result_dict)
        
        logger.info(
            f"✅ Added {user_email} to group {group_email} with role {role}"
        )
        
        return result
    
    @handle_http_errors
    def remove_member_from_group(
        self,
        group_email: str,
        user_email: str
    ) -> None:
        """
        Remove a user from a Google Group.
        
        Args:
            group_email: Email address of the group (e.g., "team@example.com")
            user_email: Email address of the user to remove
        
        Raises:
            HttpError: For Google API errors
        
        Example:
            >>> client = GoogleDirectoryClient(subject="admin@example.com")
            >>> client.remove_member_from_group("team@example.com", "user@example.com")
        """
        self.service.members().delete(
            groupKey=group_email,
            memberKey=user_email
        ).execute()
        
        logger.info(
            f"✅ Removed {user_email} from group {group_email}"
        )
    
    def is_member_of_group(
        self,
        group_email: str,
        user_email: str
    ) -> bool:
        """
        Check if a user is a member of a Google Group.
        
        Args:
            group_email: Email address of the group
            user_email: Email address of the user to check
        
        Returns:
            True if user is a member, False otherwise
        
        Raises:
            HttpError: For Google API errors (except 404, which returns False)
        
        Example:
            >>> client = GoogleDirectoryClient(subject="admin@example.com")
            >>> if client.is_member_of_group("team@example.com", "user@example.com"):
            ...     print("User is a member")
        """
        try:
            result_dict = self.service.members().get(
                groupKey=group_email,
                memberKey=user_email
            ).execute()
            # Convert dict to Pydantic model (not used, but validates response)
            MemberResource(**result_dict)
            return True
        except HttpError as e:
            if e.resp.status == 404:
                return False
            self._raise_for_status(e)

