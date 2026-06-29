# shopify_request_builders.py has been deleted - all functionality replaced by sgqlc
# Query strings are built inline (e.g., f"id:{order_id}" or f"name:#{order_number}")
from .shopify_customer_utils import ShopifyCustomerUtils

__all__ = [
    "ShopifyCustomerUtils",
]


