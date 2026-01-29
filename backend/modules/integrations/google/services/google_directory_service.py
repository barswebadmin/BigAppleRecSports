"""
Google Directory API service methods and models.

Contains Directory-specific functionality: models, methods, and helper functions.
"""

import logging
from typing import Optional, Annotated, Literal, TYPE_CHECKING, Any, List
from dataclasses import dataclass

from googleapiclient.errors import HttpError

from backend.modules.integrations.google.services._google_api_service_builder import build_google_api_service
from backend.modules.integrations.google.base_methods import handle_http_errors, paginate_api_call
from backend.modules.integrations.google.models.google_directory_resources import GroupResource, MemberResource, UserResource, GroupWithMembers

logger = logging.getLogger(__name__)


@dataclass
class AddMemberResult:
    """Result of adding a member to a group."""
    member: MemberResource
    warning: Optional[str] = None  # If set, indicates a warning (e.g., member already exists)
    
    @property
    def is_warning(self) -> bool:
        """Returns True if this result represents a warning."""
        return self.warning is not None


class GoogleDirectoryService():
    """Google Directory API service methods.
    
    Provides methods for interacting with Google Workspace Directory API.
    Uses paginate_api_call() from base_methods for pagination.
    """
    
    if TYPE_CHECKING:
        def _raise_for_status(self, error: HttpError) -> None: ...
    

    def __init__(self):
        
        required_scopes = [
            'https://www.googleapis.com/auth/admin.directory.group',
            'https://www.googleapis.com/auth/admin.directory.group.member',
            # 'https://www.googleapis.com/auth/admin.directory.user.readonly',
            'https://www.googleapis.com/auth/admin.directory.user',
        ]

        self.service = build_google_api_service('admin', 'directory_v1', required_scopes)
        self.required_scopes = required_scopes  # Store for error diagnostics
        # Store callables, not the Resource objects
        self.users = self.service.users  # type: ignore[attr-defined]
        self.groups = self.service.groups  # type: ignore[attr-defined]
        self.members = self.service.members  # type: ignore[attr-defined]
    

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
            >>> client = GoogleApiClient(subject="admin@example.com")
            >>> users = client.list_all_users()
            >>> print(f"Found {len(users)} users")
            >>> for user in users:
            ...     print(f"{user.primary_email}: {user.name.full_name if user.name else 'N/A'}")
        """
        params = {
            'customer': 'my_customer',
            'maxResults': min(max_results, 500)
        }
        
        users_dicts = paginate_api_call(
            self.users().list,
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
            >>> client = GoogleApiClient(subject="admin@example.com")
            >>> user = client.get_user("user@example.com")
            >>> print(f"User: {user.primary_email} - {user.name.full_name if user.name else 'N/A'}")
        """
        user_dict = self.users().get(userKey=user_email).execute()  # type: ignore[attr-defined]
        user = UserResource(**user_dict)
        
        logger.info(f"✅ Found user: {user.primary_email}")
        
        return user
    
    @handle_http_errors
    def create_user(
        self,
        primary_email: str,
        given_name: str,
        family_name: str,
        recovery_email: Optional[str] = None,
        password: Optional[str] = None,
        change_password_at_next_login: bool = True,
        org_unit_path: Optional[str] = None
    ) -> UserResource:
        """
        Create a new Google Workspace user.
        
        Args:
            primary_email: Primary email address for the user (e.g., "user@example.com")
            given_name: User's first/given name
            family_name: User's last/family name
            recovery_email: Optional recovery/backup email address for account recovery
            password: Optional password. If not provided, user will be required to set password on first login.
            change_password_at_next_login: Whether user must change password on next login (default: True)
            org_unit_path: Optional organizational unit path (e.g., "/Staff" or "/Students")
        
        Returns:
            UserResource Pydantic model with created user information
        
        Raises:
            HttpError: For Google API errors (including 409 if user already exists, 400 for invalid data)
        
        Example:
            >>> client = GoogleApiClient(subject="admin@example.com")
            >>> user = client.create_user(
            ...     primary_email="newuser@example.com",
            ...     given_name="John",
            ...     family_name="Doe",
            ...     recovery_email="backup@example.com"
            ... )
            >>> print(f"Created user: {user.primary_email}")
        """
        user_body = {
            'primaryEmail': primary_email,
            'name': {
                'givenName': given_name,
                'familyName': family_name
            },
            'changePasswordAtNextLogin': change_password_at_next_login
        }
        
        if recovery_email:
            user_body['recoveryEmail'] = recovery_email
        
        if password:
            user_body['password'] = password
        
        if org_unit_path:
            user_body['orgUnitPath'] = org_unit_path
        
        user_dict = self.users().insert(body=user_body).execute()  # type: ignore[attr-defined]
        user = UserResource(**user_dict)
        
        logger.info(f"✅ Created user: {user.primary_email}")
        
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
            >>> client = GoogleApiClient(subject="admin@example.com")
            >>> groups = client.list_all_groups()
            >>> print(f"Found {len(groups)} groups")
            >>> for group in groups:
            ...     print(f"{group.email}: {group.name}")
        """
        params = {'customer': 'my_customer'}
        
        groups_dicts = paginate_api_call(
            self.groups().list,
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
            >>> client = GoogleApiClient(subject="admin@example.com")
            >>> result = client.get_group("team@example.com")
            >>> group = result.group
            >>> members = result.members
            >>> print(f"Group {group.email} has {len(members)} members")
        """
        # Get group using Google Directory API
        group_dict = self.groups().get(groupKey=group_email).execute()  # type: ignore[attr-defined]
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
            >>> client = GoogleApiClient(subject="admin@example.com")
            >>> members = client.list_group_members("team@example.com")
            >>> print(f"Group has {len(members)} members")
            >>> owners = client.list_group_members("team@example.com", roles=["OWNER"])
        """
        params = {'groupKey': group_email}
        if roles:
            params['roles'] = ','.join(roles)
        
        members_dicts = paginate_api_call(
            self.members().list,
            result_key='members',
            **params
        )
        
        # Convert dicts to Pydantic models
        members = [MemberResource(**member_dict) for member_dict in members_dicts]
        
        logger.info(
            f"✅ Found {len(members)} members in group {group_email}"
        )
        
        return members
    
    def add_member_to_group(
        self,
        group_email: str,
        user_email: str,
        role: str = 'MEMBER'
    ) -> AddMemberResult:
        """
        Add a user to a Google Group.
        
        Args:
            group_email: Email address of the group (e.g., "team@example.com")
            user_email: Email address of the user to add
            role: Member role - "MEMBER", "OWNER", or "MANAGER" (default: "MEMBER")
        
        Returns:
            AddMemberResult containing:
            - member: MemberResource with member information
            - warning: Optional warning message (e.g., if member already exists)
        
        Raises:
            HttpError: For Google API errors other than 409 (member already exists)
        
        Example:
            >>> client = GoogleApiClient(subject="admin@example.com")
            >>> result = client.add_member_to_group("team@example.com", "user@example.com")
            >>> if result.is_warning:
            ...     print(f"Warning: {result.warning}")
            >>> print(f"Member: {result.member.email}")
        """
        member_body = {
            'email': user_email,
            'role': role
        }
        
        try:
            result_dict = self.members().insert(
                groupKey=group_email,
                body=member_body
            ).execute()
            
            # Convert dict to Pydantic model
            member = MemberResource(**result_dict)
            
            logger.info(
                f"✅ Added {user_email} to group {group_email} with role {role}"
            )
            
            return AddMemberResult(member=member)
            
        except HttpError as e:
            # Check if this is a 409 Conflict error (member already exists)
            is_duplicate = False
            if hasattr(e, 'resp') and hasattr(e.resp, 'status'):
                if e.resp.status == 409:
                    is_duplicate = True
            
            if is_duplicate:
                # Member already exists - return as warning
                # Try to get the existing member info
                try:
                    members = self.list_group_members(group_email)
                    user_email_lower = user_email.lower()
                    existing_member = next((m for m in members if m.email.lower() == user_email_lower), None)
                    
                    if existing_member:
                        warning_msg = f"{user_email} is already a member of {group_email}"
                        logger.warning(f"⚠️  {warning_msg}")
                        return AddMemberResult(member=existing_member, warning=warning_msg)
                except Exception:
                    pass
                
                # If we can't get the member, still return a warning result
                # Create a minimal member resource from the request
                warning_msg = f"{user_email} is already a member of {group_email}"
                logger.warning(f"⚠️  {warning_msg}")
                
                # Create a minimal member representation
                from backend.modules.integrations.google.models.google_directory_resources import MemberResource
                minimal_member = MemberResource(
                    kind='admin#directory#member',
                    etag='',
                    id='',
                    email=user_email,
                    role=role,
                    type='USER',
                    status='ACTIVE'
                )
                return AddMemberResult(member=minimal_member, warning=warning_msg)
            else:
                # Other HttpErrors - re-raise to be handled by @handle_http_errors
                raise
    
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
            >>> client = GoogleApiClient(subject="admin@example.com")
            >>> client.remove_member_from_group("team@example.com", "user@example.com")
        """
        self.members().delete(
            groupKey=group_email,
            memberKey=user_email
        ).execute()
        
        logger.info(
            f"✅ Removed {user_email} from group {group_email}"
        )
    
    @handle_http_errors
    def create_group(
        self,
        email: str,
        name: str,
        description: Optional[str] = None
    ) -> GroupResource:
        """
        Create a new Google Group.
        
        Args:
            email: Email address for the group (e.g., "team@example.com")
            name: Display name for the group
            description: Optional description for the group
        
        Returns:
            GroupResource Pydantic model with created group information
        
        Raises:
            HttpError: For Google API errors (including 409 if group already exists)
        
        Example:
            >>> client = GoogleApiClient(subject="admin@example.com")
            >>> group = client.create_group(
            ...     email="newteam@example.com",
            ...     name="New Team",
            ...     description="A new team group"
            ... )
            >>> print(f"Created group: {group.email}")
        """
        group_body = {
            'email': email,
            'name': name
        }
        
        if description:
            group_body['description'] = description
        
        group_dict = self.groups().insert(body=group_body).execute()  # type: ignore[attr-defined]
        group = GroupResource(**group_dict)
        
        logger.info(f"✅ Created group: {group.email}")
        
        return group

    @handle_http_errors
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
            >>> client = GoogleApiClient(subject="admin@example.com")
            >>> if client.is_member_of_group("team@example.com", "user@example.com"):
            ...     print("User is a member")
        """
        try:
            result_dict = self.members().get(
                groupKey=group_email,
                memberKey=user_email
            ).execute()
            # Convert dict to Pydantic model (not used, but validates response)
            MemberResource(**result_dict)
            return True
        except HttpError as e:
            if hasattr(e, 'resp') and hasattr(e.resp, 'status') and e.resp.status == 404:
                return False
            # Re-raise other errors (this will never return)
            self._raise_for_status(e)
            return False  # Unreachable, but satisfies type checker
