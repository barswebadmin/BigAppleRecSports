"""
Shopify API Models

Pydantic models for Shopify API request/response validation and serialization.
These models define the API contract for all Shopify endpoints.
"""

import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import Field, validator

from backend.shared.model_config import ApiModel
from backend.shared.api_models import (
    SuccessResponse,
    ListResponse
)


# ============================================================================
# ENUMS
# ============================================================================

class OrderCancelReason(str, Enum):
    """Order cancellation reasons."""
    CUSTOMER = "CUSTOMER"
    FRAUD = "FRAUD"
    INVENTORY = "INVENTORY"
    DECLINED = "DECLINED"
    OTHER = "OTHER"


class RefundType(str, Enum):
    """Refund types."""
    REFUND = "refund"  # Original payment method
    CREDIT = "credit"  # Store credit


class DiscountType(str, Enum):
    """Discount types."""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"


class OrderStatus(str, Enum):
    """Order status values."""
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ProductStatus(str, Enum):
    """Product status values."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"


# ============================================================================
# ORDER MODELS
# ============================================================================

class LineItemModel(ApiModel):
    """Line item model for orders."""
    id: str
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    title: str
    quantity: int
    price: str
    total_discount: Optional[str] = None
    custom_attributes: Optional[List[Dict[str, Any]]] = None


class CustomerModel(ApiModel):
    """Customer model for orders."""
    id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class OrderResponse(SuccessResponse):
    """Response model for single order."""
    data: Dict[str, Any] = Field(default_factory=dict)

    @validator('data')
    def validate_order_data(cls, v):
        """Validate order data structure."""
        required_fields = ['id', 'order_number', 'email', 'total_price', 'currency']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Order data must contain '{field}' field")
        return v


class OrderListResponse(ListResponse):
    """Response model for order list."""


class OrderCancelRequest(ApiModel):
    """Request model for order cancellation."""
    reason: OrderCancelReason = Field(
        default=OrderCancelReason.CUSTOMER, description="Cancellation reason"
    )
    notify_customer: bool = Field(default=False, description="Whether to notify the customer")
    refund: bool = Field(default=False, description="Whether to automatically refund")
    restock: bool = Field(default=False, description="Whether to restock inventory")
    staff_note: Optional[str] = Field(None, description="Optional staff note")

class OrderRefundRequest(ApiModel):
    """Request model for order refund."""
    amount: Optional[float] = Field(
        None, ge=0, description="Refund amount (if not specified, will calculate)"
    )
    refund_type: RefundType = Field(default=RefundType.REFUND, description="Type of refund")
    reason: Optional[str] = Field(None, description="Refund reason")
    notify_customer: bool = Field(default=True, description="Whether to notify the customer")
    submitted_at: Optional[str] = Field(None, description="Submission timestamp in ISO format")

    @validator('submitted_at')
    def validate_submitted_at(cls, v):
        """Validate submitted_at timestamp format."""
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError as exc:
                raise ValueError(
                    "submitted_at must be in ISO format (YYYY-MM-DDTHH:MM:SSZ)"
                ) from exc
        return v


class OrderDiscountRequest(ApiModel):
    """Request model for order discount."""
    discount_type: DiscountType = Field(..., description="Type of discount")
    discount_value: float = Field(..., gt=0, description="Discount value (percentage or amount)")
    reason: Optional[str] = Field(None, description="Discount reason")

    @validator('discount_value')
    def validate_discount_value(cls, v, values):
        """Validate discount value based on type."""
        discount_type = values.get('discount_type')
        if discount_type == DiscountType.PERCENTAGE and v > 100:
            raise ValueError("Percentage discount cannot exceed 100%")
        return v

# ============================================================================
# PRODUCT MODELS
# ============================================================================

class VariantModel(ApiModel):
    """Product variant model."""
    id: str
    product_id: str
    title: str
    price: str
    sku: Optional[str] = None
    inventory_quantity: Optional[int] = None
    inventory_management: Optional[str] = None


class ProductResponse(SuccessResponse):
    """Response model for single product."""
    data: Dict[str, Any] = Field(default_factory=dict)

    @validator('data')
    def validate_product_data(cls, v):
        """Validate product data structure."""
        required_fields = ['id', 'title', 'handle', 'status']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Product data must contain '{field}' field")
        return v


class ProductListResponse(ListResponse):
    """Response model for product list."""


class ProductUpdateRequest(ApiModel):
    """Request model for product updates."""
    title: Optional[str] = Field(None, description="Product title")
    body_html: Optional[str] = Field(None, description="Product description HTML")
    vendor: Optional[str] = Field(None, description="Product vendor")
    product_type: Optional[str] = Field(None, description="Product type")
    tags: Optional[str] = Field(None, description="Product tags (comma-separated)")
    status: Optional[ProductStatus] = Field(None, description="Product status")
    published: Optional[bool] = Field(None, description="Whether product is published")
# ============================================================================
# CUSTOMER MODELS
# ============================================================================

class AddressModel(ApiModel):
    """Customer address model."""
    id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    address1: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None


class CustomerResponse(SuccessResponse):
    """Response model for single customer."""
    data: Dict[str, Any] = Field(default_factory=dict)

    @validator('data')
    def validate_customer_data(cls, v):
        """Validate customer data structure."""
        required_fields = ['id', 'email']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Customer data must contain '{field}' field")
        return v


class CustomerListResponse(ListResponse):
    """Response model for customer list."""


class CustomerUpdateRequest(ApiModel):
    """Request model for customer updates."""
    first_name: Optional[str] = Field(None, description="Customer first name")
    last_name: Optional[str] = Field(None, description="Customer last name")
    email: Optional[str] = Field(None, description="Customer email")
    phone: Optional[str] = Field(None, description="Customer phone")
    tags: Optional[str] = Field(None, description="Customer tags (comma-separated)")
    note: Optional[str] = Field(None, description="Customer note")
    addresses: Optional[List[AddressModel]] = Field(None, description="Customer addresses")

    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        if v is not None:
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, v):
                raise ValueError("Invalid email format")
        return v
# ============================================================================
# FILTER MODELS
# ============================================================================

class OrderFilterParams(ApiModel):
    """Filter parameters for order list endpoint."""
    start_date: Optional[str] = Field(None, description="Start date in ISO format")
    end_date: Optional[str] = Field(None, description="End date in ISO format")
    status: Optional[OrderStatus] = Field(None, description="Filter by order status")
    financial_status: Optional[str] = Field(None, description="Filter by financial status")
    fulfillment_status: Optional[str] = Field(None, description="Filter by fulfillment status")
    customer_email: Optional[str] = Field(None, description="Filter by customer email")

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        """Validate ISO date format."""
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError as exc:
                raise ValueError("Date must be in ISO format (YYYY-MM-DDTHH:MM:SSZ)") from exc
        return v


class ProductFilterParams(ApiModel):
    """Filter parameters for product list endpoint."""
    start_date: Optional[str] = Field(None, description="Start date in ISO format")
    end_date: Optional[str] = Field(None, description="End date in ISO format")
    status: Optional[ProductStatus] = Field(None, description="Filter by product status")
    vendor: Optional[str] = Field(None, description="Filter by vendor")
    product_type: Optional[str] = Field(None, description="Filter by product type")
    published: Optional[bool] = Field(None, description="Filter by published status")

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        """Validate ISO date format."""
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError as exc:
                raise ValueError("Date must be in ISO format (YYYY-MM-DDTHH:MM:SSZ)") from exc
        return v


class CustomerFilterParams(ApiModel):
    """Filter parameters for customer list endpoint."""
    start_date: Optional[str] = Field(None, description="Start date in ISO format")
    end_date: Optional[str] = Field(None, description="End date in ISO format")
    email: Optional[str] = Field(None, description="Filter by email")
    phone: Optional[str] = Field(None, description="Filter by phone")
    tags: Optional[str] = Field(None, description="Filter by tags")

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        """Validate ISO date format."""
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError as exc:
                raise ValueError("Date must be in ISO format (YYYY-MM-DDTHH:MM:SSZ)") from exc
        return v

    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        if v is not None:
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, v):
                raise ValueError("Invalid email format")
        return v