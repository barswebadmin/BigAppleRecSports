"""Keep-warm ping short-circuit middleware.

    from powertools.warmup import skip_warmup

    @skip_warmup
    @guard
    @tracer.capture_lambda_handler
    def lambda_handler(event, context): ...

Place skip_warmup outermost so pings bypass guard, tracer, logger, and all
handler logic. Returns {"status": "warm"} immediately with a 200.

Recognized sources
    aws.events                 EventBridge scheduled keep-warm rule
    serverless-plugin-warmup   Serverless Framework warmup plugin

Add to WARMUP_SOURCES if a third keep-warm producer is introduced.
"""

from aws_lambda_powertools.middleware_factory import lambda_handler_decorator

from powertools.http import ok
from powertools.observability import logger

WARMUP_SOURCES = frozenset({
    "aws.events",
    "serverless-plugin-warmup",
})


@lambda_handler_decorator
def skip_warmup(handler, event, context):
    source = event.get("source", "")
    if source in WARMUP_SOURCES:
        logger.debug("Warm-up ping — skipping handler", extra={"source": source})
        return ok({"status": "warm"})
    return handler(event, context)
