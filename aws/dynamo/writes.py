"""DynamoDB write operations (create / overwrite).

``put_item``    — single item, full create-or-overwrite.
``batch_write`` — multiple items via ``client.batch_mutate`` (25-item chunking,
                  unprocessed-item retries handled transparently by boto3).

Both functions accept either a Pydantic model instance (``Refund``,
``WaitlistEntry``) or a plain dict. Model instances are validated on
construction; ``to_dynamo_item`` calls ``model_dump(exclude_none=True)`` to
strip None-valued optional fields before the DynamoDB write.
"""

from pydantic import BaseModel

from aws.dynamo.client import batch_mutate, log_op


def to_dynamo_item(item: BaseModel | dict) -> dict:
    """Serialize a Pydantic model or plain dict to a DynamoDB-ready dict.

    Models use ``model_dump(exclude_none=True)``; dicts are passed through.
    Called by both ``put_item`` and ``batch_write``.
    """
    return item.model_dump(exclude_none=True) if isinstance(item, BaseModel) else item


def put_item(table, item: BaseModel | dict, name: str) -> None:
    """Write a full item (create or overwrite). ``name`` is used as the log prefix."""
    data = to_dynamo_item(item)
    table.put_item(Item=data)
    log_op(name, "put", id=data.get("id"))


def batch_write(table, items: list[BaseModel | dict], name: str) -> None:
    """Write multiple items. Chunking and retries handled by boto3 batch_writer."""
    batch_mutate(
        table,
        list(map(to_dynamo_item, items)),
        lambda batch, item: batch.put_item(Item=item),
        name,
        "batch_write",
    )
