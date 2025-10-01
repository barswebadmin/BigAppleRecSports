from typing import Any, Dict, Optional
from models.shopify.orders import Order


def map_order_node_to_order(node: Optional[Dict[str, Any]]) -> Optional[Order]:
    if not node:
        return None
    try:
        return Order(**node)
    except Exception:
        allowed_keys = {"id", "name", "totalPriceSet", "customer", "transactions", "refunds", "cancelledAt"}
        cleaned = {k: v for k, v in node.items() if k in allowed_keys}
        return Order(**cleaned)


