"""
Google Request Models

Pydantic models for validating and parsing Google API requests.
These models handle identifier parsing, validation, and return proper validation errors.
"""

import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator

from backend.shared.api_models import ValidationAPIError


# ============================================================================
# IDENTIFIER REQUEST MODELS
# ============================================================================

class GoogleUserIdentifierRequest(BaseModel):
    """Request model for Google user identifier parsing and validation."""
    identifier: str = Field(..., min_length=1, description="User identifier")

    @validator('identifier')
    def validate_identifier(cls, v):
        """Validate user identifier."""
        if not v or not v.strip():
            raise ValueError("User identifier cannot be empty")
        return v.strip()

    def parse(self) -> Dict[str, Any]:
        """
        Parse the identifier and return service-compatible format.
        
        Returns:
            Dictionary with parsed identifier information
            
        Raises:
            ValidationAPIError: If identifier format is invalid
        """
        identifier = self.identifier.strip()
        
        try:
            if '@' in identifier:
                # Email format - validate it
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, identifier):
                    raise ValueError("Invalid email format")
                return {"email": identifier}
            
            # Assume it's a Google user ID
            return {"user_id": identifier}
        except ValueError as e:
            raise ValidationAPIError(
                message=str(e),
                field_errors={"identifier": [str(e)]}
            ) from e


class GoogleGroupIdentifierRequest(BaseModel):
    """Request model for Google group identifier parsing and validation."""
    identifier: str = Field(..., min_length=1, description="Group identifier")

    @validator('identifier')
    def validate_identifier(cls, v):
        """Validate group identifier."""
        if not v or not v.strip():
            raise ValueError("Group identifier cannot be empty")
        return v.strip()

    def parse(self) -> Dict[str, Any]:
        """
        Parse the identifier and return service-compatible format.
        
        Returns:
            Dictionary with parsed identifier information
            
        Raises:
            ValidationAPIError: If identifier format is invalid
        """
        identifier = self.identifier.strip()
        
        try:
            if '@' in identifier:
                # Group email format
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, identifier):
                    raise ValueError("Invalid group email format")
                return {"group_email": identifier}
            
            # Assume it's a group ID
            return {"group_id": identifier}
        except ValueError as e:
            raise ValidationAPIError(
                message=str(e),
                field_errors={"identifier": [str(e)]}
            ) from e


class GoogleDriveFileIdentifierRequest(BaseModel):
    """Request model for Google Drive file identifier parsing and validation."""
    identifier: str = Field(..., min_length=1, description="File identifier")

    @validator('identifier')
    def validate_identifier(cls, v):
        """Validate file identifier."""
        if not v or not v.strip():
            raise ValueError("File identifier cannot be empty")
        return v.strip()

    def parse(self) -> Dict[str, Any]:
        """
        Parse the identifier and return service-compatible format.
        
        Returns:
            Dictionary with parsed identifier information
            
        Raises:
            ValidationAPIError: If identifier format is invalid
        """
        identifier = self.identifier.strip()
        
        try:
            # Google Drive file IDs are typically alphanumeric strings
            if re.match(r'^[a-zA-Z0-9_-]+$', identifier):
                return {"file_id": identifier}
            
            # Check if it's a Google Drive URL
            drive_url_pattern = r'https://drive\.google\.com/.*[?&]id=([a-zA-Z0-9_-]+)'
            match = re.search(drive_url_pattern, identifier)
            if match:
                return {"file_id": match.group(1)}
            
            raise ValueError(f"Invalid Google Drive file identifier format: {identifier}")
        except ValueError as e:
            raise ValidationAPIError(
                message=str(e),
                field_errors={"identifier": [str(e)]}
            ) from e


