"""
Shopify Request Models

Pydantic models for validating and parsing Shopify API requests.
These models handle identifier parsing, validation, and return proper validation errors.
"""

import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator

from backend.shared.api_models import ValidationAPIError


# ============================================================================
# IDENTIFIER REQUEST MODELS
# ============================================================================

class ShopifyOrderIdentifierRequest(BaseModel):
    """Request model for Shopify order identifier parsing and validation."""
    identifier: str = Field(..., min_length=1, description="Order identifier")

    @validator('identifier')
    def validate_identifier(cls, v):
        """Validate order identifier."""
        if not v or not v.strip():
            raise ValueError("Order identifier cannot be empty")
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
            if identifier.startswith('#'):
                # Order number format: #1001
                return {"order_number": identifier[1:]}
            if identifier.startswith('gid://shopify/Order/'):
                # GraphQL ID format: gid://shopify/Order/123456
                order_id = identifier.split('/')[-1]
                return {"order_id": order_id}
            if identifier.isdigit():
                # Could be order number or ID - let service handle both
                return {"identifier": identifier}
            
            raise ValueError(f"Invalid order identifier format: {identifier}")
        except ValueError as e:
            raise ValidationAPIError(
                message=str(e),
                field_errors={"identifier": [str(e)]}
            ) from e


class ShopifyProductIdentifierRequest(BaseModel):
    """Request model for Shopify product identifier parsing and validation."""
    identifier: str = Field(..., min_length=1, description="Product identifier")

    @validator('identifier')
    def validate_identifier(cls, v):
        """Validate product identifier."""
        if not v or not v.strip():
            raise ValueError("Product identifier cannot be empty")
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
            if identifier.startswith('gid://shopify/Product/'):
                # GraphQL ID format: gid://shopify/Product/123456
                product_id = identifier.split('/')[-1]
                return {"product_id": product_id}
            if identifier.isdigit():
                # Numeric product ID
                return {"product_id": identifier}
            
            # Assume it's a SKU or handle
            return {"identifier": identifier}
        except ValueError as e:
            raise ValidationAPIError(
                message=str(e),
                field_errors={"identifier": [str(e)]}
            ) from e


class ShopifyCustomerIdentifierRequest(BaseModel):
    """Request model for Shopify customer identifier parsing and validation."""
    identifier: str = Field(..., min_length=1, description="Customer identifier")

    @validator('identifier')
    def validate_identifier(cls, v):
        """Validate customer identifier."""
        if not v or not v.strip():
            raise ValueError("Customer identifier cannot be empty")
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
            if identifier.startswith('gid://shopify/Customer/'):
                # GraphQL ID format: gid://shopify/Customer/123456
                customer_id = identifier.split('/')[-1]
                return {"customer_id": customer_id}
            if identifier.isdigit():
                # Numeric customer ID
                return {"customer_id": identifier}
            
            raise ValueError(f"Invalid customer identifier format: {identifier}")
        except ValueError as e:
            raise ValidationAPIError(
                message=str(e),
                field_errors={"identifier": [str(e)]}
            ) from e


# ============================================================================
# PAGINATION AND FILTERING REQUEST MODELS
# ============================================================================

class PaginationRequest(BaseModel):
    """Request model for pagination parameters."""
    limit: Optional[int] = Field(default=50, ge=1, le=1000, description="Items per page")
    offset: Optional[int] = Field(default=0, ge=0, description="Items to skip")

    def validate_and_normalize(self) -> tuple[int, int]:
        """
        Validate and return normalized pagination parameters.
        
        Returns:
            Tuple of (limit, offset)
            
        Raises:
            ValidationAPIError: If parameters are invalid
        """
        try:
            limit = self.limit or 50
            offset = self.offset or 0
            
            if limit < 1 or limit > 1000:
                raise ValueError("Limit must be between 1 and 1000")
            
            if offset < 0:
                raise ValueError("Offset must be non-negative")
            
            return limit, offset
        except ValueError as e:
            raise ValidationAPIError(
                message=str(e),
                field_errors={"pagination": [str(e)]}
            ) from e


class DateRangeRequest(BaseModel):
    """Request model for date range filtering."""
    start_date: Optional[str] = Field(None, description="Start date in ISO format")
    end_date: Optional[str] = Field(None, description="End date in ISO format")

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        """Validate ISO date format."""
        if v is not None:
            try:
                from datetime import datetime
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError as exc:
                raise ValueError("Date must be in ISO format (YYYY-MM-DDTHH:MM:SSZ)") from exc
        return v

    def validate_and_parse(self) -> tuple[Optional[str], Optional[str]]:
        """
        Validate date range and return normalized dates.
        
        Returns:
            Tuple of (start_date, end_date)
            
        Raises:
            ValidationAPIError: If date range is invalid
        """
        try:
            if self.start_date and self.end_date:
                from datetime import datetime
                start_dt = datetime.fromisoformat(self.start_date.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(self.end_date.replace('Z', '+00:00'))
                
                if start_dt > end_dt:
                    raise ValueError("start_date must be before end_date")
            
            return self.start_date, self.end_date
        except ValueError as e:
            raise ValidationAPIError(
                message=str(e),
                field_errors={"date_range": [str(e)]}
            ) from e


# ============================================================================
# LEGACY COMPATIBILITY
# ============================================================================

class FetchOrderRequest(BaseModel):
    """
    Legacy order lookup request using digits-only identifiers.
    At least one of order_id, order_number, or email must be provided.
    - order_id: Shopify numeric order id (no gid)
    - order_number: Shopify numeric order number (no leading '#')
    - email: Shopify order email
    """

    order_id: Optional[str] = None
    order_number: Optional[str] = None
    email: Optional[str] = None

    @classmethod
    def create(cls, data: dict) -> "FetchOrderRequest":
        """
        Flexible factory accepting a dict like {"order_number": "43298"}
        or {"order_id": "5885712466014"} or {"email": "user@example.com"}.
        """
        from backend.modules.integrations.shopify.services.shopify_normalizers import (
            normalize_order_number,
            normalize_order_identifier,
        )
        from backend.shared.validators import validate_email

        order_id_input = data.get("order_id")
        order_number_input = data.get("order_number")
        email_input = data.get("email")

        norm_id = normalize_order_identifier(order_id_input) if order_id_input else None
        order_id = norm_id.get("digits_only") if norm_id else None
        
        norm_num = normalize_order_number(order_number_input) if order_number_input else None
        order_number = norm_num.get("digits_only") if norm_num else None

        email = email_input if validate_email(email_input).is_valid else None

        if not order_id and not order_number and not email:
            raise ValueError("Must provide a valid order_id, order_number, or email")
        return cls(order_id=order_id, order_number=order_number, email=email)