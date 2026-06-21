import os
from typing import Any

from box import Box
from services.orders.requests import CancelOrderRequest, GetOrderQuery
from shared.exceptions import NotFoundError, UnprocessableError
from shopify_client.shop_client import ShopifyClient, schema

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
    """Cancel a Shopify order.

    Stage 3 migration: delegates the cancel mutation to
    ``ShopifyRefundService`` (D31 / Property 8). ``ShopifyUserError`` is
    converted to the legacy ``UnprocessableError`` so existing route
    handlers continue to see the same exception type. The new service
    does not pass ``staff_note`` directly — instead the canonical service
    builds a "Slack-approved cancel (by ...)" staff note from
    ``approved_by``. Until callers carry an ``approved_by`` identity, we
    fall back to ``"system"``.
    """
    from modules.refunds.services.shopify_refund_service import (
        ShopifyRefundService,
        ShopifyUserError,
    )

    try:
        return await ShopifyRefundService(client).cancel_order(
            order_id=order_id,
            approved_by="system",
            reason=body.reason,
            restock=body.restock,
            notify_customer=body.notify_customer,
        )
    except ShopifyUserError as exc:
        raise UnprocessableError(f"Order cancel failed: {exc.errors}") from exc


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
