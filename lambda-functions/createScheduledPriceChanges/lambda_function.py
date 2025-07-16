__version__ = "1.0.0"

import boto3
import json
import traceback
import os

from bars_common_utils.event_utils import parse_event_body, validate_required_fields, get_field_safe
from bars_common_utils.response_utils import format_response, format_error
from bars_common_utils.scheduler_utils import create_schedule_target

def lambda_handler(event, context):
    """Create a new scheduled price change"""
    scheduler = boto3.client('scheduler', region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    print("🔵 Raw event received:", json.dumps(event, indent=2))

    try:
        # Parse and validate event
        event_body = parse_event_body(event)
        required_fields = ["scheduleName", "groupName"]
        event_body = validate_required_fields(event_body, required_fields)
        
        # Extract fields with defaults
        schedule_name = event_body["scheduleName"]
        group_name = event_body["groupName"]
        schedule_time = get_field_safe(event_body, "scheduleTime", "2025-06-02T12:00:00")
        timezone = get_field_safe(event_body, "timezone", "America/New_York")
        
        # Create target configuration
        target = create_schedule_target(
            function_arn="arn:aws:lambda:us-east-1:084375563770:function:changePricesOfOpenAndWaitlistVariants",
            role_arn="arn:aws:iam::084375563770:role/service-role/Amazon_EventBridge_Scheduler_LAMBDA_3bc414251c",
            input_data=event_body,
            description="Created by createScheduledPriceChanges Lambda"
        )

        # Create schedule
        response = scheduler.create_schedule(
            Name=schedule_name,
            GroupName=group_name,
            ScheduleExpression=f"at({schedule_time})",
            ScheduleExpressionTimezone=timezone,
            FlexibleTimeWindow={ "Mode": "OFF" },
            Target=target,
            ActionAfterCompletion="NONE"
        )
        
        return format_response(200, {
            "message": "✅ Schedule created successfully",
            "scheduleArn": response["ScheduleArn"]
        })

    except ValueError as e:
        return format_error(400, str(e))
    except scheduler.exceptions.ConflictException:
        return format_error(400, "Schedule with this name already exists")
    except Exception as e:
        return format_error(500, "Failed to create schedule", str(e))