"""Singleton Logger, Tracer, and Metrics for BARS Lambda functions.

All three read their configuration from environment variables so this module
is the same across every function — no function-specific wiring needed here.

Environment variables
---------------------
POWERTOOLS_SERVICE_NAME   Required. Identifies the service in logs/traces.
POWERTOOLS_LOG_LEVEL      Optional. DEBUG | INFO | WARNING | ERROR (default INFO).
POWERTOOLS_METRICS_NAMESPACE  Optional. CloudWatch namespace (default BARS).

Usage
-----
    from powertools.observability import logger, tracer, metrics

    @tracer.capture_lambda_handler          # root X-Ray segment for each invocation
    @logger.inject_lambda_context(log_event=False)  # adds request_id, cold_start, etc.
    def lambda_handler(event, context):
        logger.info("Handling request", action=action)
        tracer.put_annotation(key="action", value=action)
        ...

    @tracer.capture_method                  # subsegment around any inner function
    def call_shopify():
        ...

    # CloudWatch EMF metric (flushed automatically at handler return)
    metrics.add_metric(name="RefundEvaluated", unit=MetricUnit.Count, value=1)
    metrics.add_dimension(name="action", value="evaluate_refund")
"""

import os

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit  # re-export for callers

logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace=os.environ.get("POWERTOOLS_METRICS_NAMESPACE", "BARS"))


def emit_metric(
    name: str,
    *,
    value: float = 1,
    unit: MetricUnit = MetricUnit.Count,
    dimension_name: str | None = None,
    dimension_value: str | None = None,
) -> None:
    """Emit a single CloudWatch EMF metric, optionally with one extra dimension.

    The Metrics singleton accumulates metrics and flushes them to CloudWatch
    at the end of the handler invocation (when using @metrics.log_metrics) or
    when metrics.flush_metrics() is called explicitly.

    Example
    -------
        emit_metric("RefundEvaluated")
        emit_metric("ShopifyLatencyMs", value=250, unit=MetricUnit.Milliseconds)
        emit_metric("RefundApproved", dimension_name="action", dimension_value="create_refund")
    """
    if dimension_name and dimension_value:
        metrics.add_dimension(name=dimension_name, value=dimension_value)
    metrics.add_metric(name=name, unit=unit, value=value)
