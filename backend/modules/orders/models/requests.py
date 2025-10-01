from pydantic import BaseModel
from typing import Optional
from shared.normalizers import (
    normalize_shopify_id,
    normalize_order_number,
    normalize_email,
)


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

        order_id = normalize_shopify_id(order_id_input)
        order_number = normalize_order_number(order_number_input)
        email = normalize_email(email_input)

        if not order_id_input and not order_number_input and not email_input:
            raise ValueError("Must provide a valid order_id, order_number, or email")
        
        # Check for invalid inputs that were provided but failed normalization
        if order_id_input is not None and order_id is None:
            raise ValueError(f"'{order_id_input}' is not a valid order_id")
        if order_number_input is not None and order_number is None:
            raise ValueError(f"'{order_number_input}' is not a valid order_number")
        if email_input is not None and email is None:
            raise ValueError(f"'{email_input}' is not a valid email")
            
        return cls(order_id=order_id, order_number=order_number, email=email)