"""
Slack API Controller

Handles HTTP request/response conversion for Slack API endpoints.
Delegates to existing backend services and maintains consistency with CLI command functionality.

CRITICAL: This controller ONLY handles HTTP-specific logic and delegates all business logic
to existing backend services. It does NOT rewrite or duplicate existing functionality.
"""

from typing import Dict, Any, Optional

from backend.controllers.api.base import BaseAPIController
from backend.modules.integrations.slack.slack_service import SlackService
from backend.shared.api_models import (
    APIError,
    NotFoundAPIError,
    ValidationAPIError,
    APIResponse
)
from backend.modules.integrations.slack.models import (
    SlackUserIdentifierRequest,
    SlackGroupIdentifierRequest,
    SlackChannelIdentifierRequest,
    SlackPaginationRequest,
    SlackMessageRequest,
    SlackUserGroupRequest
)


class SlackAPIController(BaseAPIController):
    """
    API controller for Slack operations.

    This controller follows the webhook controller pattern and delegates all business logic
    to the existing SlackService. It ONLY handles:
    - HTTP request/response conversion
    - Parameter validation and normalization
    - Error mapping to HTTP status codes
    - Response formatting

    It does NOT contain any business logic - all operations are delegated to SlackService.
    """

    def __init__(self):
        super().__init__()
        # REUSE existing service - DO NOT rewrite business logic
        self.slack_service = SlackService()

    # ============================================================================
    # USER OPERATIONS
    # ============================================================================

    async def get_user(self, identifier: str) -> APIResponse:
        """
        Get a specific user by identifier.

        DELEGATES to existing SlackService methods - same as CLI uses.
        """
        try:
            self.log_api_request("GET", f"/users/{identifier}")

            # Validate and parse identifier using request model
            identifier_request = SlackUserIdentifierRequest(identifier=identifier)
            identifier_dict = identifier_request.parse()

            # DELEGATE to existing service method - same as CLI command uses
            self.log_service_call("get_user", identifier_dict)
            user = self.slack_service.get_user_by_identifier(identifier_dict)

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

        DELEGATES to existing SlackService methods - same as CLI uses.
        """
        try:
            self.log_api_request("GET", f"/groups/{identifier}")

            # Validate and parse identifier using request model
            identifier_request = SlackGroupIdentifierRequest(identifier=identifier)
            identifier_dict = identifier_request.parse()

            # DELEGATE to existing service method - same as CLI command uses
            self.log_service_call("get_group", identifier_dict)
            group = self.slack_service.get_group_by_identifier(identifier_dict)

            if not group:
                raise NotFoundAPIError("Group", identifier)

            # Convert to API response format
            group_dict = self._convert_group_to_dict(group)

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

    # ============================================================================
    # CHANNEL OPERATIONS
    # ============================================================================

    async def get_channel(self, identifier: str) -> APIResponse:
        """
        Get a specific channel by identifier.

        DELEGATES to existing SlackService methods - same as CLI uses.
        """
        try:
            self.log_api_request("GET", f"/channels/{identifier}")

            # Validate and parse identifier using request model
            identifier_request = SlackChannelIdentifierRequest(identifier=identifier)
            identifier_dict = identifier_request.parse()

            # DELEGATE to existing service method - same as CLI command uses
            self.log_service_call("get_channel", identifier_dict)
            channel = self.slack_service.get_channel_by_identifier(identifier_dict)

            if not channel:
                raise NotFoundAPIError("Channel", identifier)

            # Convert to API response format
            channel_dict = self._convert_channel_to_dict(channel)

            return APIResponse(**self.format_success_response(
                data=channel_dict,
                message="Channel retrieved successfully"
            ))

        except ValidationAPIError:
            # Re-raise validation errors as-is
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error getting channel %s: %s", identifier, e)
            raise self.map_exception_to_http_error(e)

    # ============================================================================
    # MESSAGE OPERATIONS
    # ============================================================================

    async def send_message(self, message_request: SlackMessageRequest) -> APIResponse:
        """
        Send a message to a Slack channel.

        DELEGATES to existing SlackService methods - same as CLI uses.
        """
        try:
            self.log_api_request("POST", "/messages", {
                "channel": message_request.channel,
                "text": message_request.text[:100] + "..." if len(message_request.text) > 100 else message_request.text
            })

            # Parse channel identifier
            channel_dict = message_request.parse_channel()

            # DELEGATE to existing service method - same as CLI command uses
            self.log_service_call("send_message", {
                "channel": channel_dict,
                "text": message_request.text,
                "thread_ts": message_request.thread_ts
            })
            
            result = self.slack_service.send_message(
                channel=channel_dict,
                text=message_request.text,
                thread_ts=message_request.thread_ts
            )

            return APIResponse(**self.format_success_response(
                data={"message_ts": result.get("ts"), "channel": result.get("channel")},
                message="Message sent successfully"
            ))

        except ValidationAPIError:
            # Re-raise validation errors as-is
            raise
        except APIError:
            raise
        except Exception as e:
            self.logger.error("Error sending message: %s", e)
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
                "name": str(user.name) if hasattr(user, 'name') else None,
                "email": str(user.email) if hasattr(user, 'email') else None,
                "display_name": str(user.display_name) if hasattr(user, 'display_name') else None,
                "real_name": str(user.real_name) if hasattr(user, 'real_name') else None,
                "is_admin": bool(user.is_admin) if hasattr(user, 'is_admin') else False,
                "is_bot": bool(user.is_bot) if hasattr(user, 'is_bot') else False,
                "deleted": bool(user.deleted) if hasattr(user, 'deleted') else False,
            }
        except Exception as e:
            self.logger.warning("Error converting user to dict: %s", e)
            return {
                "id": str(user.id) if hasattr(user, 'id') else "unknown",
                "name": "unknown",
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
                "name": str(group.name) if hasattr(group, 'name') else None,
                "handle": str(group.handle) if hasattr(group, 'handle') else None,
                "description": str(group.description) if hasattr(group, 'description') else None,
                "member_count": int(group.member_count) if hasattr(group, 'member_count') else 0,
                "is_archived": bool(group.is_archived) if hasattr(group, 'is_archived') else False,
            }
        except Exception as e:
            self.logger.warning("Error converting group to dict: %s", e)
            return {
                "id": str(group.id) if hasattr(group, 'id') else "unknown",
                "name": "unknown",
                "error": "Conversion error"
            }

    def _convert_channel_to_dict(self, channel: Any) -> Dict[str, Any]:
        """
        Convert channel object to dictionary for API response.

        REUSES existing data structures - DO NOT rewrite conversion logic.
        """
        try:
            return {
                "id": str(channel.id) if hasattr(channel, 'id') else None,
                "name": str(channel.name) if hasattr(channel, 'name') else None,
                "topic": str(channel.topic) if hasattr(channel, 'topic') else None,
                "purpose": str(channel.purpose) if hasattr(channel, 'purpose') else None,
                "member_count": int(channel.member_count) if hasattr(channel, 'member_count') else 0,
                "is_private": bool(channel.is_private) if hasattr(channel, 'is_private') else False,
                "is_archived": bool(channel.is_archived) if hasattr(channel, 'is_archived') else False,
            }
        except Exception as e:
            self.logger.warning("Error converting channel to dict: %s", e)
            return {
                "id": str(channel.id) if hasattr(channel, 'id') else "unknown",
                "name": "unknown",
                "error": "Conversion error"
            }