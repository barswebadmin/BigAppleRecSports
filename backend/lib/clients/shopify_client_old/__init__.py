"""Shopify Admin GraphQL client package."""

from .client import ShopifyClient
from .gql import GqlQuery, GqlResult, build_shopify_gid
from .product_image import ProductImage
from .models import (
    OrderCreateResult,
    OrderCreateWebhook,
    OrderLineItemResult,
    ProductUpdateResult,
    ProductUpdateWebhook,
    process_order_create,
    process_product_update,
)
from .queries import (
    AdjustInventory,
    AttachProductMedia,
    BulkUpdateVariantPrices,
    DeleteProductMedia,
    FileUpdateProductRef,
    GetAllOrdersForExport,
    GetCustomer,
    GetInventoryInfo,
    GetMediaImageUrl,
    GetOrdersByProduct,
    GetProduct,
    GetVariant,
    SearchCustomerByEmail,
    SearchCustomersByEmails,
    UpdateCustomerTags,
    UpdateProduct,
)

__all__ = [
    "ShopifyClient",
    "GqlQuery",
    "GqlResult",
    "ProductImage",
    "OrderCreateWebhook",
    "OrderCreateResult",
    "OrderLineItemResult",
    "ProductUpdateWebhook",
    "ProductUpdateResult",
    "process_order_create",
    "process_product_update",
    "build_shopify_gid",
    "AdjustInventory",
    "AttachProductMedia",
    "BulkUpdateVariantPrices",
    "DeleteProductMedia",
    "FileUpdateProductRef",
    "GetAllOrdersForExport",
    "GetCustomer",
    "GetInventoryInfo",
    "GetMediaImageUrl",
    "GetOrdersByProduct",
    "GetProduct",
    "GetVariant",
    "SearchCustomerByEmail",
    "SearchCustomersByEmails",
    "UpdateCustomerTags",
    "UpdateProduct",
]
