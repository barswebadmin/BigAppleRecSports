"""BARS DynamoDB access — separated by behavior.

All reads return plain Python dicts; boto3.resource handles DynamoDB type
wrappers automatically. Nested map attributes come back as plain dicts;
list attributes as plain lists.

For DynamoDB config/parameter tables, see ``powertools.parameters.make_dynamo_config``.
For idempotency persistence, see ``powertools.idempotency``.

Submodules
----------
models    Pydantic table schemas: Refund, WaitlistEntry
reads     get_item, query, process_stream (Powertools BatchProcessor)
writes    put_item, batch_write  (accepts model instances or plain dicts)
updates   patch_item, soft_delete  (flat and dotted-path nested fields)
deletes   hard_delete, batch_delete

Quick reference
---------------
    import boto3
    from boto3.dynamodb.conditions import Key
    from aws.dynamo import deletes, reads, updates, writes
    from aws.dynamo.models import Refund, WaitlistEntry

    REFUNDS   = boto3.resource("dynamodb").Table("refunds")
    WAITLISTS = boto3.resource("dynamodb").Table("waitlists")

    # Validated write via model
    item = Refund(id="rf-a1b2c3d4e5f6a7b8", email="player@bars.com", ...)
    writes.put_item(REFUNDS, item, "refunds")

    # Read
    item  = reads.get_item(REFUNDS, "rf-abc123")
    items = reads.query(REFUNDS, index="customer-index",
                        key_cond=Key("customer_id").eq(cid), scan_forward=False)

    # Update (flat or nested)
    updates.patch_item(REFUNDS, "rf-abc123", "refunds", status="completed")
    updates.patch_item(REFUNDS, "rf-abc123", "refunds", **{"metadata.source": "google"})
    updates.soft_delete(REFUNDS, "rf-abc123", "refunds")

    # Delete
    deletes.hard_delete(REFUNDS, "rf-abc123", "refunds")
    deletes.batch_delete(REFUNDS, ["rf-abc123", "rf-def456"], "refunds")

    # DynamoDB Streams
    from aws.dynamo.reads import DynamoDBRecord

    def handle_record(record: DynamoDBRecord) -> None:
        new_image = record.dynamodb.new_image

    def lambda_handler(event, context):
        return reads.process_stream(event, handle_record, context)
"""

from aws.dynamo import deletes, models, reads, updates, writes

__all__ = ["deletes", "models", "reads", "updates", "writes"]
