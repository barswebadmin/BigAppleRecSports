"""
SGQLC models for Shopify GraphQL API.

Direct sgqlc Type definitions (separate from Pydantic models).
Import from here to get sgqlc Type classes for query generation.
"""

# Import direct sgqlc Type definitions
from backend.modules.integrations.shopify.models.sgqlc_models.customer_sgqlc import (
    Address,
    Customer,
    CustomerConnection,
)

from backend.modules.integrations.shopify.models.sgqlc_models.order_sgqlc import (
    MoneySet,
    MoneySetWrapper,
    InventoryItem,
    LineItemVariant,
    CustomAttribute,
    DiscountApplication,
    DiscountApplicationConnection,
    LineItem,
    LineItemConnection,
    RefundLineItem,
    RefundLineItemConnection,
    RefundTransaction,
    RefundTransactionConnection,
    Transaction,
    Refund,
    Order,
    OrderConnection,
)

# Import Pydantic models (for data validation/parsing)
from backend.modules.integrations.shopify.models.sgqlc_models.customer_pydantic import (
    Address as AddressPydantic,
    Customer as CustomerPydantic,
)
from backend.modules.integrations.shopify.models.sgqlc_models.order_pydantic import (
    MoneySet as MoneySetPydantic,
    MoneySetWrapper as MoneySetWrapperPydantic,
    RefundTransaction as RefundTransactionPydantic,
    Refund as RefundPydantic,
    RefundLineItem as RefundLineItemPydantic,
    Transaction as TransactionPydantic,
    CustomAttribute as CustomAttributePydantic,
    InventoryItem as InventoryItemPydantic,
    LineItemVariant as LineItemVariantPydantic,
    DiscountApplication as DiscountApplicationPydantic,
    LineItem as LineItemPydantic,
    Order as OrderPydantic,
)

# Import Pydantic models for products (for data validation/parsing)
from backend.modules.integrations.shopify.models.sgqlc_models.product_pydantic import (
    Image as ImagePydantic,
    ProductOptionValue as ProductOptionValuePydantic,
    Metafield as MetafieldPydantic,
    Collection as CollectionPydantic,
    Product as ProductPydantic,
)

# Product models - TODO: Create separate sgqlc types when needed
# For now, keep using bridge for products
from backend.modules.integrations.shopify.models.sgqlc_models.sgqlc_bridge import get_sgqlc_type, get_connection_type

Image = get_sgqlc_type(ImagePydantic)
ImageConnection = get_connection_type(ImagePydantic)  # Used in Product.images
ProductOptionValue = get_sgqlc_type(ProductOptionValuePydantic)
Metafield = get_sgqlc_type(MetafieldPydantic)
MetafieldConnection = get_connection_type(MetafieldPydantic)  # Used in Product.metafields
Collection = get_sgqlc_type(CollectionPydantic)
CollectionConnection = get_connection_type(CollectionPydantic)  # Used in Product.collections
Product = get_sgqlc_type(ProductPydantic)
ProductConnection = get_connection_type(ProductPydantic)

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
    'RefundLineItem',
    'Transaction',
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
