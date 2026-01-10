from __future__ import annotations
from typing import Optional, TYPE_CHECKING
import datetime
from shared.model_config import ApiModel
from ..models.orders import Order

if TYPE_CHECKING:
    from .orders import Order

class Customer(ApiModel):
    id: str
    created_at: datetime.datetime
    default_email: Optional[str]
    default_phone_number: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    last_order: Optional["Order"]
    tags: list[Optional[str]]