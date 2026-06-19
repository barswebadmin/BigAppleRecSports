"""BARS convenience wrappers around aws-lambda-powertools v3.

Submodules
----------
observability   Logger + Tracer + Metrics singletons
http            ok/err response builders + @guard decorator
timing          @timed latency metric decorator
warmup          @skip_warmup keep-alive ping short-circuit
idempotency     DynamoDB persistence store + IDEMPOTENCY_CONFIG
feature_flags   AppConfig-backed FeatureFlags factory
parameters      SSM Parameter Store helpers (/bars/{env}/ convention)

All submodules depend on the official Powertools layer being present in the
Lambda runtime. Do NOT bundle aws-lambda-powertools as a pip dep — add the
official layer ARN instead.

Required Lambda environment variables
--------------------------------------
POWERTOOLS_SERVICE_NAME   e.g. ShopifyRefundHandler  (Logger + Tracer)
POWERTOOLS_LOG_LEVEL      e.g. INFO                  (Logger, default INFO)
BARS_ENV                  prod | staging | dev        (parameters path prefix)
"""
