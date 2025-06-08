import boto3
import json
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo

# Initialize EventBridge Scheduler client
scheduler_client = boto3.client("scheduler")

def lambda_handler(event, context):
    """
    Retrieve and update an EventBridge schedule's ScheduleExpression.
    """

    try:
        # Extract event body correctly (for API Gateway requests)
        event_body = json.loads(event["body"]) if "body" in event else event

        # Extract details from the incoming event
        schedule_name = event_body.get("scheduleName")
        product_url = event_body.get("productUrl")
        source_variant_gid = event_body.get("sourceVariantGid")
        destination_variant_gid = event_body.get("destinationVariantGid")
        group_name = event_body.get("groupName")
        new_datetime = event_body.get("newDatetime")  # Expected format: "YYYY-MM-DDTHH:MM:SS"

        if not all([schedule_name, new_datetime]):
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "❌ Missing required parameters! Must provide schedule_name and new_datetime.",
                    "received": event_body
                }, indent=2)
            }

        # Validate the new datetime format
        try:
            # Parse UTC datetime string
            utc_dt = datetime.strptime(new_datetime, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))

            # Format for AWS ScheduleExpression
            eastern_dt = utc_dt.astimezone(ZoneInfo("America/New_York"))
            eastern_dt = eastern_dt - timedelta(minutes=1)

            # Format as ET-local string for AWS
            formatted_datetime = eastern_dt.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "❌ Invalid datetime format",
                    "expected_format": "YYYY-MM-DDTHH:MM:SS",
                    "received": new_datetime
                }, indent=2)
            }

        print("🧪 Attempting to update EventBridge Scheduler with:")
        print(json.dumps({
            "Name": schedule_name,
            "ScheduleExpression": f"at({formatted_datetime})",
            "sourceVariantGid": source_variant_gid,
            "destinationVariantGid": destination_variant_gid,
            "groupName": group_name
        }, indent=2))

        # Retrieve existing schedule details
        existing_schedule = scheduler_client.get_schedule(
            Name=schedule_name,
            GroupName=group_name
            )

        # Extract current configuration while keeping ScheduleExpressionTimezone unchanged
        current_target = existing_schedule.get("Target", {})
        schedule_timezone = existing_schedule.get("ScheduleExpressionTimezone", "America/New_York")

        updated_input = json.dumps({
            "scheduleName": schedule_name,
            "productUrl": product_url,
            "sourceVariantGid": source_variant_gid,
            "destinationVariantGid": destination_variant_gid
        })

        print("🧪 Sending update to EventBridge Scheduler with:")
        print(json.dumps({
            "Name": schedule_name,
            "ScheduleExpression": f"at({formatted_datetime})",
            "ScheduleExpressionTimezone": "America/New_York",
            "FlexibleTimeWindow": {"Mode": "OFF"},
            "Target": {**current_target, "Input": updated_input},
            "State": "ENABLED"
        }, indent=2))

        # Update the schedule
        response = scheduler_client.update_schedule(
            Name=schedule_name,
            GroupName=group_name,
            ScheduleExpression=f"at({formatted_datetime})",
            ScheduleExpressionTimezone="America/New_York",
            FlexibleTimeWindow={"Mode": "OFF"},
            Target={**current_target, "Input": updated_input},
            State="ENABLED"
        )
        
        print("✅ AWS response:")
        print(json.dumps(response, indent=2, default=str))

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"✅ Schedule '{schedule_name}' updated successfully!",
                "new_expression": f"at({formatted_datetime})",
                "aws_response": response
            }, indent=2)
        }

    except scheduler_client.exceptions.ResourceNotFoundException:
        return {
            "statusCode": 404,
            "body": json.dumps({
                "error": "❌ Schedule not found",
                "schedule_name": schedule_name
            }, indent=2)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "❌ Failed to update schedule",
                "message": str(e)
            }, indent=2)
        }