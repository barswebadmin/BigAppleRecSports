"""
Admin Controller

Handles HTTP request/response conversion for administrative operations.
Delegates to existing backend services and maintains consistency with CLI command functionality.

CRITICAL: This controller ONLY handles HTTP-specific logic and delegates all business logic
to existing backend services. It does NOT rewrite or duplicate existing functionality.
"""

import json
from typing import Dict, Any

from controllers.api.base import BaseAPIController


class AdminController(BaseAPIController):
    """
    API controller for administrative operations.

    This controller follows the established pattern and delegates all business logic
    to existing services. It ONLY handles:
    - HTTP request/response conversion
    - Parameter validation and normalization
    - Error mapping to HTTP status codes
    - Response formatting

    It does NOT contain any business logic - all operations are delegated to appropriate services.
    """

    def __init__(self):
        super().__init__()
        # Future: Initialize services as needed
        # self.google_service = GoogleService()

    # ============================================================================
    # GOOGLE OPERATIONS
    # ============================================================================

    async def handle_create_google_alias(self, request_body: Dict[str, Any]) -> dict:
        """
        Handle creation of Google email alias.

        For now, this just prints the request body as indented JSON.
        Future: Will delegate to GoogleService for actual alias creation.

        Args:
            request_body: Dictionary containing alias creation parameters

        Returns:
            dict with success status and operation details
        """
        try:
            self.log_api_request("POST", "/admin/google/emails/aliases", request_body)

            print("=== Google Alias Creation Request ===")
            print(json.dumps(request_body, indent=2))
            print("=====================================")

            self.log_service_call("create_google_alias", request_body)

            response_data = {
                "operation": "create_google_alias",
                "request_received": request_body,
                "status": "printed_to_console",
                "message": "Request body printed to console as indented JSON"
            }

            return self.format_success_response(
                data=response_data,
                message="Google alias creation request processed (printed to console)"
            )

        except ValueError:
            raise
        except Exception as e:
            self.logger.error("Error handling Google alias creation: %s", e)
            raise self.map_exception_to_http_error(e)