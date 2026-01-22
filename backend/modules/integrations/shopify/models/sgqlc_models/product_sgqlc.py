"""Product sgqlc Type definitions.

Direct sgqlc Type definitions for Product models.
These are separate from Pydantic models and defined directly using sgqlc's Type system.
"""

from sgqlc.types import Type, Field, String, Int, Boolean, list_of
from sgqlc.types.relay import Connection, connection_args

# Import InventoryItem from order_sgqlc to avoid duplication
from backend.modules.integrations.shopify.models.sgqlc_models.order_sgqlc import InventoryItem


class Image(Type):
    """Image model for products."""
    url = Field(String)
    altText = Field(String)
    width = Field(Int)
    height = Field(Int)


class ImageConnection(Connection):
    """Image Connection type."""
    nodes = list_of(Image)


class ProductOption(Type):
    """Product option model."""
    id = Field(String)
    name = Field(String)
    values = Field(list_of(String))


class Metafield(Type):
    """Metafield model."""
    id = Field(String)
    key = Field(String)
    value = Field(String)
    namespace = Field(String)
    type = Field(String)
    description = Field(String)


class MetafieldConnection(Connection):
    """Metafield Connection type."""
    nodes = list_of(Metafield)


class Collection(Type):
    """Collection model."""
    id = Field(String)
    title = Field(String)
    handle = Field(String)
    description = Field(String)


class CollectionConnection(Connection):
    """Collection Connection type."""
    nodes = list_of(Collection)


class SEO(Type):
    """SEO model."""
    title = Field(String)
    description = Field(String)


class Money(Type):
    """Money model with amount and currency."""
    amount = Field(String)
    currencyCode = Field(String)


class PriceRange(Type):
    """Price range model."""
    minVariantPrice = Field(Money)
    maxVariantPrice = Field(Money)


class CompareAtPriceRange(Type):
    """Compare at price range model."""
    minVariantCompareAtPrice = Field(Money)
    maxVariantCompareAtPrice = Field(Money)


class SellingPlanGroup(Type):
    """Selling plan group model."""
    id = Field(String)
    name = Field(String)
    summary = Field(String)


class SellingPlanGroupConnection(Connection):
    """Selling plan group Connection type."""
    nodes = list_of(SellingPlanGroup)


class ProductVariant(Type):
    """Product variant model."""
    id = Field(String)
    title = Field(String)
    displayName = Field(String)
    price = Field(String)
    inventoryQuantity = Field(Int)
    inventoryItem = Field(InventoryItem)
    product = Field('Product')  # Forward reference


class ProductVariantConnection(Connection):
    """Product variant Connection type."""
    nodes = list_of(ProductVariant)


class Product(Type):
    """Product sgqlc Type."""
    id = Field(String)
    title = Field(String)
    description = Field(String)
    descriptionHtml = Field(String)
    vendor = Field(String)
    handle = Field(String)
    status = Field(String)
    productType = Field(String)
    tags = Field(list_of(String))
    createdAt = Field(String)
    updatedAt = Field(String)
    publishedAt = Field(String)
    onlineStoreUrl = Field(String)
    onlineStorePreviewUrl = Field(String)
    totalInventory = Field(Int)
    tracksInventory = Field(Boolean)
    featuredImage = Field(Image)
    images = Field(ImageConnection, args=connection_args())
    options = Field(list_of(ProductOption))
    metafields = Field(MetafieldConnection, args=connection_args())
    collections = Field(CollectionConnection, args=connection_args())
    seo = Field(SEO)
    priceRange = Field(PriceRange)
    compareAtPriceRange = Field(CompareAtPriceRange)
    giftCardTemplateSuffix = Field(String)
    requiresSellingPlan = Field(Boolean)
    sellingPlanGroups = Field(SellingPlanGroupConnection, args=connection_args())
    variants = Field(ProductVariantConnection, args=connection_args())


class ProductConnection(Connection):
    """Product Connection type."""
    nodes = list_of(Product)
