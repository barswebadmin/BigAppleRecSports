"""Lambda entrypoint — general-purpose action router.

Decorator stack (outermost → innermost)
----------------------------------------
@guard                          catches ValidationError → 400, Exception → 500
@tracer.capture_lambda_handler  X-Ray root segment; annotates cold_start
@logger.inject_lambda_context   appends request_id, cold_start to every log
@event_source                   converts raw event dict → LambdaFunctionUrlEvent

Routing
-------
Dispatches by the ``action`` key in the request body. Register handlers in
``_ROUTES`` below. Each handler receives the full parsed body and must return
a JSON-serialisable dict; ``ok()`` wraps it in a 200 Function URL response.

Required Lambda environment variables
--------------------------------------
POWERTOOLS_SERVICE_NAME   e.g. AwsRouter
POWERTOOLS_LOG_LEVEL      e.g. INFO
"""

import json

from aws_lambda_powertools.utilities.data_classes import LambdaFunctionUrlEvent, event_source
from powertools.http import err, guard, ok
from powertools.observability import logger, tracer

# ---------------------------------------------------------------------------
# Route registry  {action: handler_callable}
# ---------------------------------------------------------------------------
# Import handlers here and add entries as routes are built out.
# Example:
#   from handlers.my_handler import handle_my_action
#   _ROUTES: dict[str, callable] = {
#       "my_action": handle_my_action,
#   }
_ROUTES: dict = {}


@guard
@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=False)
@event_source(data_class=LambdaFunctionUrlEvent)
def lambda_handler(event: LambdaFunctionUrlEvent, context) -> dict:
    try:
        body: dict = json.loads(event.body or "{}")
    except (json.JSONDecodeError, TypeError):
        return err(400, "Malformed request body")

    action: str | None = body.get("action")
    if not action:
        return err(400, "Missing required field: action")

    logger.append_keys(action=action)
    tracer.put_annotation(key="action", value=action)

    handler = _ROUTES.get(action)
    if handler is None:
        return err(
            400,
            f"Unknown action: {action!r}",
            {"supported_actions": sorted(_ROUTES)},
        )

    return ok(handler(body))
