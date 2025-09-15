"""
Inventory movement scheduling logic
Handles creating EventBridge schedules for moving inventory between variants
"""

import boto3  # type: ignore
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any
from bars_common_utils.date_utils import parse_iso_datetime


def create_scheduled_inventory_movements(event_body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create an EventBridge schedule for moving inventory between variants

    Expected event_body structure:
    {
        "actionType": "create-scheduled-inventory-movements",
        "scheduleName": "auto-move-...",
        "groupName": "move-inventory-between-variants-...",
        "productUrl": "https://...",
        "sourceVariant": {
            "type": "early",
            "name": "Early Registration",
            "gid": "gid://shopify/ProductVariant/..."
        },
        "destinationVariant": {
            "type": "open",
            "name": "Open Registration",
            "gid": "gid://shopify/ProductVariant/..."
        },
        "newDatetime": "2024-01-01T10:00:00",
        "note": "...",
        "totalInventory": 64,
        "numberVetSpotsToReleaseAtGoLive": 40
    }
    """
    print("📦 Creating scheduled inventory movement")
    print(f"🔍 Event data: {json.dumps(event_body, indent=2)}")

    # Initialize EventBridge Scheduler client
    scheduler_client = boto3.client(
        "scheduler", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    )

    # Extract required fields
    schedule_name = event_body.get("scheduleName")
    group_name = event_body.get("groupName")
    new_datetime = event_body.get("newDatetime")

    if not all([schedule_name, group_name, new_datetime]):
        raise ValueError(
            "❌ Missing required parameters! Must provide scheduleName, groupName, and newDatetime."
        )

    # Validate datetime format and convert timezone
    try:
        utc_dt = parse_iso_datetime(str(new_datetime))
        eastern_dt = utc_dt.astimezone(ZoneInfo("America/New_York")) - timedelta(
            minutes=1
        )
        formatted_datetime = eastern_dt.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError as e:
        raise ValueError(f"❌ {str(e)}")

    # Extract inventory information for logging
    total_inventory = event_body.get("totalInventory")
    number_vet_spots = event_body.get("numberVetSpotsToReleaseAtGoLive")

    # Prepare the input for the MoveInventoryLambda (includes all fields from event_body)
    updated_input = json.dumps(event_body)

    print(f"🕐 Scheduling for: {formatted_datetime} (America/New_York)")
    print(f"📊 Total inventory: {total_inventory}")
    print(f"🎖️ Vet spots to release: {number_vet_spots}")

    # Create the EventBridge schedule
    response = scheduler_client.create_schedule(
        Name=schedule_name,
        GroupName=group_name,
        ScheduleExpression=f"at({formatted_datetime})",
        ScheduleExpressionTimezone="America/New_York",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": "arn:aws:lambda:us-east-1:084375563770:function:MoveInventoryLambda",
            "RoleArn": "arn:aws:iam::084375563770:role/service-role/Amazon_EventBridge_Scheduler_LAMBDA_3bc414251c",
            "Input": updated_input,
        },
        ActionAfterCompletion="DELETE",
        State="ENABLED",
        Description="",
    )

    print("✅ Created new inventory movement schedule:")
    print(json.dumps(response, indent=2, default=str))

    return {
        "message": f"✅ Schedule '{schedule_name}' created successfully!",
        "new_expression": f"at({formatted_datetime})",
        "aws_response": response,
    }
