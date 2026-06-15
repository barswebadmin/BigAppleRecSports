"""Typed Shopify Admin client.

Re-exports the public surface so callers can write
``from shopify_client import ShopifyClient, ShopifyUserError``.
"""

from .client import (
    CustomerSearchQuery,
    InventoryAdjustResult,
    OrderSearchQuery,
    ProductSearchQuery,
    ShopifyClient,
    VariantUpdate,
)
from .exceptions import ShopifyUserError, raise_if_user_errors

__all__ = [
    "CustomerSearchQuery",
    "InventoryAdjustResult",
    "OrderSearchQuery",
    "ProductSearchQuery",
    "ShopifyClient",
    "ShopifyUserError",
    "VariantUpdate",
    "raise_if_user_errors",
]
