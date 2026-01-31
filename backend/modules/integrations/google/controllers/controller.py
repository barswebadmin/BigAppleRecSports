"""
Google Controller

Handles HTTP request/response conversion for Google API endpoints.
Uses request models that handle all the complexity of interacting with googleapiclient services directly.

The request models contain all the logic for:
- Identifier parsing and validation
- API service initialization
- Request structure building
- Direct API execution

This controller only handles HTTP-specific logic and response formatting.
"""

from typing import Dict, Any

from controllers.api.base import BaseAPIController
from shared.api_models import (
    APIError,
    NotFoundAPIError,
    ValidationAPIError,
    APIResponse,
    SuccessResponse
)


class GoogleController(BaseAPIController):
    """
    API controller for Google operations.

    This controller uses request models that handle all the complexity of interacting
    with Google APIs directly. The request models:
    - Parse and validate identifiers
    - Initialize appropriate Google API services
    - Build request structures
    - Execute API calls directly

    This controller only handles:
    - HTTP request/response conversion
    - Response formatting
    - Error mapping to HTTP status codes
    """

    def __init__(self):
        super().__init__()

    # ============================================================================
    # USER OPERATIONS
    # ============================================================================

    async def get_user(self, identifier: str) -> SuccessResponse:
        """
        Get a specific user by identifier.

        Uses GoogleDirectoryService to fetch user data.
        """
        try:
            self.log_api_request("GET", f"/users/{identifier}")

            from modules.integrations.google.services.google_directory_service import GoogleDirectoryService
            from googleapiclient.errors import HttpError
            
            directory_service = GoogleDirectoryService()
            user = directory_service.get_user(identifier)

            user_dict = self._convert_user_to_dict(user.model_dump())

            return SuccessResponse(**self.format_success_response(
                data=user_dict,
                message="User retrieved successfully"
            ))

        except ValidationAPIError:
            raise
        except APIError:
            raise
        except HttpError as e:
            status_code = e.resp.status if hasattr(e, 'resp') and hasattr(e.resp, 'status') else 500
            if status_code == 404:
                raise NotFoundAPIError("User", identifier)
            else:
                self.logger.error("Google API error getting user: %s", e)
                raise APIError(f"Google API error: {e.reason}", status_code=status_code)
        except Exception as e:
            self.logger.error("Error getting user %s: %s", identifier, e)
            raise self.map_exception_to_http_error(e)

    async def list_users(self, max_results: int = 500) -> SuccessResponse:
        """
        List all users in the organization.

        Uses GoogleDirectoryService to fetch users.
        """
        try:
            self.log_api_request("GET", "/users")

            from modules.integrations.google.services.google_directory_service import GoogleDirectoryService
            
            directory_service = GoogleDirectoryService()
            users = directory_service.list_all_users(max_results=max_results)

            users_list = [self._convert_user_to_dict(user.model_dump()) for user in users]

            return SuccessResponse(**self.format_success_response(
                data={"users": users_list, "count": len(users_list)},
                message=f"Retrieved {len(users_list)} users successfully"
            ))

        except ValidationAPIError:
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error listing users: %s", e)
            raise self.map_exception_to_http_error(e)

    async def create_user(self, user_request: dict) -> SuccessResponse:
        """
        Create a new Google user.

        Uses GoogleDirectoryService to create the user.
        """
        try:
            self.log_api_request("POST", "/users", user_request)

            from modules.integrations.google.services.google_directory_service import GoogleDirectoryService
            from googleapiclient.errors import HttpError
            
            directory_service = GoogleDirectoryService()
            
            # Extract and validate parameters
            primary_email = user_request.get('primary_email')
            given_name = user_request.get('given_name')
            family_name = user_request.get('family_name')
            
            if not primary_email:
                raise ValidationAPIError("Primary email is required", {"primary_email": ["This field is required"]})
            if not given_name:
                raise ValidationAPIError("Given name is required", {"given_name": ["This field is required"]})
            if not family_name:
                raise ValidationAPIError("Family name is required", {"family_name": ["This field is required"]})
            
            user = directory_service.create_user(
                primary_email=primary_email,
                given_name=given_name,
                family_name=family_name,
                recovery_email=user_request.get('recovery_email'),
                password=user_request.get('password'),
                change_password_at_next_login=user_request.get('change_password_at_next_login', True),
                org_unit_path=user_request.get('org_unit_path')
            )

            user_dict = self._convert_user_to_dict(user.model_dump())

            return SuccessResponse(**self.format_success_response(
                data=user_dict,
                message="User created successfully"
            ))

        except ValidationAPIError:
            raise
        except APIError:
            raise
        except HttpError as e:
            status_code = e.resp.status if hasattr(e, 'resp') and hasattr(e.resp, 'status') else 500
            if status_code == 409:
                raise ValidationAPIError("User already exists", {"primary_email": ["A user with this email already exists"]})
            else:
                self.logger.error("Google API error creating user: %s", e)
                raise APIError(f"Google API error: {e.reason}", status_code=status_code)
        except Exception as e:
            self.logger.error("Error creating user: %s", e)
            raise self.map_exception_to_http_error(e)

    # ============================================================================
    # GROUP OPERATIONS
    # ============================================================================

    async def get_group(self, identifier: str) -> SuccessResponse:
        """
        Get a specific group by identifier.

        Uses GoogleDirectoryService to fetch group data.
        """
        try:
            self.log_api_request("GET", f"/groups/{identifier}")

            # Import and initialize the directory service
            from modules.integrations.google.services.google_directory_service import GoogleDirectoryService
            
            directory_service = GoogleDirectoryService()
            
            # Get group with members
            result = directory_service.get_group(identifier, include_members=True)
            
            if not result.group:
                raise NotFoundAPIError("Group", identifier)

            # Convert to API response format
            group_dict = self._convert_group_to_dict(result.group.model_dump())
            
            # Add members information
            group_dict["members"] = [
                {
                    "kind": member.kind if hasattr(member, 'kind') else "admin#directory#member",
                    "etag": member.etag if hasattr(member, 'etag') else "",
                    "id": member.id if hasattr(member, 'id') else "",
                    "email": member.email,
                    "role": member.role,
                    "type": member.type,
                    "status": member.status
                }
                for member in result.members
            ]
            
            self.logger.info(f"Found {len(result.members)} members in group {identifier}")

            return SuccessResponse(**self.format_success_response(
                data=group_dict,
                message="Group retrieved successfully"
            ))

        except ValidationAPIError:
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error getting group %s: %s", identifier, e)
            raise self.map_exception_to_http_error(e)

    async def list_groups(self) -> APIResponse:
        """
        List all groups in the organization.

        Uses GoogleGroupIdentifierRequest to handle all API complexity.
        """
        try:
            self.log_api_request("GET", "/groups")

            # Create request model - it handles all the complexity
            request = GoogleGroupIdentifierRequest(identifier="dummy")  # Not used for list operation
            
            # Execute API call directly through request model
            groups_data = request.execute_list_groups()

            # Convert to API response format
            groups_list = [self._convert_group_to_dict(group_data) for group_data in groups_data]

            return APIResponse(**self.format_success_response(
                data={"groups": groups_list, "count": len(groups_list)},
                message=f"Retrieved {len(groups_list)} groups successfully"
            ))

        except ValidationAPIError:
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error listing groups: %s", e)
            raise self.map_exception_to_http_error(e)

    async def create_group(self, group_request: dict) -> SuccessResponse:
        """
        Create a new Google group.

        Uses GoogleDirectoryService to create the group.
        """
        try:
            self.log_api_request("POST", "/groups", group_request)

            # Import and initialize the directory service
            from modules.integrations.google.services.google_directory_service import GoogleDirectoryService
            
            directory_service = GoogleDirectoryService()
            
            # Extract parameters from request
            email = group_request.get('email')
            name = group_request.get('name')
            description = group_request.get('description')
            
            # Validate required fields
            if not email:
                raise ValidationAPIError("Email is required", {"email": ["This field is required"]})
            if not name:
                raise ValidationAPIError("Name is required", {"name": ["This field is required"]})
            
            # Validate email format
            if '@' not in email:
                raise ValidationAPIError(
                    "Invalid email format", 
                    {"email": ["Email must be a valid email address with domain (e.g., group@bigapplerecsports.com)"]}
                )
            
            # Create the group
            group = directory_service.create_group(
                email=email,
                name=name,
                description=description
            )

            # Convert to API response format
            group_dict = self._convert_group_to_dict(group.model_dump())

            return SuccessResponse(**self.format_success_response(
                data=group_dict,
                message="Group created successfully"
            ))

        except ValidationAPIError:
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error creating group: %s", e)
            raise self.map_exception_to_http_error(e)

    async def add_group_member(self, group_email: str, member_request: dict) -> SuccessResponse:
        """
        Add a member to a Google group.

        Uses GoogleDirectoryService to add the member.
        """
        try:
            self.log_api_request("POST", f"/groups/{group_email}/members", member_request)

            # Import and initialize the directory service
            from modules.integrations.google.services.google_directory_service import GoogleDirectoryService
            
            directory_service = GoogleDirectoryService()
            
            # Extract parameters from request
            member_email = member_request.get('member_email')
            role = member_request.get('role', 'MEMBER')
            
            # Validate required fields
            if not member_email:
                raise ValidationAPIError("Member email is required", {"member_email": ["This field is required"]})
            
            # Validate email format
            if '@' not in member_email:
                raise ValidationAPIError(
                    "Invalid email format", 
                    {"member_email": ["Email must be a valid email address with domain"]}
                )
            
            # Add member to group
            result = directory_service.add_member_to_group(
                group_email=group_email,
                user_email=member_email,
                role=role
            )

            # Convert to API response format
            member_dict = {
                "kind": result.member.kind if hasattr(result.member, 'kind') else "admin#directory#member",
                "etag": result.member.etag if hasattr(result.member, 'etag') else "",
                "id": result.member.id if hasattr(result.member, 'id') else "",
                "email": result.member.email,
                "role": result.member.role,
                "type": result.member.type,
                "status": result.member.status
            }
            
            message = "Member added to group successfully"
            if result.is_warning:
                message = result.warning
                member_dict["warning"] = True
                member_dict["warning_message"] = result.warning

            return SuccessResponse(**self.format_success_response(
                data=member_dict,
                message=message
            ))

        except ValidationAPIError:
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error adding group member: %s", e)
            raise self.map_exception_to_http_error(e)

    async def remove_group_member(self, group_email: str, member_email: str) -> SuccessResponse:
        """
        Remove a member from a Google group.

        Uses GoogleDirectoryService to remove the member.
        """
        try:
            self.log_api_request("DELETE", f"/groups/{group_email}/members/{member_email}")

            # Import and initialize the directory service
            from modules.integrations.google.services.google_directory_service import GoogleDirectoryService
            from googleapiclient.errors import HttpError
            
            directory_service = GoogleDirectoryService()
            
            # Validate email format
            if '@' not in member_email:
                raise ValidationAPIError(
                    "Invalid email format", 
                    {"member_email": ["Email must be a valid email address with domain"]}
                )
            
            # Remove member from group
            directory_service.remove_member_from_group(
                group_email=group_email,
                user_email=member_email
            )

            return SuccessResponse(**self.format_success_response(
                data={"group_email": group_email, "member_email": member_email},
                message="Member removed from group successfully"
            ))

        except ValidationAPIError:
            raise
        except APIError:
            raise
        except HttpError as e:
            status_code = e.resp.status if hasattr(e, 'resp') and hasattr(e.resp, 'status') else 500
            
            if status_code == 404:
                # Parse the error reason to provide more specific message
                error_reason = e.reason if hasattr(e, 'reason') else "Resource not found"
                
                # Check if it's specifically a group not found error
                if 'groupKey' in error_reason or 'groupKey' in str(e):
                    raise NotFoundAPIError("Group", group_email)
                # Check if it's specifically a member not found error
                elif 'memberKey' in error_reason or 'memberKey' in str(e):
                    raise NotFoundAPIError("Member", f"{member_email} in group {group_email}")
                else:
                    # Generic not found
                    raise NotFoundAPIError("Member or Group", f"{member_email} in {group_email}")
            elif status_code == 403:
                raise APIError("Permission denied: insufficient permissions to remove member from group", status_code=403)
            elif status_code == 400:
                raise ValidationAPIError(f"Invalid request: {e.reason}", {"error": [str(e)]})
            else:
                self.logger.error("Google API error removing group member: %s", e)
                raise APIError(f"Google API error: {e.reason}", status_code=status_code)
        except Exception as e:
            self.logger.error("Unexpected error removing group member: %s", e)
            raise self.map_exception_to_http_error(e)

    # ============================================================================
    # SHEETS OPERATIONS
    # ============================================================================

    async def get_sheet(self, spreadsheet_id: str) -> SuccessResponse:
        """
        Get a Google Sheet by ID.

        Uses GoogleSheetsService to fetch sheet data.
        """
        try:
            self.log_api_request("GET", f"/sheets/{spreadsheet_id}")

            from modules.integrations.google.services.google_sheets_service import GoogleSheetsService
            from googleapiclient.errors import HttpError
            
            sheets_service = GoogleSheetsService()
            # Get basic spreadsheet metadata
            spreadsheet = sheets_service.spreadsheets.get(spreadsheetId=spreadsheet_id).execute()

            sheet_dict = {
                "spreadsheet_id": spreadsheet.get('spreadsheetId'),
                "title": spreadsheet.get('properties', {}).get('title'),
                "locale": spreadsheet.get('properties', {}).get('locale'),
                "time_zone": spreadsheet.get('properties', {}).get('timeZone'),
                "sheets": [
                    {
                        "sheet_id": sheet.get('properties', {}).get('sheetId'),
                        "title": sheet.get('properties', {}).get('title'),
                        "index": sheet.get('properties', {}).get('index'),
                        "sheet_type": sheet.get('properties', {}).get('sheetType')
                    }
                    for sheet in spreadsheet.get('sheets', [])
                ]
            }

            return SuccessResponse(**self.format_success_response(
                data=sheet_dict,
                message="Sheet retrieved successfully"
            ))

        except ValidationAPIError:
            raise
        except APIError:
            raise
        except HttpError as e:
            status_code = e.resp.status if hasattr(e, 'resp') and hasattr(e.resp, 'status') else 500
            if status_code == 404:
                raise NotFoundAPIError("Sheet", spreadsheet_id)
            else:
                self.logger.error("Google API error getting sheet: %s", e)
                raise APIError(f"Google API error: {e.reason}", status_code=status_code)
        except Exception as e:
            self.logger.error("Error getting sheet %s: %s", spreadsheet_id, e)
            raise self.map_exception_to_http_error(e)

    async def create_sheet(self, sheet_request: dict) -> SuccessResponse:
        """
        Create a new Google Sheet.

        Uses GoogleSheetsService to create the sheet.
        """
        try:
            self.log_api_request("POST", "/sheets", sheet_request)

            from modules.integrations.google.services.google_sheets_service import GoogleSheetsService
            
            sheets_service = GoogleSheetsService()
            
            title = sheet_request.get('title')
            if not title:
                raise ValidationAPIError("Title is required", {"title": ["This field is required"]})
            
            spreadsheet_body = {
                'properties': {
                    'title': title
                }
            }
            
            spreadsheet = sheets_service.spreadsheets.create(body=spreadsheet_body).execute()

            sheet_dict = {
                "spreadsheet_id": spreadsheet.get('spreadsheetId'),
                "title": spreadsheet.get('properties', {}).get('title'),
                "spreadsheet_url": spreadsheet.get('spreadsheetUrl')
            }

            return SuccessResponse(**self.format_success_response(
                data=sheet_dict,
                message="Sheet created successfully"
            ))

        except ValidationAPIError:
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error creating sheet: %s", e)
            raise self.map_exception_to_http_error(e)

    async def update_sheet(self, spreadsheet_id: str, sheet_request: dict) -> SuccessResponse:
        """
        Update a Google Sheet.

        Uses GoogleSheetsService to update the sheet.
        """
        try:
            self.log_api_request("PUT", f"/sheets/{spreadsheet_id}", sheet_request)

            from modules.integrations.google.services.google_sheets_service import GoogleSheetsService
            from googleapiclient.errors import HttpError
            
            sheets_service = GoogleSheetsService()
            
            title = sheet_request.get('title')
            if not title:
                raise ValidationAPIError("Title is required", {"title": ["This field is required"]})
            
            requests = [{
                'updateSpreadsheetProperties': {
                    'properties': {
                        'title': title
                    },
                    'fields': 'title'
                }
            }]
            
            body = {'requests': requests}
            sheets_service.spreadsheets.batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
            
            # Get updated spreadsheet
            spreadsheet = sheets_service.spreadsheets.get(spreadsheetId=spreadsheet_id).execute()

            sheet_dict = {
                "spreadsheet_id": spreadsheet.get('spreadsheetId'),
                "title": spreadsheet.get('properties', {}).get('title'),
                "spreadsheet_url": spreadsheet.get('spreadsheetUrl')
            }

            return SuccessResponse(**self.format_success_response(
                data=sheet_dict,
                message="Sheet updated successfully"
            ))

        except ValidationAPIError:
            raise
        except APIError:
            raise
        except HttpError as e:
            status_code = e.resp.status if hasattr(e, 'resp') and hasattr(e.resp, 'status') else 500
            if status_code == 404:
                raise NotFoundAPIError("Sheet", spreadsheet_id)
            else:
                self.logger.error("Google API error updating sheet: %s", e)
                raise APIError(f"Google API error: {e.reason}", status_code=status_code)
        except Exception as e:
            self.logger.error("Error updating sheet %s: %s", spreadsheet_id, e)
            raise self.map_exception_to_http_error(e)

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _convert_user_to_dict(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert user data from Google API to dictionary for API response.
        """
        try:
            name_data = user_data.get('name', {})
            return {
                "id": user_data.get('id'),
                "email": user_data.get('primaryEmail'),
                "name": name_data.get('fullName'),
                "given_name": name_data.get('givenName'),
                "family_name": name_data.get('familyName'),
                "is_admin": user_data.get('isAdmin', False),
                "suspended": user_data.get('suspended', False),
                "org_unit_path": user_data.get('orgUnitPath'),
            }
        except Exception as e:
            self.logger.warning("Error converting user to dict: %s", e)
            return {
                "id": user_data.get('id', 'unknown'),
                "email": user_data.get('primaryEmail', 'unknown'),
                "error": "Conversion error"
            }

    def _convert_group_to_dict(self, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert group data from Google API to dictionary for API response.
        """
        try:
            return {
                "kind": group_data.get('kind', 'admin#directory#group'),
                "id": group_data.get('id'),
                "etag": group_data.get('etag', ''),
                "email": group_data.get('email'),
                "name": group_data.get('name'),
                "description": group_data.get('description', ''),
                "direct_members_count": str(group_data.get('directMembersCount', 0)),
                "admin_created": group_data.get('adminCreated', False),
            }
        except Exception as e:
            self.logger.warning("Error converting group to dict: %s", e)
            return {
                "kind": "admin#directory#group",
                "id": group_data.get('id', 'unknown'),
                "etag": "",
                "email": group_data.get('email', 'unknown'),
                "name": group_data.get('name', 'unknown'),
                "description": "",
                "direct_members_count": "0",
                "admin_created": False,
                "error": "Conversion error"
            }