import os
from typing import Any

from box import Box
from shopify_client.shop_client import ShopifyClient, schema

from services.orders.requests import CancelOrderRequest, GetOrderQuery
from shared.exceptions import NotFoundError, UnprocessableError

client = ShopifyClient(
    store_id=os.environ.get("SHOPIFY__STORE_ID", ""),
    api_version=os.environ.get("SHOPIFY__API_VERSION", "2026-07"),
    token=os.environ.get("SHOPIFY__TOKEN__ADMIN", ""),
)


async def fetch_order(q: GetOrderQuery) -> Box:
    """Fetch a single order by GID or 5-digit number. Raises NotFoundError if absent."""
    if q.id:
        order = client.run(schema.orders.queries.by_id, id=q.id)
    else:
        matches = client.run(schema.orders.queries.by_name, name=f"#{q.number}")
        order = matches[0] if matches else None
    if order is None:
        raise NotFoundError(f"Order not found: number={q.number} id={q.id}")
    return order


async def get_order_basic(q: GetOrderQuery) -> dict[str, Any]:
    order = await fetch_order(q)
    return order.to_dict()


async def validate_cancellation(q: GetOrderQuery) -> dict[str, Any]:
    order = await fetch_order(q)
    return {
        "order": order.to_dict(),
        "cancellable": order.cancelled_at is None,
        "reason_if_not": "Already cancelled" if order.cancelled_at else None,
    }


async def cancel(order_id: str, body: CancelOrderRequest) -> dict[str, Any]:
    payload = client.run(
        schema.orders.mutations.cancel,
        order_id=order_id,
        reason=body.reason,
        restock=body.restock,
        notify_customer=body.notify_customer,
        staff_note=body.staff_note,
    )
    if payload.user_errors:
        raise UnprocessableError(f"Order cancel failed: {list(payload.user_errors)}")
    return payload.to_dict()


ACCEPTED_WEBHOOK_TOPICS = frozenset({
    "orders/create",
    "orders/updated",
    "orders/cancelled",
})


async def process_webhook(topic: str, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
    """Acknowledge a Shopify orders webhook. Per-topic side effects (Slack
    notify, DB write) land when those integrations exist in lib/ — at that
    point this becomes a dispatch on topic."""
    if topic not in ACCEPTED_WEBHOOK_TOPICS:
        raise UnprocessableError(f"Unsupported topic: {topic!r}")
    return {"ok": True, "topic": topic, "bytes": len(body)}
