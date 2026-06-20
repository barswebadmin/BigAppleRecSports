"""Shared DynamoDB resource and low-level utilities.

The ``dynamo`` resource is a module-level singleton; boto3 reuses the
connection across warm Lambda invocations.

For config/parameter tables, see ``powertools.parameters.make_dynamo_config``.
For idempotency state, see ``powertools.idempotency``.

Behavior modules:
    reads     get_item, query, DynamoDB Stream batch processing (Powertools)
    writes    put_item, batch_write
    updates   patch_item, soft_delete  (supports dotted nested paths)
    deletes   hard_delete, batch_delete
"""

import os
from collections import deque
from typing import Any

import logging

import boto3

logger = logging.getLogger(__name__)  # stdlib logger; Lambda replaces root handler with Powertools at init

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
dynamo = boto3.resource("dynamodb", region_name=REGION)


def build_update_expr(fields: dict[str, Any]) -> tuple[str, dict, dict]:
    """Build a SET expression from a dict of field → value pairs.

    Keys may be dotted paths for nested attributes (e.g. ``"metadata.source"``).
    Every path component is #-aliased to avoid DynamoDB reserved-word collisions.
    The dot-to-underscore alias for value placeholders is computed once per key.

    Returns (UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues).

    Examples:
        # Flat:   {"status": "completed"}  →  SET #status = :status
        # Nested: {"metadata.source": "google"}  →  SET #metadata.#source = :metadata_source
    """
    parsed  = {k: (k.split("."), k.replace(".", "_")) for k in fields}
    names   = {f"#{p}": p for parts, _ in parsed.values() for p in parts}
    values  = {f":{alias}": fields[k] for k, (_, alias) in parsed.items()}
    clauses = [
        ".".join(f"#{p}" for p in parts) + f" = :{alias}"
        for parts, alias in parsed.values()
    ]
    return "SET " + ", ".join(clauses), names, values


def log_op(name: str, event: str, **kwargs) -> None:
    """Log a table operation at INFO using ``{name}.{event}`` naming."""
    logger.info(f"{name}.{event}", **kwargs)


def batch_mutate(table, items, op, name: str, event: str) -> None:
    """Execute ``op(batch, item)`` for every item via boto3 batch_writer.

    Handles 25-item chunking and unprocessed-item retries transparently.
    Called by ``writes.batch_write`` and ``deletes.batch_delete``.

    Args:
        op:    Single-expression callable ``(batch, item) → None``.
        name:  Log prefix (e.g. ``"refunds"``).
        event: Log event suffix (e.g. ``"batch_write"`` or ``"batch_delete"``).
    """
    with table.batch_writer() as batch:
        deque((op(batch, item) for item in items), maxlen=0)
    log_op(name, event, count=len(items))
