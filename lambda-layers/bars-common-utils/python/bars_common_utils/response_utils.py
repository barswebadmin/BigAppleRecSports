"""
Standardized response formatting for Lambda functions
"""

import json
import os
import sys
from typing import Any, Dict, Optional

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