"""ShopifyProductUpdates — consolidated Shopify product management Lambda.

Routes incoming events to one of three handlers based on the ``action`` field
(or inferred from the event's key signature when ``action`` is absent):

  phase-transition      EventBridge Scheduler → registration period changes
                        (title, tags, image, inventory transfer via DynamoDB
                        season record + YAML period config).

  update-prices         EventBridge Scheduler → bulk variant price update for
                        the open + waitlist variants of a product.

  sold-out-image-check  Shopify ``products/update`` webhook → swap the product
                        image to the sport-specific sold-out/waitlist version
                        when all registration-relevant variants reach 0 inventory.

All handlers return the standard Lambda-proxy envelope
``{statusCode, headers, body: json.dumps(...)}``.

Event routing
─────────────
Explicit (preferred):
    {"action": "phase-transition|update-prices|sold-out-image-check", ...}

Inferred from key signatures when ``action`` is absent:
    seasonId + targetPeriod  → phase-transition
    productGid + updatedPrice  → update-prices
    admin_graphql_api_id + variants  → sold-out-image-check

API-Gateway ``{body: "..."}`` wrapping is unwrapped before routing.
"""

import json
import logging
from typing import Any

from .handlers import image_swap, phase_transition, update_prices
from .responses import err

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_ACTION_FIELD = "action"
_SIGNATURES: list[tuple[set[str], str]] = [
    ({"seasonId", "targetPeriod"}, "phase-transition"),
    ({"productGid", "updatedPrice"}, "update-prices"),
    ({"admin_graphql_api_id", "variants"}, "sold-out-image-check"),
]


def _unwrap(event: Any) -> dict[str, Any]:
    """Unwrap API-Gateway ``{body: "..."}`` or return the event as-is."""
    if isinstance(event, dict) and "body" in event:
        body = event["body"]
        if isinstance(body, str):
            return json.loads(body)
        if isinstance(body, dict):
            return body
        raise ValueError(f"Unsupported body type: {type(body).__name__}")
    if isinstance(event, dict):
        return event
    raise ValueError(f"Unsupported event type: {type(event).__name__}")


def _detect_action(payload: dict[str, Any]) -> str | None:
    if _ACTION_FIELD in payload:
        return payload[_ACTION_FIELD]
    keys = set(payload)
    for required_keys, action in _SIGNATURES:
        if required_keys.issubset(keys):
            return action
    return None


def lambda_handler(raw_event: Any, _context: Any) -> dict[str, Any]:
    logger.info("invoked", extra={"event": raw_event})

    try:
        payload = _unwrap(raw_event)
    except (json.JSONDecodeError, ValueError) as exc:
        return err(400, "Could not parse request body", reason=str(exc))

    action = _detect_action(payload)

    if action == "phase-transition":
        return phase_transition.handle(payload)
    if action == "update-prices":
        return update_prices.handle(payload)
    if action == "sold-out-image-check":
        return image_swap.handle(payload)

    known = [a for _, a in _SIGNATURES]
    return err(
        400,
        "Cannot determine action from event",
        hint=f"Set 'action' to one of {known}, or include the required key signatures.",
        receivedKeys=sorted(payload.keys()),
    )
