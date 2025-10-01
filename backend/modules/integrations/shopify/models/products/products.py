from __future__ import annotations
from pydantic import BaseModel
from typing import List, Optional

class Product(BaseModel):
    id: str
    title: str
    handle: Optional[str]
    description: Optional[str]
    variants: Optional[List["Variant"]]

class Variant(BaseModel):
    id: str
    name: str
    price: Optional[float]
    inventory: Optional[int]
    inventory_item_id: Optional[str]