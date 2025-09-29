from __future__ import annotations
from pydantic import BaseModel
from typing import List, Optional, TYPE_CHECKING
import datetime
from backend.shared.model_config import BaseModelConfig
from backend.modules.integrations.shopify.models.orders import Order

if TYPE_CHECKING:
    from .orders import Order

class Customer(BaseModel):
    model_config = BaseModelConfig
    id: str
    created_at: datetime.datetime
    default_email: Optional[str]
    default_phone_number: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    last_order: Optional["Order"]
    tags: List[Optional[str]]