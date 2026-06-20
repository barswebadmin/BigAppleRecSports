"""DynamoDB read operations.

Covers point lookups, index queries, and DynamoDB Stream batch processing
via the Powertools BatchProcessor (partial failure checkpointing).

Stream usage
------------
    from aws.dynamo import reads
    from aws.dynamo.reads import DynamoDBRecord

    def handle_record(record: DynamoDBRecord) -> None:
        new = record.dynamodb.new_image   # nested attributes come back as plain dicts/lists
        old = record.dynamodb.old_image

    def lambda_handler(event, context):
        return reads.process_stream(event, handle_record, context)

    # process_stream logs batch size before and succeeded/failed counts after.
    # Failed records are checkpointed back to the stream for retry only.
"""

from typing import Any

from aws_lambda_powertools.utilities.batch import BatchProcessor, EventType, process_partial_response  # pyright: ignore[reportMissingImports]
from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import DynamoDBRecord  # noqa: F401 — re-exported  # pyright: ignore[reportMissingImports]
from boto3.dynamodb.conditions import Attr

from aws.dynamo.client import log_op

STREAM_PROCESSOR = BatchProcessor(event_type=EventType.DynamoDBStreams)


def get_item(table, item_id: str) -> dict | None:
    """Fetch one item by primary key ``id``. Returns None if not found."""
    return table.get_item(Key={"id": item_id}).get("Item")


def query(
    table,
    *,
    index: str,
    key_cond: Any,
    scan_forward: bool = True,
    limit: int | None = None,
    include_deleted: bool = False,
) -> list[dict]:
    """Query a GSI and return matching items.

    Args:
        table:           boto3 Table resource.
        index:           GSI name, e.g. ``"customer-index"``.
        key_cond:        boto3 KeyConditionExpression.
        scan_forward:    True = ascending SK; False = descending (newest first).
        limit:           Max items returned. Omit for all matches.
        include_deleted: When False (default), soft-deleted items are excluded.

    Example:
        from boto3.dynamodb.conditions import Key
        from aws.dynamo import reads

        items = reads.query(
            TABLE,
            index="customer-index",
            key_cond=Key("customer_id").eq(customer_id),
            scan_forward=False,
            limit=50,
        )
    """
    return table.query(
        IndexName=index,
        KeyConditionExpression=key_cond,
        ScanIndexForward=scan_forward,
        **({"FilterExpression": Attr("deleted_at").not_exists()} if not include_deleted else {}),
        **({"Limit": limit} if limit is not None else {}),
    )["Items"]


def process_stream(event: dict, record_handler, context) -> dict:
    """Process a DynamoDB Stream batch with Powertools partial-failure support.

    Logs batch size before processing and succeeded/failed counts after.
    Failed records are checkpointed back to the stream; successful records are
    not reprocessed on the next invocation.

    The ``record_handler`` receives a typed ``DynamoDBRecord``; import it via:
        from aws.dynamo.reads import DynamoDBRecord
    """
    count = len(event.get("Records", []))
    log_op("dynamo.stream", "batch_start", count=count)
    result = process_partial_response(
        event=event,
        record_handler=record_handler,
        processor=STREAM_PROCESSOR,
        context=context,
    )
    failed = len(result.get("batchItemFailures", []))
    log_op("dynamo.stream", "batch_end", total=count, failed=failed, succeeded=count - failed)
    return result
