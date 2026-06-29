"""
Shopify API Models

Pydantic models for Shopify API request/response validation and serialization.
These models define the API contract for all Shopify endpoints.
"""

import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator

from shared_utilities.pydantic_config import DEFAULT_CONFIG_DICT
from shared_utilities import build_shopify_admin_url, extract_shopify_id


class SuccessResponse(BaseModel):
    """Success response model with data payload."""
    success: bool = True
    message: str = "Success"
    data: Any = None


class ListResponse(SuccessResponse):
    """List response model with pagination."""
    data: dict = Field(default_factory=dict)


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

class LineItemModel(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Line item model for orders."""
    id: str
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    title: str
    quantity: int
    price: str
    total_discount: Optional[str] = None
    custom_attributes: Optional[List[Dict[str, Any]]] = None


class CustomerModel(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Customer model for orders."""
    id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class OrderResponse(SuccessResponse):
    """Response model for single order.
    
    Accepts raw Shopify order data and adds computed fields:
    - 'number': Order number without leading '#'
    - 'url': Shopify admin URL for the order
    - 'order_number_link': CLI-formatted hyperlink combining number and URL
    - 'product_title': First line item product title
    - 'product_url': Shopify admin URL for the product
    - 'product_link': CLI-formatted hyperlink for product
    - 'form_email': Email from line item customAttributes (key contains 'email')
    - 'amount_paid': Total price from presentmentMoney
    - 'cancellation_status': Formatted cancellation info or "N/A"
    - 'refund_status': Formatted refund info or "N/A (Not Refunded)"
    """
    data: Dict[str, Any] = Field(default_factory=dict)

    @validator('data')
    def validate_and_alias_order_data(cls, v):
        """Validate order data and add computed fields for CLI display."""
        
        # Validate required fields
        if 'id' not in v:
            raise ValueError("Order data must contain 'id' field")
        
        # Extract order number (strip leading '#')
        if 'name' in v:
            name_value = v['name']
            if isinstance(name_value, str):
                v['number'] = name_value.lstrip('#')
            else:
                v['number'] = name_value
        
        # Build order URL
        if 'id' in v:
            order_id = v['id']
            if isinstance(order_id, str):
                v['url'] = build_shopify_admin_url('orders', order_id)
                # Create CLI-formatted hyperlink: \033]8;;URL\033\\TEXT\033]8;;\033\\
                v['order_number_link'] = f"\033]8;;{v['url']}\033\\#{v.get('number', 'N/A')}\033]8;;\033\\"
        
        # Extract first product info and email from line items
        line_items = v.get('lineItems', {})
        if isinstance(line_items, dict):
            nodes = line_items.get('nodes', [])
            if nodes and len(nodes) > 0:
                first_item = nodes[0]
                
                # Extract product info
                product = first_item.get('product', {})
                if product:
                    v['product_title'] = product.get('title', 'N/A')
                    product_id = product.get('id')
                    if product_id:
                        v['product_url'] = build_shopify_admin_url('products', product_id)
                        v['product_link'] = f"\033]8;;{v['product_url']}\033\\{v['product_title']}\033]8;;\033\\"
                
                # Extract email from customAttributes
                custom_attributes = first_item.get('customAttributes', [])
                if isinstance(custom_attributes, list):
                    for attr in custom_attributes:
                        if isinstance(attr, dict):
                            key = attr.get('key', '')
                            if 'email' in key.lower():
                                v['form_email'] = attr.get('value', 'N/A')
                                break
        
        # Extract amount paid from presentmentMoney
        total_price_set = v.get('totalPriceSet', {})
        if isinstance(total_price_set, dict):
            presentment_money = total_price_set.get('presentmentMoney', {})
            if isinstance(presentment_money, dict):
                v['amount_paid'] = presentment_money.get('amount', '0.00')
        
        # Format cancellation status
        cancelled_at = v.get('cancelledAt')
        cancel_reason = v.get('cancelReason')
        if cancelled_at:
            reason_text = cancel_reason if cancel_reason else 'No reason provided'
            v['cancellation_status'] = f"Canceled at {cancelled_at} ({reason_text})"
        else:
            v['cancellation_status'] = "N/A"
        
        # Format refund status with detailed information
        refunds = v.get('refunds')
        cancelled_at = v.get('cancelledAt')
        
        if refunds and isinstance(refunds, list) and len(refunds) > 0:
            refund_items = []
            has_actual_refund = False
            
            for refund in refunds:
                # Extract refund amount
                total_refunded_set = refund.get('totalRefundedSet', {})
                if isinstance(total_refunded_set, dict):
                    presentment_money = total_refunded_set.get('presentmentMoney', {})
                    if isinstance(presentment_money, dict):
                        refund_amount = presentment_money.get('amount', '0.00')
                    else:
                        refund_amount = '0.00'
                else:
                    refund_amount = '0.00'
                
                # Check if this is an actual refund (amount > 0)
                try:
                    if float(refund_amount) > 0:
                        has_actual_refund = True
                except (ValueError, TypeError):
                    pass
                
                # Extract refund method from first transaction
                refund_method = 'Unknown'
                transactions = refund.get('transactions', {})
                if isinstance(transactions, dict):
                    nodes = transactions.get('nodes', [])
                    if nodes and len(nodes) > 0:
                        first_transaction = nodes[0]
                        refund_method = first_transaction.get('gateway', 'Unknown')
                
                # Extract timestamp and reason
                refund_timestamp = refund.get('createdAt', 'Unknown date')
                refund_reason = refund.get('note', 'No reason provided')
                
                # Format: $115.0 refunded to shopify_payments at 2026-01-09T23:15:37Z (Customer request)
                refund_line = f"${refund_amount} refunded to {refund_method} at {refund_timestamp} ({refund_reason})"
                refund_items.append(refund_line)
            
            # If order was canceled but no actual refund amount, show special message
            if cancelled_at and not has_actual_refund:
                v['refund_status'] = "N/A (Canceled but not refunded)"
            else:
                # If multiple refunds, format with bullet points
                if len(refund_items) > 1:
                    v['refund_status'] = '\n- ' + '\n- '.join(refund_items)
                else:
                    v['refund_status'] = refund_items[0]
        else:
            v['refund_status'] = "N/A (Not Refunded)"
        
        return v


class OrderListResponse(ListResponse):
    """Response model for order list."""


class OrderCancelRequest(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Request model for order cancellation."""
    reason: OrderCancelReason = Field(
        default=OrderCancelReason.CUSTOMER, description="Cancellation reason"
    )
    notify_customer: bool = Field(default=False, description="Whether to notify the customer")
    refund: bool = Field(default=False, description="Whether to automatically refund")
    restock: bool = Field(default=False, description="Whether to restock inventory")
    staff_note: Optional[str] = Field(None, description="Optional staff note")

class OrderRefundRequest(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
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


class OrderDiscountRequest(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
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

class VariantModel(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
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


class ProductUpdateRequest(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
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

class AddressModel(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
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


class CustomerUpdateRequest(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
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

class OrderFilterParams(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
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


class ProductFilterParams(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
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


class CustomerFilterParams(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
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