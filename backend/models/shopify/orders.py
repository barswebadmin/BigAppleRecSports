from __future__ import annotations
from pydantic import BaseModel
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .customers import Customer
    from .transactions import Transaction

class Order(BaseModel):
    id: str
    name: str
    email: str
    customer: "Customer"
    transactions: List["Transaction"]
