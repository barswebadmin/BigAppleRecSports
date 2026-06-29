"""Orders domain service. Flat module-level async functions, no class."""

import logging

from pydantic import BaseModel

from core.clients import shopify
from lib.clients.shopify.generated.enums import OrderCancelReason
from lib.clients.shopify.generated.fragments import Order
from lib.clients.shopify.generated.order_cancel import OrderCancel
from lib.clients.shopify.generated.orders_get import OrdersGetOrdersNodes

logger = logging.getLogger(__name__)


async def get_order(order_id: int) -> Order:
    """Fetch a single order by numeric ID. Raises if not found."""
    result = await shopify.orders_get(query=f"id:{order_id}", first=1)
    if not result.orders.nodes:
        raise ValueError(f"Order not found: {order_id}")
    if len(result.orders.nodes) > 1:
        raise ValueError(f"Multiple orders found: {order_id}")
    return result.orders.nodes[0]


async def find_orders(order_number: int | str | None) -> list[OrdersGetOrdersNodes]:
    result = await shopify.orders_get(query=f"name:#{order_number}", first=10)
    return result.orders.nodes


async def cancel_order(
    order_id: int,
    cancel_details: "CancelOrderRequest",
) -> OrderCancel:
    return await shopify.order_cancel(
        order_id=f"gid://shopify/Order/{order_id}",
        reason=cancel_details.reason,
        restock=cancel_details.restock,
        notify_customer=cancel_details.notify,
        staff_note=f"{cancel_details.cancelled_by} + {cancel_details.notes}",
    )


def strip_order_number_prefix(order_number: str | None) -> str:
    """Strip the leading ``#`` from a Shopify order number."""
    if not order_number:
        return ""
    trimmed = order_number.strip()
    return trimmed[1:] if trimmed.startswith("#") else trimmed


class CancelOrderRequest(BaseModel):
    reason: OrderCancelReason | None = OrderCancelReason.CUSTOMER
    restock: bool = False
    notify: bool = False
    cancelled_by: str | None = ""
    notes: str | None = ""
