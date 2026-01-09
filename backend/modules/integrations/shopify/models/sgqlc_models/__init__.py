"""
SGQLC models for Shopify GraphQL API.

These are separate from Pydantic models and use sgqlc Type syntax.
"""

from .customer import (
    Address,
    Customer,
    CustomerConnection,
)
from .order import (
    MoneySet,
    MoneySetWrapper,
    RefundTransaction,
    RefundTransactionConnection,
    Refund,
    LineItemReference,
    RefundLineItem,
    RefundLineItemConnection,
    Transaction,
    TransactionConnection,
    CustomAttribute,
    InventoryItem,
    LineItemVariant,
    DiscountApplication,
    DiscountApplicationConnection,
    LineItem,
    LineItemConnection,
    Order,
    OrderConnection,
)
from .product import (
    Image,
    ImageConnection,
    ProductOptionValue,
    Metafield,
    MetafieldConnection,
    Collection,
    CollectionConnection,
    Product,
    ProductConnection,
)

__all__ = [
    # Customer models
    'Address',
    'Customer',
    'CustomerConnection',
    # Order models
    'MoneySet',
    'MoneySetWrapper',
    'RefundTransaction',
    'RefundTransactionConnection',
    'Refund',
    'LineItemReference',
    'RefundLineItem',
    'RefundLineItemConnection',
    'Transaction',
    'TransactionConnection',
    'CustomAttribute',
    'InventoryItem',
    'LineItemVariant',
    'DiscountApplication',
    'DiscountApplicationConnection',
    'LineItem',
    'LineItemConnection',
    'Order',
    'OrderConnection',
    # Product models
    'Image',
    'ImageConnection',
    'ProductOptionValue',
    'Metafield',
    'MetafieldConnection',
    'Collection',
    'CollectionConnection',
    'Product',
    'ProductConnection',
]

