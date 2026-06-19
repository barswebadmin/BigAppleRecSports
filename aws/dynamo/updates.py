"""DynamoDB update operations (partial mutations).

``patch_item``  — update specific fields; supports dotted paths for nested attributes.
``soft_delete`` — sets ``deleted_at``; item is retained for audit history.

Nested attribute example
------------------------
    from aws.dynamo import updates

    # Top-level field:
    updates.patch_item(TABLE, "rf-abc123", "refunds", status="completed")

    # Nested map attribute (no DynamoDB schema change needed — store as a map):
    updates.patch_item(
        TABLE, "rf-abc123", "refunds",
        **{"metadata.source": "google", "metadata.reviewed_by": "admin@bars.com"},
    )
    # → SET #metadata.#source = :metadata_source, #metadata.#reviewed_by = :metadata_reviewed_by
"""

from datetime import datetime, timezone
from typing import Any

from aws.dynamo.client import build_update_expr, log_op


def apply_update(table, item_id: str, name: str, op: str, data: dict[str, Any], **log_extras) -> None:
    """Build a SET expression, write it, and log the operation.

    Called by ``patch_item`` and ``soft_delete``. Extra keyword arguments are
    forwarded to ``log_op`` (e.g. ``fields=`` for ``patch_item``).
    """
    expr, names, values = build_update_expr(data)
    table.update_item(
        Key={"id": item_id},
        UpdateExpression=expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )
    log_op(name, op, id=item_id, **log_extras)


def patch_item(table, item_id: str, name: str, **fields: Any) -> None:
    """Patch specific fields (including dotted nested paths) on an existing item."""
    apply_update(table, item_id, name, "update", fields, fields=list(fields))


def soft_delete(table, item_id: str, name: str) -> None:
    """Set ``deleted_at`` to now; preserves item for audit history."""
    apply_update(table, item_id, name, "soft_delete", {"deleted_at": datetime.now(timezone.utc).isoformat()})
