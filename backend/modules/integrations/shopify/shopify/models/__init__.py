"""Lightweight shopify models package API."""

from .requests import (
    FetchOrderRequest,
    ShopifyOrderIdentifierRequest,
    ShopifyProductIdentifierRequest,
    ShopifyCustomerIdentifierRequest,
    PaginationRequest,
    DateRangeRequest
)
from .api_models import (
    OrderResponse,
    OrderListResponse,
    ProductResponse,
    ProductListResponse,
    CustomerResponse,
    CustomerListResponse,
    OrderCancelRequest,
    OrderRefundRequest,
    OrderDiscountRequest,
    OrderStatus,
    ProductStatus,
    RefundType,
    DiscountType,
    OrderCancelReason
)

__all__ = [
    # Legacy
    "FetchOrderRequest",
    # New Request Models
    "ShopifyOrderIdentifierRequest",
    "ShopifyProductIdentifierRequest", 
    "ShopifyCustomerIdentifierRequest",
    "PaginationRequest",
    "DateRangeRequest",
    # API Models
    "OrderResponse",
    "OrderListResponse",
    "ProductResponse",
    "ProductListResponse",
    "CustomerResponse",
    "CustomerListResponse",
    "OrderCancelRequest",
    "OrderRefundRequest",
    "OrderDiscountRequest",
    # Enums
    "OrderStatus",
    "ProductStatus",
    "RefundType",
    "DiscountType",
    "OrderCancelReason",
]

