"""
Shopify Webhooks Router

Handles incoming Shopify webhooks for product changes (especially inventory updates)
"""

import json
import logging

from fastapi import APIRouter, Request, HTTPException

from controllers.webhooks import ShopifyWebhooksController

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/shopify", tags=["shopify-webhooks"])

_controller = ShopifyWebhooksController()

# =============================================================================
# SHOPIFY WEBHOOKS (BEGIN)
# =============================================================================

def _get_shopify_topic(headers: dict[str, str]) -> str:
    topic = (headers.get("x-shopify-topic") or "").strip()
    if not topic:
        logger.warning("SHOPIFY_WEBHOOK missing x-shopify-topic header")
        raise HTTPException(status_code=400, detail="Missing x-shopify-topic header")
    return topic


def _require_topic(*, actual: str, expected: str, kind: str) -> None:
    if actual != expected:
        logger.warning("SHOPIFY_WEBHOOK kind=%s topic_mismatch actual=%s expected=%s", kind, actual, expected)
        raise HTTPException(status_code=409, detail=f"Unexpected x-shopify-topic for {kind}: {actual}")


def _log_webhook_request(headers: dict[str, str], body: bytes, *, kind: str) -> None:
    try:
        parsed_body = json.loads(body.decode("utf-8"))
        request = {"kind": kind, "headers": headers, "body": parsed_body}

        logger.info("SHOPIFY WEBHOOK RECEIVED")
        logger.info(json.dumps(request, indent=2, ensure_ascii=False))
    except Exception:
        logger.info("SHOPIFY_WEBHOOK kind=%s headers=%s", kind, json.dumps(headers, indent=2, ensure_ascii=False, sort_keys=True))
        logger.info("SHOPIFY_WEBHOOK body_raw=%s", body.decode("utf-8", errors="replace"))


@router.post("/products-update")
async def handle_products_update(request: Request):
    headers = dict(request.headers)
    topic = _get_shopify_topic(headers)
    _require_topic(actual=topic, expected="products/update", kind="products-update")
    body = await request.body()
    _log_webhook_request(headers, body, kind="products-update")
    ok = _controller.handle_webhook_product_update(body=body, headers=headers)
    return {"ok": ok}


# =============================================================================
# SHOPIFY WEBHOOKS (END)
# =============================================================================
