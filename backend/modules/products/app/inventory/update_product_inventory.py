from typing import Dict, Any
from ...models import FetchProductRequest
from ..fetch_product_from_shopify import fetch_product_from_shopify

def update_product_inventory(request_details: FetchProductRequest) -> Dict[str, Any]:
    """
    Update product inventory
    """

    product = fetch_product_from_shopify(request_details)
    return {"success": "false", "message": "Not implemented"}