"""DynamoDB delete operations (permanent removal).

Prefer ``updates.soft_delete`` to preserve audit history. Use these only
when the item must be fully purged (GDPR erasure, test cleanup, etc.).

``hard_delete``  — remove one item by id.
``batch_delete`` — remove multiple items via ``client.batch_mutate``.
"""

from aws.dynamo.client import batch_mutate, log_op


def hard_delete(table, item_id: str, name: str) -> None:
    """Permanently remove one item by primary key ``id``."""
    table.delete_item(Key={"id": item_id})
    log_op(name, "hard_delete", id=item_id)


def batch_delete(table, item_ids: list[str], name: str) -> None:
    """Permanently remove multiple items. Chunking handled by boto3 batch_writer."""
    batch_mutate(
        table,
        item_ids,
        lambda batch, id_: batch.delete_item(Key={"id": id_}),
        name,
        "batch_delete",
    )
