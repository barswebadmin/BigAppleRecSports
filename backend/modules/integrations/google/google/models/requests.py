"""Google API request models."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator
from shared_utilities.validators import validators


class GetGoogleGroupsRequest(BaseModel):
    """Request model for listing Google Workspace groups."""

    domain: Optional[str] = Field(
        default=None,
        description="Domain name to list groups for"
    )
    customer: Optional[str] = Field(
        default=None,
        description="Customer ID or 'my_customer' for the current customer"
    )
    max_results: int = Field(
        default=200,
        ge=1,
        le=500,
        description="Maximum number of results to return"
    )
    page_token: Optional[str] = Field(
        default=None,
        description="Token for pagination"
    )
    user_key: Optional[str] = Field(
        default=None,
        description="Email or ID of user to get groups for"
    )


class CreateGoogleGroupRequest(BaseModel):
    """Request model for creating a Google Workspace group."""

    email: str = Field(
        description="Group email address"
    )
    name: str = Field(
        min_length=1,
        max_length=75,
        description="Human-readable name for the group"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Optional description for the group"
    )

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format and append domain if needed."""
        if not validators.validate(v, 'email', strict=False):
            raise ValueError('Invalid email format')

        # Append domain if not present
        if '@' not in v:
            v = f"{v}@bigapplerecsports.com"
        elif not v.endswith('@bigapplerecsports.com'):
            # For now, only allow our domain
            raise ValueError('Group email must be in bigapplerecsports.com domain')

        return v.lower().strip()

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean group name."""
        v = v.strip()
        if not v:
            raise ValueError('Group name cannot be empty')
        return v

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean description."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


# Aliases for backward compatibility
GetGroupsRequest = GetGoogleGroupsRequest
