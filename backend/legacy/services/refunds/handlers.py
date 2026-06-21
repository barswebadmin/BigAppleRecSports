from typing import Any

from fastapi import Request

from services.refunds import service


async def handle_webhook(req: Request) -> dict[str, Any]:
    """Pull `x-shopify-topic` + raw body off the request and dispatch.
    `service.process_webhook` raises `UnprocessableError` on unknown topics."""
    topic = req.headers.get("x-shopify-topic", "").strip()
    return await service.process_webhook(topic, await req.body(), dict(req.headers))
