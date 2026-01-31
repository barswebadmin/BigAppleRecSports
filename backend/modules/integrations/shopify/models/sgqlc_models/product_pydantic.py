"""
Product models for Shopify GraphQL API.

Uses forward references to avoid circular imports.
"""

from typing import List, TYPE_CHECKING, Optional
from pydantic import BaseModel, Field

from modules.integrations.shopify.models.sgqlc_models.common_pydantic import Connection

from modules.integrations.shopify.models.sgqlc_models.common_pydantic import ShopifyBaseModel, create_list_model

if TYPE_CHECKING:
    pass


class Image(BaseModel):
    """Image model for products."""
    url: Optional[str] = None
    altText: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class ProductOptionValue(BaseModel):
    """Product option value."""
    id: Optional[str] = None
    name: Optional[str] = None
    values: List[str] = Field(default_factory=list)


class Metafield(BaseModel):
    """Metafield model."""
    id: Optional[str] = None
    key: Optional[str] = None
    value: Optional[str] = None
    namespace: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None


class Collection(BaseModel):
    """Collection model."""
    id: Optional[str] = None
    title: Optional[str] = None
    handle: Optional[str] = None
    description: Optional[str] = None


@create_list_model
class Product(ShopifyBaseModel):
    """Complete product model with type safety."""
    id: str
    title: Optional[str] = None
    descriptionHtml: Optional[str] = None
    handle: Optional[str] = None
    status: Optional[str] = None
    productType: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    publishedAt: Optional[str] = None
    onlineStoreUrl: Optional[str] = None
    totalInventory: Optional[int] = None
    tracksInventory: Optional[bool] = None
    featuredImage: Optional[Image] = None
    images: Optional[Connection[Image]] = None  # Defaults to first=2 in queries
    options: List[ProductOptionValue] = Field(default_factory=list)
    metafields: Optional[Connection[Metafield]] = None
    collections: Optional[Connection[Collection]] = None

