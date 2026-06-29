"""
Base API Controller

Provides common functionality for all API controllers including error handling,
response formatting, and logging patterns.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from fastapi import HTTPException
from datetime import datetime


class BaseAPIController:
    """
    Base class for all API controllers providing common functionality.
    
    This class provides:
    - Consistent error handling and HTTP status code mapping
    - Standard response formatting
    - Logging utilities
    - Common validation patterns
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def format_success_response(
        self, 
        data: Any, 
        message: str = "Success"
    ) -> Dict[str, Any]:
        """Format a successful API response with consistent structure."""
        return {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    def format_error_response(
        self, 
        error: str, 
        details: Any = None
    ) -> Dict[str, Any]:
        """Format an error API response with consistent structure."""
        return {
            "success": False,
            "error": error,
            "details": details,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    def format_list_response(
        self,
        items: List[Any],
        total_count: int,
        limit: int,
        offset: int,
        message: str = "Success"
    ) -> Dict[str, Any]:
        """Format a paginated list response with consistent structure."""
        return {
            "success": True,
            "message": message,
            "data": {
                "items": items,
                "pagination": {
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(items) < total_count,
                    "next_offset": offset + limit if offset + len(items) < total_count else None
                }
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    def map_exception_to_http_error(self, exception: Exception) -> HTTPException:
        """
        Map service exceptions to appropriate HTTP status codes.
        
        This method provides consistent error handling across all controllers
        by mapping common exception types to HTTP status codes.
        """
        if isinstance(exception, ValueError):
            return HTTPException(status_code=400, detail=str(exception))
        elif isinstance(exception, PermissionError):
            return HTTPException(status_code=403, detail=str(exception))
        elif isinstance(exception, FileNotFoundError):
            return HTTPException(status_code=404, detail=str(exception))
        elif isinstance(exception, ConnectionError):
            return HTTPException(status_code=502, detail=f"External service error: {exception}")
        elif isinstance(exception, TimeoutError):
            return HTTPException(status_code=504, detail=f"Request timeout: {exception}")
        else:
            self.logger.error(f"Unexpected error: {exception}", exc_info=True)
            return HTTPException(status_code=500, detail="Internal server error")
    
    def validate_identifier(self, identifier: str, identifier_type: str) -> str:
        """
        Validate and normalize identifiers.
        
        Args:
            identifier: The identifier to validate
            identifier_type: Type of identifier for error messages
            
        Returns:
            Normalized identifier
            
        Raises:
            HTTPException: If identifier is invalid
        """
        if not identifier or not identifier.strip():
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid {identifier_type}: identifier cannot be empty"
            )
        
        return identifier.strip()
    
    def validate_pagination_params(
        self, 
        limit: Optional[int] = None, 
        offset: Optional[int] = None
    ) -> tuple[int, int]:
        """
        Validate and normalize pagination parameters.
        
        Args:
            limit: Maximum number of items to return
            offset: Number of items to skip
            
        Returns:
            Tuple of (limit, offset) with validated values
            
        Raises:
            HTTPException: If parameters are invalid
        """
        # Set defaults
        if limit is None:
            limit = 50
        if offset is None:
            offset = 0
        
        # Validate limits
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 1000"
            )
        
        if offset < 0:
            raise HTTPException(
                status_code=400,
                detail="Offset must be non-negative"
            )
        
        return limit, offset
    
    def log_api_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Dict[str, Any] = None
    ) -> None:
        """Log API request details for debugging and monitoring."""
        self.logger.info(
            f"API Request: {method} {endpoint}",
            extra={"params": params or {}}
        )
    
    def log_service_call(
        self, 
        service_method: str, 
        params: Dict[str, Any] = None
    ) -> None:
        """Log service method calls for debugging."""
        self.logger.debug(
            f"Calling service method: {service_method}",
            extra={"params": params or {}}
        )