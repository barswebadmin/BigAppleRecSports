"""
Google Controller

Handles HTTP request/response conversion for Google API endpoints.
Delegates to existing backend services and maintains consistency with CLI command functionality.

CRITICAL: This controller ONLY handles HTTP-specific logic and delegates all business logic
to existing backend services. It does NOT rewrite or duplicate existing functionality.
"""

from typing import Dict, Any

from backend.controllers.api.base import BaseAPIController
from backend.modules.integrations.google.google_api_client import GoogleApiClient
from backend.shared.api_models import (
    APIError,
    NotFoundAPIError,
    ValidationAPIError,
    APIResponse
)
from backend.modules.integrations.google.models import (
    GoogleGroupMemberRequest
)


class GoogleController(BaseAPIController):
    """
    API controller for Google operations.

    This controller follows the webhook controller pattern and delegates all business logic
    to the existing GoogleService. It ONLY handles:
    - HTTP request/response conversion
    - Parameter validation and normalization
    - Error mapping to HTTP status codes
    - Response formatting

    It does NOT contain any business logic - all operations are delegated to GoogleService.
    """

    def __init__(self):
        super().__init__()
        # REUSE existing service - DO NOT rewrite business logic
        self.google_client = GoogleApiClient()

    # ============================================================================
    # USER OPERATIONS
    # ============================================================================

    async def get_user(self, identifier: str) -> APIResponse:
        """
        Get a specific user by identifier.

        DELEGATES to existing GoogleApiClient methods - same as CLI uses.
        """
        try:
            self.log_api_request("GET", f"/users/{identifier}")

            # DELEGATE to existing client method - same as CLI command uses
            self.log_service_call("get_user", {"identifier": identifier})
            user = self.google_client.get_user(identifier)

            if not user:
                raise NotFoundAPIError("User", identifier)

            # Convert to API response format
            user_dict = self._convert_user_to_dict(user)

            return APIResponse(**self.format_success_response(
                data=user_dict,
                message="User retrieved successfully"
            ))

        except ValidationAPIError:
            # Re-raise validation errors as-is
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error getting user %s: %s", identifier, e)
            raise self.map_exception_to_http_error(e)

    # ============================================================================
    # GROUP OPERATIONS
    # ============================================================================

    async def get_group(self, identifier: str) -> APIResponse:
        """
        Get a specific group by identifier.

        DELEGATES to existing GoogleApiClient methods - same as CLI uses.
        """
        try:
            self.log_api_request("GET", f"/groups/{identifier}")

            # DELEGATE to existing client method - same as CLI command uses
            self.log_service_call("get_group", {"identifier": identifier})
            group_with_members = self.google_client.get_group(identifier, include_members=True)

            if not group_with_members or not group_with_members.group:
                raise NotFoundAPIError("Group", identifier)

            # Convert to API response format
            group_dict = self._convert_group_to_dict(group_with_members.group)
            # Add members information
            group_dict["members"] = [
                {
                    "email": member.email,
                    "role": member.role,
                    "type": member.type,
                    "status": member.status
                }
                for member in group_with_members.members
            ]

            return APIResponse(**self.format_success_response(
                data=group_dict,
                message="Group retrieved successfully"
            ))

        except ValidationAPIError:
            # Re-raise validation errors as-is
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error getting group %s: %s", identifier, e)
            raise self.map_exception_to_http_error(e)

    async def create_group(self, group_request: dict) -> APIResponse:
        """
        Create a new Google group.

        DELEGATES to existing GoogleApiClient methods - same as CLI uses.
        """
        try:
            self.log_api_request("POST", "/groups", group_request)

            # DELEGATE to existing client method - same as CLI command uses
            self.log_service_call("create_group", group_request)
            group = self.google_client.create_group(
                email=group_request.get("email"),
                name=group_request.get("name"),
                description=group_request.get("description", "")
            )

            # Convert to API response format
            group_dict = self._convert_group_to_dict(group)

            return APIResponse(**self.format_success_response(
                data=group_dict,
                message="Group created successfully"
            ))

        except ValidationAPIError:
            # Re-raise validation errors as-is
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error creating group: %s", e)
            raise self.map_exception_to_http_error(e)

    async def add_group_member(self, member_request: GoogleGroupMemberRequest) -> APIResponse:
        """
        Add a member to a Google group.

        DELEGATES to existing GoogleApiClient methods - same as CLI uses.
        """
        try:
            self.log_api_request("POST", f"/groups/{member_request.group_email}/members", {
                "member_email": member_request.member_email,
                "role": member_request.role
            })

            # DELEGATE to existing client method - same as CLI command uses
            self.log_service_call("add_group_member", {
                "group_email": member_request.group_email,
                "member_email": member_request.member_email,
                "role": member_request.role
            })
            
            # Use the directory service directly for adding members
            result = self.google_client.directory_service.add_member_to_group(
                group_email=member_request.group_email,
                user_email=member_request.member_email,
                role=member_request.role
            )

            # Convert AddMemberResult to dict
            member_dict = {
                "email": result.member.email,
                "role": result.member.role,
                "type": result.member.type,
                "status": result.member.status,
                "warning": result.warning
            }

            return APIResponse(**self.format_success_response(
                data=member_dict,
                message="Member added to group successfully"
            ))

        except ValidationAPIError:
            # Re-raise validation errors as-is
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error adding group member: %s", e)
            raise self.map_exception_to_http_error(e)

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _convert_user_to_dict(self, user: Any) -> Dict[str, Any]:
        """
        Convert user object to dictionary for API response.

        REUSES existing data structures - DO NOT rewrite conversion logic.
        """
        try:
            return {
                "id": str(user.id) if hasattr(user, 'id') else None,
                "email": str(user.primaryEmail) if hasattr(user, 'primaryEmail') else None,
                "name": str(user.name.fullName) if hasattr(user, 'name') and hasattr(user.name, 'fullName') else None,
                "given_name": str(user.name.givenName) if hasattr(user, 'name') and hasattr(user.name, 'givenName') else None,
                "family_name": str(user.name.familyName) if hasattr(user, 'name') and hasattr(user.name, 'familyName') else None,
                "is_admin": bool(user.isAdmin) if hasattr(user, 'isAdmin') else False,
                "suspended": bool(user.suspended) if hasattr(user, 'suspended') else False,
                "org_unit_path": str(user.orgUnitPath) if hasattr(user, 'orgUnitPath') else None,
            }
        except Exception as e:
            self.logger.warning("Error converting user to dict: %s", e)
            return {
                "id": str(user.id) if hasattr(user, 'id') else "unknown",
                "email": "unknown",
                "error": "Conversion error"
            }

    def _convert_group_to_dict(self, group: Any) -> Dict[str, Any]:
        """
        Convert group object to dictionary for API response.

        REUSES existing data structures - DO NOT rewrite conversion logic.
        """
        try:
            return {
                "id": str(group.id) if hasattr(group, 'id') else None,
                "email": str(group.email) if hasattr(group, 'email') else None,
                "name": str(group.name) if hasattr(group, 'name') else None,
                "description": str(group.description) if hasattr(group, 'description') else None,
                "direct_members_count": int(group.direct_members_count) if hasattr(group, 'direct_members_count') else 0,
                "admin_created": bool(group.admin_created) if hasattr(group, 'admin_created') else False,
            }
        except Exception as e:
            self.logger.warning("Error converting group to dict: %s", e)
            return {
                "id": str(group.id) if hasattr(group, 'id') else "unknown",
                "email": "unknown",
                "error": "Conversion error"
            }