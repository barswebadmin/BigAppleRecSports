"""
Inventory addition and title change scheduling logic
Handles creating EventBridge schedules for setting products live with inventory and title updates
"""

import boto3  # type: ignore
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any


def create_initial_inventory_addition_and_title_change(
    event_body: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create an EventBridge schedule for adding inventory and updating product title

    Expected event_body structure:
    {
        "actionType": "create-initial-inventory-addition-and-title-change",
        "scheduleName": "auto-set-productId-sportSlug-daySlug-divisionSlug-live",
        "groupName": "set-product-live",
        "productUrl": "https://09fe59-3.myshopify.com/admin/products/123456789",
        "productTitle": "New Product Title",
        "variantGid": "gid://shopify/ProductVariant/123456789",
        "newDatetime": "2024-01-01T10:00:00",
        "note": "...",
        "totalInventory": 64,
        "numberVetSpotsToReleaseAtGoLive": 40
    }

    Note: inventoryToAdd is calculated from numberVetSpotsToReleaseAtGoLive
    """
    print("🚀 Creating scheduled inventory addition and title change")
    print(f"🔍 Event data: {json.dumps(event_body, indent=2)}")

    # Initialize EventBridge Scheduler client
    scheduler_client = boto3.client(
        "scheduler", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    )

    # Extract required fields
    schedule_name = event_body.get("scheduleName")
    group_name = event_body.get("groupName")
    new_datetime = event_body.get("newDatetime")
    product_url = event_body.get("productUrl")
    product_title = event_body.get("productTitle")
    variant_gid = event_body.get("variantGid")

    # Extract inventory fields
    total_inventory = event_body.get("totalInventory")
    number_vet_spots = event_body.get("numberVetSpotsToReleaseAtGoLive")

    # Use numberVetSpotsToReleaseAtGoLive as the inventory to add
    inventory_to_add = number_vet_spots

    # Validate required fields
    required_fields = [
        "scheduleName",
        "groupName",
        "newDatetime",
        "productUrl",
        "productTitle",
        "variantGid",
        "numberVetSpotsToReleaseAtGoLive",
    ]
    missing_fields = [field for field in required_fields if not event_body.get(field)]

    if missing_fields:
        raise ValueError(f"❌ Missing required parameters: {', '.join(missing_fields)}")

    # Validate datetime format and convert timezone
    try:
        utc_dt = datetime.strptime(str(new_datetime), "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=ZoneInfo("UTC")
        )
        eastern_dt = utc_dt.astimezone(ZoneInfo("America/New_York")) - timedelta(
            minutes=1
        )
        formatted_datetime = eastern_dt.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        raise ValueError(
            f"❌ Invalid datetime format. Expected YYYY-MM-DDTHH:MM:SS, received: {new_datetime}"
        )

    # Validate inventory amount (numberVetSpotsToReleaseAtGoLive)
    if not isinstance(inventory_to_add, int) or inventory_to_add <= 0:
        raise ValueError(
            "❌ numberVetSpotsToReleaseAtGoLive must be a positive integer"
        )

    # Prepare the input for the setProductLiveByAddingInventory lambda
    lambda_input = {
        "productUrl": product_url,
        "productTitle": product_title,
        "variantGid": variant_gid,
        "inventoryToAdd": inventory_to_add,
        "totalInventory": total_inventory,
        "numberVetSpotsToReleaseAtGoLive": number_vet_spots,
    }

    updated_input = json.dumps(lambda_input)

    print(f"🕐 Scheduling for: {formatted_datetime} (America/New_York)")
    print(
        f"📦 Will add {inventory_to_add} inventory to variant {variant_gid} (using numberVetSpotsToReleaseAtGoLive)"
    )
    print(f"📝 Will update product title to: {product_title}")
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
            "Arn": "arn:aws:lambda:us-east-1:084375563770:function:setProductLiveByAddingInventory",
            "RoleArn": "arn:aws:iam::084375563770:role/service-role/Amazon_EventBridge_Scheduler_LAMBDA_3bc414251c",
            "Input": updated_input,
        },
        ActionAfterCompletion="DELETE",
        State="ENABLED",
        Description="Schedule to set product live by adding inventory and updating title",
    )

    print("✅ Created new inventory addition and title change schedule:")
    print(json.dumps(response, indent=2, default=str))

    return {
        "message": f"✅ Schedule '{schedule_name}' created successfully!",
        "new_expression": f"at({formatted_datetime})",
        "lambda_input": lambda_input,
        "aws_response": response,
    }


def create_remaining_inventory_addition_schedule(
    event_body: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create an EventBridge schedule for adding remaining inventory to live products

    This function targets the addRemainingInventoryToLiveProduct Lambda function
    instead of the setProductLiveByAddingInventory function.

    Expected event_body structure:
    {
        "actionType": "create-initial-inventory-addition-and-title-change",
        "scheduleName": "auto-add-remaining-inventory-{product_id}-{sport}-{day}-{division}",
        "groupName": "add-remaining-inventory-to-live-product",
        "productUrl": "https://09fe59-3.myshopify.com/admin/products/123456789",
        "productTitle": "Product Title",
        "variantGid": "gid://shopify/ProductVariant/123456789",
        "newDatetime": "2024-01-01T10:00:00",
        "note": "newDateTime is in UTC (ET is 4 hours earlier than what this says)",
        "totalInventory": 100,
        "numberVetSpotsToReleaseAtGoLive": 40,
        "inventoryToAdd": 60
    }
    """
    print("🚀 Creating scheduled remaining inventory addition")
    print(f"🔍 Event data: {json.dumps(event_body, indent=2)}")

    # Initialize EventBridge Scheduler client
    scheduler_client = boto3.client(
        "scheduler", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    )

    # Extract required fields
    schedule_name = event_body.get("scheduleName")
    group_name = event_body.get("groupName")
    new_datetime = event_body.get("newDatetime")
    product_url = event_body.get("productUrl")
    product_title = event_body.get("productTitle")
    variant_gid = event_body.get("variantGid")
    inventory_to_add = event_body.get("inventoryToAdd")

    # Validate required fields
    required_fields = [
        "scheduleName",
        "groupName",
        "newDatetime",
        "productUrl",
        "productTitle",
        "variantGid",
        "inventoryToAdd",
    ]

    missing_fields = [field for field in required_fields if not event_body.get(field)]
    if missing_fields:
        raise ValueError(f"❌ Missing required fields: {', '.join(missing_fields)}")

    # Parse and validate datetime
    try:
        # Parse the datetime and add 1 minute buffer
        parsed_dt = datetime.fromisoformat(new_datetime.replace("Z", "+00:00"))
        eastern_dt = parsed_dt.astimezone(ZoneInfo("America/New_York")) + timedelta(
            minutes=1
        )
        formatted_datetime = eastern_dt.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        raise ValueError(
            f"❌ Invalid datetime format. Expected YYYY-MM-DDTHH:MM:SS, received: {new_datetime}"
        )

    # Validate inventory amount
    if not isinstance(inventory_to_add, int) or inventory_to_add <= 0:
        raise ValueError("❌ inventoryToAdd must be a positive integer")

    # Prepare the input for the addRemainingInventoryToLiveProduct lambda
    lambda_input = {
        "productUrl": product_url,
        "productTitle": product_title,
        "variantGid": variant_gid,
        "inventoryToAdd": inventory_to_add,
    }

    updated_input = json.dumps(lambda_input)

    print(f"🕐 Scheduling for: {formatted_datetime} (America/New_York)")
    print(
        f"📦 Will add {inventory_to_add} remaining inventory to variant {variant_gid}"
    )
    print("🎯 Target Lambda: addRemainingInventoryToLiveProduct")

    # Create the EventBridge schedule
    response = scheduler_client.create_schedule(
        Name=schedule_name,
        GroupName=group_name,
        ScheduleExpression=f"at({formatted_datetime})",
        ScheduleExpressionTimezone="America/New_York",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": "arn:aws:lambda:us-east-1:084375563770:function:addRemainingInventoryToLiveProduct",
            "RoleArn": "arn:aws:iam::084375563770:role/service-role/Amazon_EventBridge_Scheduler_LAMBDA_3bc414251c",
            "Input": updated_input,
        },
        ActionAfterCompletion="DELETE",
        State="ENABLED",
        Description="Schedule to add remaining inventory to live product",
    )

    print("✅ Created new remaining inventory addition schedule:")
    print(json.dumps(response, indent=2, default=str))

    return {
        "message": f"✅ Remaining inventory schedule '{schedule_name}' created successfully!",
        "new_expression": f"at({formatted_datetime})",
        "lambda_input": lambda_input,
        "aws_response": response,
    }
