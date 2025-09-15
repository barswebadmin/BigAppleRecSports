"""
Inventory Information model for product creation
"""

from pydantic import BaseModel, field_validator
from typing import Optional, Union


class InventoryInfo(BaseModel):
    """Inventory information for product creation"""

    price: Union[int, float]
    totalInventory: int
    numberVetSpotsToReleaseAtGoLive: Optional[int] = None

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, v):
        if isinstance(v, str):
            try:
                price_val = float(v)
            except ValueError:
                raise ValueError("Price must be a valid number")
        else:
            price_val = v

        if price_val <= 0:
            raise ValueError("Price must be greater than 0")
        return price_val

    @field_validator("totalInventory", mode="before")
    @classmethod
    def validate_inventory(cls, v):
        if isinstance(v, str):
            try:
                inventory_int = int(v)
            except ValueError:
                raise ValueError("Total inventory must be a valid integer")
        else:
            inventory_int = v

        if inventory_int <= 0:
            raise ValueError("Total inventory must be greater than 0")
        return inventory_int
