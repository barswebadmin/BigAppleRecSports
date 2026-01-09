"""
Google Directory API Client.

Handles authentication and managing Google Workspace directory resources (groups, users, members)
using Service Account credentials with domain-wide delegation.
"""

import logging
from typing import List, Optional, Dict, Any, TypedDict, Literal

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .base_client import GoogleAPIClient, handle_http_errors

# Google Groups member roles
GroupMemberRole = Literal["MEMBER", "OWNER", "MANAGER"]

logger = logging.getLogger(__name__)


class MemberResource(TypedDict, total=False):
    """Google Admin SDK Directory API Member resource structure."""
    kind: str  # 'admin#directory#member'
    etag: str
    id: str
    email: str
    role: str  # 'MEMBER', 'OWNER', 'MANAGER'
    type: str  # 'USER', 'GROUP', 'CUSTOMER', 'EXTERNAL'
    status: str  # 'ACTIVE', 'ARCHIVED', etc.
    delivery_settings: str  # 'ALL_MAIL', 'DAILY', 'DIGEST', 'NONE'


class MembersListResponse(TypedDict, total=False):
    """Google Admin SDK Directory API Members list response structure."""
    kind: str  # 'admin#directory#members'
    etag: str
    members: List[MemberResource]
    nextPageToken: str


class GroupResource(TypedDict, total=False):
    """Google Admin SDK Directory API Group resource structure."""
    kind: str  # 'admin#directory#group'
    id: str
    etag: str
    email: str
    name: str
    description: str
    adminCreated: bool
    directMembersCount: str
    aliases: List[str]


class GroupsListResponse(TypedDict, total=False):
    """Google Admin SDK Directory API Groups list response structure."""
    kind: str  # 'admin#directory#groups'
    etag: str
    groups: List[GroupResource]
    nextPageToken: str


class UserResource(TypedDict, total=False):
    """Google Admin SDK Directory API User resource structure."""
    kind: str  # 'admin#directory#user'
    id: str
    etag: str
    primaryEmail: str
    name: Dict[str, str]  # {'givenName': str, 'familyName': str, 'fullName': str}
    emails: List[Dict[str, str]]
    aliases: List[str]
    suspended: bool
    archived: bool
    isAdmin: bool
    isDelegatedAdmin: bool
    creationTime: str
    lastLoginTime: str
    orgUnitPath: str
    customerId: str


class UsersListResponse(TypedDict, total=False):
    """Google Admin SDK Directory API Users list response structure."""
    kind: str  # 'admin#directory#users'
    etag: str
    users: List[UserResource]
    nextPageToken: str


class GoogleDirectoryClient(GoogleAPIClient):
    """Client for interacting with Google Admin SDK Directory API (groups, users, members)."""
    
    def __init__(self, service_account_info: Optional[Dict[str, Any]] = None, subject: Optional[str] = None):
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
                "⚠️ No subject provided. Group management may fail without domain-wide delegation."
            )
        super().__init__(service_account_info=service_account_info, subject=subject)
        self.service = self._build_service('admin', 'directory_v1')
    
    @handle_http_errors
    def list_all_users(
        self,
        max_results: int = 500
    ) -> List[UserResource]:
        """
        List all users in the organization.
        
        Args:
            max_results: Maximum number of results per page (default: 500, max: 500)
        
        Returns:
            List of UserResource dictionaries, each with 'primaryEmail', 'name', 'id', etc.
        
        Raises:
            HttpError: For Google API errors
        
        Example:
            >>> client = GoogleDirectoryClient(subject="admin@example.com")
            >>> users = client.list_all_users()
            >>> print(f"Found {len(users)} users")
            >>> for user in users:
            ...     print(f"{user['primaryEmail']}: {user['name'].get('fullName', 'N/A')}")
        """
        params = {
            'customer': 'my_customer',
            'maxResults': min(max_results, 500)
        }
        
        users = self._paginate_api_call(
            self.service.users().list,
            result_key='users',
            **params
        )
        
        logger.info(f"✅ Found {len(users)} users")
        
        return users
    
    @handle_http_errors
    def list_all_groups(
        self
    ) -> List[GroupResource]:
        """
        List all groups in the organization.
        
        Returns:
            List of GroupResource dictionaries, each with 'email', 'name', 'id', etc.
        
        Raises:
            HttpError: For Google API errors
        
        Example:
            >>> client = GoogleDirectoryClient(subject="admin@example.com")
            >>> groups = client.list_all_groups()
            >>> print(f"Found {len(groups)} groups")
            >>> for group in groups:
            ...     print(f"{group['email']}: {group['name']}")
        """
        params = {'customer': 'my_customer'}
        
        groups = self._paginate_api_call(
            self.service.groups().list,
            result_key='groups',
            **params
        )
        
        logger.info(f"✅ Found {len(groups)} groups")
        
        return groups
    
    @handle_http_errors
    def list_group_members(
        self,
        group_email: str,
        roles: Optional[List[GroupMemberRole]] = None
    ) -> List[MemberResource]:
        """
        List all members of a Google Group (with pagination).
        
        Args:
            group_email: Email address of the group (e.g., "team@example.com")
            roles: Optional list of roles to filter by: "MEMBER", "OWNER", "MANAGER"
                  If None, returns all members regardless of role
        
        Returns:
            List of MemberResource dictionaries, each with 'email', 'role', 'type', etc.
        
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
        
        members = self._paginate_api_call(
            self.service.members().list,
            result_key='members',
            **params
        )
        
        logger.info(
            f"✅ Found {len(members)} members in group {group_email}"
        )
        
        return members
    
    @handle_http_errors
    def add_member_to_group(
        self,
        group_email: str,
        user_email: str,
        role: GroupMemberRole = "MEMBER"
    ) -> MemberResource:
        """
        Add a user to a Google Group.
        
        Args:
            group_email: Email address of the group (e.g., "team@example.com")
            user_email: Email address of the user to add
            role: Member role - "MEMBER", "OWNER", or "MANAGER" (default: "MEMBER")
        
        Returns:
            MemberResource dictionary with member information (email, role, id, etc.)
        
        Raises:
            HttpError: For Google API errors
        
        Example:
            >>> client = GoogleDirectoryClient(subject="admin@example.com")
            >>> result = client.add_member_to_group("team@example.com", "user@example.com")
            >>> print(f"Added {result['email']} to group")
        """
        member_body = {
            'email': user_email,
            'role': role
        }
        
        result: MemberResource = self.service.members().insert(
            groupKey=group_email,
            body=member_body
        ).execute()
        
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
            result: MemberResource = self.service.members().get(
                groupKey=group_email,
                memberKey=user_email
            ).execute()
            return True
        except HttpError as e:
            if e.resp.status == 404:
                return False
            self._raise_for_status(e)

