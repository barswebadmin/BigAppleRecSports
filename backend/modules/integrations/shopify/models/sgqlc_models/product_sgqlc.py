"""Product variant sgqlc Type definitions."""

from sgqlc.types import Type, Field, String, ID, Int
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class ProductVariant(Type):
    """Product variant model."""
    id = Field(ID)
    title = Field(String)
    displayName = Field(String)
    inventoryQuantity = Field(Int)
    inventoryItem = Field('InventoryItem')  # Forward reference
    product = Field('Product')  # Forward reference

