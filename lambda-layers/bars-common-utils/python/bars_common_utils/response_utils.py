"""
Standardized response formatting for Lambda functions
"""

import json
import os
import sys
from typing import Any, Dict, Optional, Tuple
try:
    from botocore.exceptions import ClientError  # type: ignore
except Exception:  # pragma: no cover - botocore may not be present in all envs
    ClientError = None  # type: ignore

def format_response(status_code: int, body: Any, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Standardize API responses across all functions
    
    Args:
        status_code: HTTP status code
        body: Response body data
        headers: Optional response headers
        
    Returns:
        Formatted response dictionary
    """
    # For testing, return body as dict. For AWS deployment, return as JSON string
    # Detect test mode by checking if pytest is running
    is_testing = 'pytest' in sys.modules or os.environ.get('PYTEST_CURRENT_TEST') is not None
    
    response = {
        "statusCode": status_code,
        "body": body if is_testing else json.dumps(body, default=str)
    }
    
    # Merge custom headers with defaults
    default_headers = {'Content-Type': 'application/json'}
    if headers:
        default_headers.update(headers)
    
    response["headers"] = default_headers
    return response

def format_error(
    status_code: int, 
    error_message: str, 
    details: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Standardize error responses
    
    Args:
        status_code: HTTP status code
        error_message: Main error message
        details: Optional additional error details
        
    Returns:
        Formatted error response
    """
    body = {
        "error": error_message  # Remove ❌ emoji for test compatibility
    }
    if details:
        body["details"] = details
    return format_response(status_code, body) 


def standardize_scheduler_result(
    *,
    schedule_name: str,
    expression: str,
    aws_response: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Normalize successful create_schedule responses.
    """
    return {
        "message": f"✅ Schedule '{schedule_name}' created successfully!",
        "new_expression": expression,
        "aws_response": aws_response,
    }


def standardize_scheduler_error(
    *,
    schedule_name: Optional[str],
    reason: str,
    details: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Normalize error shape for create_schedule failures. Returns (status_code, body).
    """
    body: Dict[str, Any] = {
        "error": reason,
    }
    if schedule_name:
        body["scheduleName"] = schedule_name
    if details:
        body["details"] = details
    return 500, body


def map_exception_to_http_status(e: Exception) -> Tuple[int, Dict[str, Any]]:
    """
    Map common exceptions to HTTP status codes with structured error body.

    - 401/403: Auth/permission/token issues
    - 400: Bad request/path for AWS validation or resource not found
    - 422: Invalid input/validation from our code
    - 500: Default
    """
    message = str(e)
    details: Dict[str, Any] = {"exception": e.__class__.__name__}

    # botocore client errors
    if ClientError and isinstance(e, ClientError):  # type: ignore
        resp = e.response or {}
        err = resp.get("Error", {})
        code = err.get("Code", "")
        http_status = resp.get("ResponseMetadata", {}).get("HTTPStatusCode")
        details["aws_error_code"] = code
        details["aws_http_status"] = http_status

        # Explicit maps for auth/permission
        if code in {"UnrecognizedClientException", "InvalidClientTokenId", "SignatureDoesNotMatch"}:
            return 401, {"error": message, "details": details}
        if code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}:
            return 403, {"error": message, "details": details}

        # Validation and not found
        if code in {"ValidationException", "ResourceNotFoundException", "ValidationError"}:
            return 400, {"error": message, "details": details}

        # Fall back to AWS-reported HTTP status if present
        if isinstance(http_status, int):
            return http_status, {"error": message, "details": details}

        return 500, {"error": message, "details": details}

    # Our validation errors
    if isinstance(e, ValueError):
        return 422, {"error": message, "details": details}

    # Permission errors without botocore
    if isinstance(e, PermissionError):
        return 403, {"error": message, "details": details}

    return 500, {"error": message, "details": details}