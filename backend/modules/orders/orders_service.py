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

    Stage 5 § 5.k.0 migration: ``ShopifyRefundService`` is gone. This
    legacy compatibility shim now invokes
    ``client.run(schema.orders.mutations.cancel, **kwargs)`` directly via
    the new ``modules.refunds.inputs.build_cancel_kwargs`` builder.
    ``ShopifyUserError`` (from ``utils.shopify_refunds``) is converted to
    the legacy ``UnprocessableError`` so existing route handlers continue
    to see the same exception type. Until callers carry an ``approved_by``
    identity, we fall back to ``"system"``.
    """
    from modules.refunds.inputs import build_cancel_kwargs
    from utils.shopify_refunds import ShopifyUserError

    cancel_kwargs = build_cancel_kwargs(
        order_id=order_id,
        approved_by="system",
        reason=body.reason,
        restock=body.restock,
        notify_customer=body.notify_customer,
    )
    try:
        payload = client.run(schema.orders.mutations.cancel, **cancel_kwargs)
        if payload.user_errors:
            raise ShopifyUserError("orderCancel", list(payload.user_errors))
        return payload.to_dict()
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
