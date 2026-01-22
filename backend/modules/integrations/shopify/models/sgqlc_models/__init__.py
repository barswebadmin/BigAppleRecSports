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

# Import direct sgqlc Type definitions for products
from backend.modules.integrations.shopify.models.sgqlc_models.product_sgqlc import (
    Image,
    ImageConnection,
    ProductOption,
    Metafield,
    MetafieldConnection,
    Collection,
    CollectionConnection,
    SEO,
    Money,
    PriceRange,
    CompareAtPriceRange,
    SellingPlanGroup,
    SellingPlanGroupConnection,
    InventoryItem,
    ProductVariant,
    ProductVariantConnection,
    Product,
    ProductConnection,
)

# Import direct sgqlc Type definitions for locations
from backend.modules.integrations.shopify.models.sgqlc_models.location_sgqlc import (
    Location,
    LocationConnection,
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
    'ProductOption',
    'Metafield',
    'MetafieldConnection',
    'Collection',
    'CollectionConnection',
    'SEO',
    'Money',
    'PriceRange',
    'CompareAtPriceRange',
    'SellingPlanGroup',
    'SellingPlanGroupConnection',
    'InventoryItem',
    'ProductVariant',
    'ProductVariantConnection',
    'Product',
    'ProductConnection',
    # Location models
    'Location',
    'LocationConnection',
]
