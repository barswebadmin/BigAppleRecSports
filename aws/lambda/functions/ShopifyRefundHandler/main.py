"""Lambda entrypoint — translate API Gateway / direct-invoke events into a
``RefundRequest`` and dispatch to ``handler.handle_refund_request``.

Accepts two event shapes:
  - **Direct invoke**: ``event`` is the refund request JSON itself.
  - **API Gateway proxy**: ``event["body"]`` is the JSON string; we parse it.

Returns an API-Gateway-friendly response (``statusCode``, ``body`` as JSON
string) when invoked via gateway, or the bare result dict for direct invokes.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from handler import RefundRequest, handle_refund_request
from slack_sink import maybe_post_to_slack

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _extract_payload(event: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Return ``(payload, is_api_gateway)``. ``is_api_gateway`` tells the
    caller how to format the response."""
    if "body" in event and isinstance(event.get("body"), str):
        return json.loads(event["body"]), True
    return event, False


def _ok(body: dict[str, Any], api_gateway: bool) -> Any:
    if not api_gateway:
        return body
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }


def _err(status: int, message: str, api_gateway: bool, detail: Any = None) -> Any:
    body = {"error": message, "detail": detail}
    if not api_gateway:
        return body
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }


def lambda_handler(event: dict[str, Any], _context: Any) -> Any:
    payload, is_api_gateway = _extract_payload(event)

    try:
        req = RefundRequest.model_validate(payload)
    except ValidationError as e:
        logger.warning("Invalid refund request payload: %s", e)
        return _err(400, "Invalid request payload", is_api_gateway, detail=e.errors())
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Could not parse refund request: %s", e)
        return _err(400, "Malformed request", is_api_gateway, detail=str(e))

    logger.info(
        "Processing refund request: order=%s email=%s",
        req.order_number, req.email_address,
    )

    try:
        result = handle_refund_request(req)
    except Exception as e:  # noqa: BLE001 — top-level safety net for the lambda
        logger.exception("Refund request handling failed")
        return _err(500, "Internal error", is_api_gateway, detail=str(e))

    payload = result.to_json()

    # Fire-and-log POST to the Slack Deno app with the same payload we return
    # to the HTTP caller. Slack delivery failures don't affect the HTTP
    # response — they only log at WARNING.
    maybe_post_to_slack(payload)

    return _ok(payload, is_api_gateway)
