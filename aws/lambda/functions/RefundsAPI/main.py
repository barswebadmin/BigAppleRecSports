"""Lambda entrypoint — action dispatch + Function URL envelope.

Decorator stack (outermost → innermost)
----------------------------------------
@guard                      catches ValidationError → 400, Exception → 500
@tracer.capture_lambda_handler  X-Ray root segment; annotates cold_start
@logger.inject_lambda_context   appends request_id, cold_start to every log
@event_source               converts raw event dict → LambdaFunctionUrlEvent

Required Lambda environment variables
--------------------------------------
POWERTOOLS_SERVICE_NAME   e.g. ShopifyRefundHandler
POWERTOOLS_LOG_LEVEL      e.g. INFO
"""

import json

from aws_lambda_powertools.utilities.data_classes import LambdaFunctionUrlEvent, event_source
from handlers.handle_initial_request import run_evaluate_refund
from handlers.process_refund import handle_process_refund
from powertools.http import err, guard, ok
from powertools.observability import logger, tracer

_PROCESS_ACTIONS = frozenset({"create_refund", "cancel_order"})


@guard
@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=False)
@event_source(data_class=LambdaFunctionUrlEvent)
def lambda_handler(event: LambdaFunctionUrlEvent, context) -> dict:
    try:
        body: dict = json.loads(event.body or "{}")
    except (json.JSONDecodeError, TypeError):
        return err(400, "Malformed request body")

    action: str = body.pop("action", "evaluate_refund")
    order_number: str | None = body.get("order_number")

    logger.append_keys(action=action, order_number=order_number)
    tracer.put_annotation(key="action", value=action)

    if action == "evaluate_refund":
        return ok(run_evaluate_refund(body))
    if action in _PROCESS_ACTIONS:
        return ok(handle_process_refund({"action": action, **body}))
    return err(400, f"Unknown action: {action!r}")