class GoogleSheetsIdentifierRequest(BaseModel):
    """Request model for Google Sheets identifier parsing and validation."""
    identifier: str = Field(..., min_length=1, description="Spreadsheet identifier")

    @validator('identifier')
    def validate_identifier(cls, v):
        """Validate spreadsheet identifier."""
        if not v or not v.strip():
            raise ValueError("Spreadsheet identifier cannot be empty")
        return v.strip()

    def parse(self) -> Dict[str, Any]:
        """
        Parse the identifier and return service-compatible format.
        
        Returns:
            Dictionary with parsed identifier information
            
        Raises:
            ValidationAPIError: If identifier format is invalid
        """
        identifier = self.identifier.strip()
        
        try:
            # Google Sheets IDs are typically alphanumeric strings
            if re.match(r'^[a-zA-Z0-9_-]+$', identifier):
                return {"spreadsheet_id": identifier}
            
            # Check if it's a Google Sheets URL
            sheets_url_pattern = r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)'
            match = re.search(sheets_url_pattern, identifier)
            if match:
                return {"spreadsheet_id": match.group(1)}
            
            raise ValueError(f"Invalid Google Sheets identifier format: {identifier}")
        except ValueError as e:
            raise ValidationAPIError(
                message=str(e),
                field_errors={"identifier": [str(e)]}
            ) from e


# ============================================================================
# PAGINATION AND FILTERING REQUEST MODELS
# ============================================================================

class GooglePaginationRequest(BaseModel):
    """Request model for Google API pagination parameters."""
    max_results: Optional[int] = Field(default=100, ge=1, le=500, description="Maximum results per page")
    page_token: Optional[str] = Field(None, description="Page token for pagination")

    def validate_and_normalize(self) -> tuple[int, Optional[str]]:
        """
        Validate and return normalized pagination parameters.
        
        Returns:
            Tuple of (max_results, page_token)
            
        Raises:
            ValidationAPIError: If parameters are invalid
        """
        try:
            max_results = self.max_results or 100
            
            if max_results < 1 or max_results > 500:
                raise ValueError("max_results must be between 1 and 500")
            
            return max_results, self.page_token
        except ValueError as e:
            raise ValidationAPIError(
                message=str(e),
                field_errors={"pagination": [str(e)]}
            ) from e


# ============================================================================
# GOOGLE-SPECIFIC REQUEST MODELS
# ============================================================================

class GoogleGroupMemberRequest(BaseModel):
    """Request model for Google group member operations."""
    group_email: str = Field(..., description="Group email address")
    member_email: str = Field(..., description="Member email address")
    role: Optional[str] = Field(default="MEMBER", description="Member role")
    
    @validator('group_email', 'member_email')
    def validate_email_format(cls, v):
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v
    
    @validator('role')
    def validate_role(cls, v):
        """Validate member role."""
        valid_roles = ["OWNER", "MANAGER", "MEMBER"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class GoogleSheetsRangeRequest(BaseModel):
    """Request model for Google Sheets range operations."""
    spreadsheet_id: str = Field(..., description="Spreadsheet ID")
    range: str = Field(..., description="A1 notation range")
    
    @validator('range')
    def validate_range_format(cls, v):
        """Validate A1 notation range format."""
        # Basic A1 notation validation
        a1_pattern = r'^[A-Z]+[0-9]+:[A-Z]+[0-9]+$|^[A-Z]+:[A-Z]+$|^[0-9]+:[0-9]+$|^[A-Z]+[0-9]+$'
        if not re.match(a1_pattern, v):
            raise ValueError("Invalid A1 notation range format")
        return v


class GoogleDrivePermissionRequest(BaseModel):
    """Request model for Google Drive permission operations."""
    file_id: str = Field(..., description="File ID")
    email: str = Field(..., description="User email")
    role: str = Field(..., description="Permission role")
    type: str = Field(default="user", description="Permission type")
    
    @validator('email')
    def validate_email_format(cls, v):
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v
    
    @validator('role')
    def validate_role(cls, v):
        """Validate permission role."""
        valid_roles = ["owner", "organizer", "fileOrganizer", "writer", "commenter", "reader"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v
    
    @validator('type')
    def validate_type(cls, v):
        """Validate permission type."""
        valid_types = ["user", "group", "domain", "anyone"]
        if v not in valid_types:
            raise ValueError(f"Type must be one of: {', '.join(valid_types)}")
        return v