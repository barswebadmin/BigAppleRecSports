"""
Shopify GraphQL Models

Centralized models for Shopify entities (Customer, Order, Product, etc.)
with proper forward references to avoid circular imports.

After importing, call resolve_forward_refs() to ensure all forward references
are properly resolved for Pydantic validation.
"""

import sys
from typing import List, Optional

from .common import Connection, Edge, PageInfo

from . import customer, order
from .common import (
    ShopifyResponse,
    ShopifyBaseModel,
    ShopifyListModel,
    create_list_model,
)
from .customer import (
    Customer,
    Address,
)
from .order import (
    Order,
    Refund,
    Transaction,
    LineItem,
    DiscountApplication,
    MoneySet,
    MoneySetWrapper,
    CustomAttribute,
    LineItemVariant,
)

# List classes are auto-created by @create_list_model decorator at runtime
# Access them from module globals (decorator exports them when modules are imported)
Customers = getattr(customer, 'Customers', None)  # type: ignore
Orders = getattr(order, 'Orders', None)  # type: ignore


def resolve_forward_refs():
    """
    Resolve all forward references after models are loaded.
    
    Call this after importing all models to ensure Pydantic can properly
    validate forward references like Customer.orders -> List[Order]
    and Order.customer -> Customer.
    """
    # Import both modules to ensure they're loaded
    from . import customer, order
    
    # Create namespace with both models for forward reference resolution
    from .order import LineItem, DiscountApplication
    namespace = {
        'Order': Order,
        'Customer': Customer,
        'LineItem': LineItem,
        'DiscountApplication': DiscountApplication,
        'List': List,
        'Optional': Optional,
    }
    
    # Rebuild models with proper namespace
    Customer.model_rebuild(_types_namespace=namespace)
    Order.model_rebuild(_types_namespace=namespace)


# Auto-resolve on import
resolve_forward_refs()


__all__ = [
    "Customer",
    "Customers",
    "Address",
    "Order",
    "Orders",
    "Refund",
    "Transaction",
    "LineItem",
    "DiscountApplication",
    "MoneySet",
    "MoneySetWrapper",
    "CustomAttribute",
    "LineItemVariant",
    "PageInfo",
    "Edge",
    "Connection",
    "ShopifyResponse",
    "ShopifyBaseModel",
    "ShopifyListModel",
    "create_list_model",
    "resolve_forward_refs",
]

