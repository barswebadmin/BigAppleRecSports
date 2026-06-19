"""HTTP response builders and the guard error-catching decorator.

    from powertools.http import ok, err, guard

    @guard
    @tracer.capture_lambda_handler
    @logger.inject_lambda_context(log_event=False)
    def lambda_handler(event, context):
        if something_bad:
            return err(400, "Bad input", detail={"field": "order_id"})
        return ok({"status": "accepted"})

guard catches ValidationError → 400 and Exception → 500, both as structured
JSON using err(). Handlers that want to return a specific HTTP status call err()
directly; guard only fires on unhandled exceptions.
"""

import json
from typing import Any

from aws_lambda_powertools.middleware_factory import lambda_handler_decorator
from pydantic import ValidationError

from powertools.observability import logger

JSON_HEADERS = {"Content-Type": "application/json"}


def ok(body: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": 200, "headers": JSON_HEADERS, "body": json.dumps(body, default=str)}


def err(status: int, message: str, detail: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": message}
    if detail is not None:
        payload["detail"] = detail
    return {"statusCode": status, "headers": JSON_HEADERS, "body": json.dumps(payload, default=str)}


@lambda_handler_decorator
def guard(handler, event, context):
    """Catch ValidationError → 400 and Exception → 500 as structured HTTP error responses."""
    try:
        return handler(event, context)
    except ValidationError as exc:
        logger.warning("Request validation failed", extra={"pydantic_errors": exc.errors()})
        return err(400, "Invalid request payload", detail=exc.errors())
    except Exception:
        logger.exception("Unhandled exception in Lambda handler")
        return err(500, "Internal error")
