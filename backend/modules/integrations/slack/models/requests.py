"""
Slack Request Models

Pydantic models for validating and parsing Slack API requests.
These models handle identifier parsing, validation, and return proper validation errors.
"""

import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator

from backend.shared.api_models import ValidationAPIError


# ============================================================================
# IDENTIFIER REQUEST MODELS
# ============================================================================

class SlackUserIdentifierRequest(BaseModel):
    """Request model for Slack user identifier parsing and validation."""
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
            if identifier.startswith('U') and len(identifier) >= 9:
                # Slack user ID format: U1234567890
                return {"user_id": identifier}
            
            raise ValueError(f"Invalid user identifier format: {identifier}")
        except ValueError as e:
            raise ValidationAPIError(
                message=str(e),
                field_errors={"identifier": [str(e)]}
            ) from e


class SlackGroupIdentifierRequest(BaseModel):
    """Request model for Slack group identifier parsing and validation."""
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
            if identifier.startswith('S') and len(identifier) >= 9:
                # Slack group ID format: S1234567890
                return {"group_id": identifier}
            
            # Assume it's a group name/handle
            return {"group_name": identifier}
        except ValueError as e:
            raise ValidationAPIError(
                message=str(e),
                field_errors={"identifier": [str(e)]}
            ) from e


class SlackChannelIdentifierRequest(BaseModel):
    """Request model for Slack channel identifier parsing and validation."""
    identifier: str = Field(..., min_length=1, description="Channel identifier")

    @validator('identifier')
    def validate_identifier(cls, v):
        """Validate channel identifier."""
        if not v or not v.strip():
            raise ValueError("Channel identifier cannot be empty")
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
            if identifier.startswith('C') and len(identifier) >= 9:
                # Slack channel ID format: C1234567890
                return {"channel_id": identifier}
            if identifier.startswith('#'):
                # Channel name with # prefix
                return {"channel_name": identifier[1:]}
            
            # Assume it's a channel name
            return {"channel_name": identifier}
        except ValueError as e:
            raise ValidationAPIError(
                message=str(e),
                field_errors={"identifier": [str(e)]}
            ) from e


# ============================================================================
# PAGINATION AND FILTERING REQUEST MODELS
# ============================================================================

class SlackPaginationRequest(BaseModel):
    """Request model for Slack pagination parameters."""
    limit: Optional[int] = Field(default=50, ge=1, le=1000, description="Items per page")
    cursor: Optional[str] = Field(None, description="Pagination cursor")

    def validate_and_normalize(self) -> tuple[int, Optional[str]]:
        """
        Validate and return normalized pagination parameters.
        
        Returns:
            Tuple of (limit, cursor)
            
        Raises:
            ValidationAPIError: If parameters are invalid
        """
        try:
            limit = self.limit or 50
            
            if limit < 1 or limit > 1000:
                raise ValueError("Limit must be between 1 and 1000")
            
            return limit, self.cursor
        except ValueError as e:
            raise ValidationAPIError(
                message=str(e),
                field_errors={"pagination": [str(e)]}
            ) from e


# ============================================================================
# SLACK-SPECIFIC REQUEST MODELS
# ============================================================================

class SlackMessageRequest(BaseModel):
    """Request model for sending Slack messages."""
    channel: str = Field(..., description="Channel ID or name")
    text: str = Field(..., min_length=1, description="Message text")
    thread_ts: Optional[str] = Field(None, description="Thread timestamp")
    
    @validator('text')
    def validate_message_text(cls, v):
        """Validate message text."""
        if not v or not v.strip():
            raise ValueError("Message text cannot be empty")
        if len(v) > 4000:
            raise ValueError("Message text cannot exceed 4000 characters")
        return v.strip()

    def parse_channel(self) -> Dict[str, Any]:
        """Parse channel identifier."""
        channel_request = SlackChannelIdentifierRequest(identifier=self.channel)
        return channel_request.parse()


class SlackUserGroupRequest(BaseModel):
    """Request model for Slack user group operations."""
    user_id: str = Field(..., description="User ID")
    group_id: str = Field(..., description="Group ID")
    
    def parse_user(self) -> Dict[str, Any]:
        """Parse user identifier."""
        user_request = SlackUserIdentifierRequest(identifier=self.user_id)
        return user_request.parse()
    
    def parse_group(self) -> Dict[str, Any]:
        """Parse group identifier."""
        group_request = SlackGroupIdentifierRequest(identifier=self.group_id)
        return group_request.parse()