"""Idempotency skeleton — Powertools + DynamoDB.

On the first call Powertools writes a record keyed by idempotency_key to
DynamoDB. Retries with the same key return the cached response without
re-executing the handler. Essential for refund and inventory mutations where a
duplicate invocation has real financial consequences.

Usage (in a function's main.py)
--------------------------------
    from aws_lambda_powertools.utilities.idempotency import idempotent
    from powertools.idempotency import idempotency_store, IDEMPOTENCY_CONFIG

    @idempotent(config=IDEMPOTENCY_CONFIG, persistence_store=idempotency_store)
    @guard
    @tracer.capture_lambda_handler
    def lambda_handler(event, context): ...

            # The Slack app already sends idempotency_key in the request body:
            #   refund:{order_number}:{refund_to}:{amount}
            #   cancel:{order_number}
    # IDEMPOTENCY_CONFIG extracts it via JMESPath — no handler changes needed.

Required AWS resources
-----------------------
DynamoDB table  (name from env IDEMPOTENCY_TABLE_NAME, default bars-idempotency)
    pk  = id          String
    ttl = expiration  Number  (enable TTL on this attribute)

TODO: create table, set IDEMPOTENCY_TABLE_NAME on each function that opts in.
"""

import os

from aws_lambda_powertools.utilities.idempotency import DynamoDBPersistenceLayer, IdempotencyConfig

IDEMPOTENCY_CONFIG = IdempotencyConfig(
    # powertools_json() decodes the Function URL body string before extraction.
    event_key_jmespath="powertools_json(body).idempotency_key",
    # Requests without a key pass through un-deduplicated.
    raise_on_no_idempotency_key=False,
    # Cached responses expire after 1 hour. Tune per action's retry window.
    expires_after_seconds=3_600,
)

idempotency_store = DynamoDBPersistenceLayer(
    table_name=os.environ.get("IDEMPOTENCY_TABLE_NAME", "bars-idempotency"),
)
