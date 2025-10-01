from pydantic import BaseModel
from typing import Optional
from shared.normalizers import (
    normalize_shopify_id,
)


class FetchProductRequest(BaseModel):
    """
    Product lookup request using product identifiers.
    At least one of product_id or product_handle must be provided.
    - product_id: Shopify numeric product id (no gid prefix)
    - product_handle: Shopify product handle (URL-safe string)
    """

    product_id: Optional[str] = None
    product_handle: Optional[str] = None

    @classmethod
    def create(cls, data: dict) -> "FetchProductRequest":
        """
        Flexible factory accepting a dict like {"product_id": "123456789"}
        or {"product_handle": "my-awesome-product"}.
        """
        product_id_input = data.get("product_id")
        product_handle_input = data.get("product_handle")

        product_id = normalize_shopify_id(product_id_input)
        product_handle = product_handle_input

        if not product_id_input and not product_handle_input:
            raise ValueError("Must provide a valid product_id or product_handle")
        
        # Check for invalid inputs that were provided but failed normalization
        if product_id_input is not None and product_id is None:
            raise ValueError(f"'{product_id_input}' is not a valid product_id")
        
        return cls(product_id=product_id, product_handle=product_handle)


