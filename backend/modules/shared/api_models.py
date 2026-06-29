"""
Shared API Models and Error Handling

Common Pydantic models and error handling utilities used across all API endpoints
for consistent request/response validation, serialization, and error handling.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator
from shared.model_config import ApiModel

logger = logging.getLogger(__name__)


# ============================================================================
# API EXCEPTION CLASSES
# ============================================================================

class APIErrorModel(ApiModel):
    """Error response model that inherits ApiModel functionality."""
    error: bool = True
    message: str
    error_code: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class APIError(Exception):
    """Base exception class for API-specific errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = None,
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for HTTP response using ApiModel."""
        error_response = APIErrorModel(
            message=self.message,
            error_code=self.error_code,
            details=self.details
        )
        return error_response.to_dict_snake()


class ValidationAPIError(APIError):
    """Exception for validation errors."""

    def __init__(self, message: str, field_errors: Dict[str, list] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details={"field_errors": field_errors or {}}
        )


class NotFoundAPIError(APIError):
    """Exception for resource not found errors."""

    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            message=f"{resource_type} not found: {identifier}",
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "identifier": identifier}
        )


class ExternalServiceError(APIError):
    """Exception for external service errors."""

    def __init__(self, service_name: str, message: str):
        super().__init__(
            message=f"{service_name} service error: {message}",
            status_code=502,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service_name}
        )


# ============================================================================
# EXCEPTION MAPPING AND HANDLING UTILITIES
# ============================================================================

class ExceptionMapper:
    """
    Maps service exceptions to appropriate HTTP status codes and error responses.
    """

    # Mapping of exception types to HTTP status codes
    EXCEPTION_STATUS_MAP = {
        ValueError: 400,
        TypeError: 400,
        KeyError: 400,
        AttributeError: 400,
        PermissionError: 403,
        FileNotFoundError: 404,
        ConnectionError: 502,
        TimeoutError: 504,
    }

    # Mapping of exception types to error codes
    EXCEPTION_CODE_MAP = {
        ValueError: "INVALID_INPUT",
        TypeError: "INVALID_TYPE",
        KeyError: "MISSING_FIELD",
        AttributeError: "INVALID_ATTRIBUTE",
        PermissionError: "PERMISSION_DENIED",
        FileNotFoundError: "RESOURCE_NOT_FOUND",
        ConnectionError: "EXTERNAL_SERVICE_ERROR",
        TimeoutError: "REQUEST_TIMEOUT",
    }

    @classmethod
    def map_exception_to_api_error(cls, exception: Exception) -> APIError:
        """
        Map a service exception to an APIError.

        Args:
            exception: The exception to map

        Returns:
            APIError with appropriate status code and error details
        """
        exception_type = type(exception)

        # Check if it's already an APIError
        if isinstance(exception, APIError):
            return exception

        # Map known exception types
        status_code = cls.EXCEPTION_STATUS_MAP.get(exception_type, 500)
        error_code = cls.EXCEPTION_CODE_MAP.get(exception_type, "INTERNAL_ERROR")

        # Special handling for specific exceptions
        if isinstance(exception, ConnectionError):
            return ExternalServiceError("External API", str(exception))
        if isinstance(exception, FileNotFoundError):
            return NotFoundAPIError("Resource", str(exception))
        if isinstance(exception, PermissionError):
            return APIError(
                message="Permission denied",
                status_code=403,
                error_code="PERMISSION_DENIED"
            )

        # Default mapping
        return APIError(
            message=str(exception),
            status_code=status_code,
            error_code=error_code
        )

    @classmethod
    def create_http_exception(cls, api_error: APIError):
        """
        Create an HTTP exception from an APIError.

        Args:
            api_error: The APIError to convert

        Returns:
            Dict with formatted error response
        """
        error_response = {
            "success": False,
            "error": api_error.message,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        if api_error.error_code:
            error_response["error_code"] = api_error.error_code

        if api_error.details:
            error_response["details"] = api_error.details

        return {
            "status_code": api_error.status_code,
            "detail": error_response
        }


# ============================================================================
# BASE API RESPONSE MODELS
# ============================================================================

class APIResponse(BaseModel):
    """Base response model for all API endpoints."""
    success: bool
    message: str = "Success"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class SuccessResponse(APIResponse):
    """Success response model with data payload."""
    success: bool = True
    data: Any


class ListResponse(SuccessResponse):
    """List response model with pagination."""
    data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('data')
    @classmethod
    def validate_data_structure(cls, v):
        """Ensure data has required structure for list responses."""
        if not isinstance(v, dict):
            raise ValueError("List response data must be a dictionary")

        if 'items' not in v:
            raise ValueError("List response data must contain 'items' field")

        if 'pagination' not in v:
            raise ValueError("List response data must contain 'pagination' field")

        return v


# ============================================================================
# PAGINATION AND FILTERING MODELS
# ============================================================================

class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    limit: Optional[int] = Field(
        default=50, ge=1, le=1000, description="Maximum number of items to return"
    )
    offset: Optional[int] = Field(default=0, ge=0, description="Number of items to skip")


class FilterParams(BaseModel):
    """Base filter parameters for list endpoints."""
    start_date: Optional[str] = Field(None, description="Start date in ISO format")
    end_date: Optional[str] = Field(None, description="End date in ISO format")
    status: Optional[str] = Field(None, description="Filter by status")

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v):
        """Validate ISO date format."""
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError as exc:
                raise ValueError("Date must be in ISO format (YYYY-MM-DDTHH:MM:SSZ)") from exc
        return v
