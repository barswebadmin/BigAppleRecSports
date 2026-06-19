"""Handler latency metric middleware.

    from powertools.timing import timed

    @guard
    @timed
    @tracer.capture_lambda_handler
    def lambda_handler(event, context): ...

Stack timed inside guard so the metric captures real handler time and not
error-normalization overhead. The finally block ensures latency is always
emitted even when an exception is raised.
"""

import time

from aws_lambda_powertools.middleware_factory import lambda_handler_decorator

from powertools.observability import MetricUnit, emit_metric


@lambda_handler_decorator
def timed(handler, event, context):
    """Emit HandlerLatencyMs to CloudWatch after every invocation."""
    start = time.perf_counter()
    try:
        return handler(event, context)
    finally:
        emit_metric(
            "HandlerLatencyMs",
            value=(time.perf_counter() - start) * 1000,
            unit=MetricUnit.Milliseconds,
        )
