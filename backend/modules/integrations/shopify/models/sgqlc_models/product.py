"""
SGQLC Product models for Shopify GraphQL API.
"""

from typing import TYPE_CHECKING
from sgqlc.types import Type, Field, String, Int, Boolean, list_of
from sgqlc.types.relay import Connection, connection_args

if TYPE_CHECKING:
    from .product_pydantic import ProductConnection


class Image(Type):
    """Image model for products."""
    url = String
    altText = String
    width = Int
    height = Int


class ImageConnection(Connection):
    """Image connection."""
    nodes = list_of(Image)


class ProductOptionValue(Type):
    """Product option value."""
    id = String
    name = String
    values = list_of(String)


class Metafield(Type):
    """Metafield model."""
    id = String
    key = String
    value = String
    namespace = String
    type = String
    description = String


class MetafieldConnection(Connection):
    """Metafield connection."""
    nodes = list_of(Metafield)


class Collection(Type):
    """Collection model."""
    id = String
    title = String
    handle = String
    description = String


class CollectionConnection(Connection):
    """Collection connection."""
    nodes = list_of(Collection)


class Product(Type):
    """Complete product model with type safety."""
    id = String
    title = String
    descriptionHtml = String
    handle = String
    status = String
    productType = String
    tags = list_of(String)
    createdAt = String
    updatedAt = String
    publishedAt = String
    onlineStoreUrl = String
    totalInventory = Int
    tracksInventory = Boolean
    featuredImage = Image
    images = Field(ImageConnection, args=connection_args())  # Defaults to first=2 in queries
    options = list_of(ProductOptionValue)
    metafields = Field(MetafieldConnection, args=connection_args())
    collections = Field(CollectionConnection, args=connection_args())


class ProductConnection(Connection):
    """Product connection with nodes."""
    nodes = list_of(Product)

