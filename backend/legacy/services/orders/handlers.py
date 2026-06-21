from typing import Any

from fastapi import Depends, Request

from services.orders import service
from services.orders.requests import CancelOrderRequest, GetOrderQuery

REASON_DISPATCH = {
    "cancel": service.validate_cancellation,
    None:     service.get_order_basic,
}


async def get_order(q: GetOrderQuery = Depends()) -> dict[str, Any]:
    return await REASON_DISPATCH[q.reason](q)


async def cancel_order(order_id: str, body: CancelOrderRequest) -> dict[str, Any]:
    return await service.cancel(order_id, body)


async def handle_webhook(req: Request) -> dict[str, Any]:
    topic = req.headers.get("x-shopify-topic", "").strip()
    return await service.process_webhook(topic, await req.body(), dict(req.headers))
