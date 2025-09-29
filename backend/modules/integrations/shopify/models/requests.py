from pydantic import BaseModel, field_validator
from typing import Optional
from backend.shared.shopify_normalizers import (
    normalize_order_id,
    normalize_order_number,
)
from backend.shared.validators import validate_email_format


class FetchOrderRequest(BaseModel):
    """
    Order lookup request using digits-only identifiers.
    At least one of order_id, order_number, or email must be provided.
    - order_id: Shopify numeric order id (no gid)
    - order_number: Shopify numeric order number (no leading '#')
    - email: Shopify order email
    """

    order_id: Optional[str] = None
    order_number: Optional[str] = None
    email: Optional[str] = None

    @classmethod
    def create(cls, data: dict) -> "FetchOrderRequest":
        """
        Flexible factory accepting a dict like {"order_number": "43298"}
        or {"order_id": "5885712466014"} or {"email": "user@example.com"}.
        """
        order_id_input = data.get("order_id")
        order_number_input = data.get("order_number")
        email_input = data.get("email")

        norm_id = normalize_order_id(order_id_input) if order_id_input else None
        order_id = norm_id.get("digits_only") if norm_id else None
        
        norm_num = normalize_order_number(order_number_input) if order_number_input else None
        order_number = norm_num.get("digits_only") if norm_num else None

        email = email_input if validate_email_format(email_input).get("success") else None

        if not order_id and not order_number and not email:
            raise ValueError("Must provide a valid order_id, order_number, or email")
        return cls(order_id=order_id, order_number=order_number, email=email)


