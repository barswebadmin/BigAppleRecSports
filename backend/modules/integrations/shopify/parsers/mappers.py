from typing import Any, Dict, Optional, TypedDict, List
from ..models.orders import Order


class _OrderNode(TypedDict, total=False):
    id: str
    name: str
    email: str
    totalPriceSet: Dict[str, Any]
    totalCapturableSet: Dict[str, Any]
    customer: Dict[str, Any]
    transactions: List[Dict[str, Any]]
    refunds: List[Dict[str, Any]]
    cancelledAt: str


def map_order_node_to_order(node: Optional[_OrderNode]) -> Optional[Order]:
    if not node:
        return None
    try:
        return Order.model_validate(node)  # type: ignore[arg-type]
    except Exception:
        # For safety: strip unknown fields if Pydantic complains
        allowed = {k: node.get(k) for k in ("id", "name", "email", "totalPriceSet", "totalCapturableSet", "customer", "transactions", "refunds", "cancelledAt") if k in node}
        return Order.model_validate(allowed)  # type: ignore[arg-type]


