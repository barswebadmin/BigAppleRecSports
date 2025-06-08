"""
Standardized response formatting for Lambda functions
"""

import json
from typing import Any, Dict, Optional, Union

def format_response(status_code: int, body: Any, indent: int = 2) -> Dict[str, Any]:
    """
    Standardize API responses across all functions
    
    Args:
        status_code: HTTP status code
        body: Response body (will be JSON serialized)
        indent: JSON indentation level
        
    Returns:
        Formatted response dictionary
    """
    return {
        "statusCode": status_code,
        "body": json.dumps(body, indent=indent, default=str)
    }

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
        "error": f"❌ {error_message}"
    }
    if details:
        body["details"] = details
    return format_response(status_code, body) 