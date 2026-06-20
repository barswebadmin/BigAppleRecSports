"""Shopify GraphQL query descriptors by resource type."""

from .customers import (
    GetCustomer,
    SearchCustomerByEmail,
    SearchCustomersByEmails,
    UpdateCustomerTags,
)
from .media import (
    AttachProductMedia,
    DeleteProductMedia,
    FileUpdateProductRef,
    GetMediaImageUrl,
)
from .orders import GetOrdersByProduct
from .export_orders import GetAllOrdersForExport
from .products import (
    BulkUpdateVariantPrices,
    GetProduct,
    UpdateProduct,
)
from .variants import AdjustInventory, GetInventoryInfo, GetVariant

__all__ = [
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
