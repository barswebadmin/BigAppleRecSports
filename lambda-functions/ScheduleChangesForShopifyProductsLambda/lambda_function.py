__version__ = "1.0.0"

import json
import traceback
from typing import Dict, Any

from bars_common_utils.event_utils import parse_event_body
from bars_common_utils.response_utils import format_response, format_error
from inventory_movement_scheduler import create_scheduled_inventory_movements
from price_change_scheduler import create_scheduled_price_changes
from inventory_addition_scheduler import (
    create_initial_inventory_addition_and_title_change,
    create_remaining_inventory_addition_schedule,
)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Route requests to appropriate scheduling functions based on actionType

    Supported actionTypes:
    - create-scheduled-inventory-movements: Schedule inventory moves between variants
    - create-scheduled-price-changes: Schedule price changes throughout a season
    - create-initial-inventory-addition-and-title-change: Schedule initial inventory addition and title update
    """
    try:
        print("🔄 ScheduleChangesForShopifyProductsLambda invoked")
        print(f"📥 Raw event: {json.dumps(event, indent=2)}")

        # Parse event body
        event_body = parse_event_body(event)
        print(f"📋 Parsed event body: {json.dumps(event_body, indent=2)}")

        # Get action type
        action_type = event_body.get("actionType")
        if not action_type:
            return format_error(400, "❌ Missing required field: actionType")

        # Route to appropriate handler based on action type
        if action_type == "create-scheduled-inventory-movements":
            result = create_scheduled_inventory_movements(event_body)
            return format_response(201, result)

        elif action_type == "create-scheduled-price-changes":
            result = create_scheduled_price_changes(event_body)
            return format_response(200, result)

        elif action_type == "create-initial-inventory-addition-and-title-change":
            # Check groupName to determine which Lambda function to target
            group_name = event_body.get("groupName")
            if group_name == "add-remaining-inventory-to-live-product":
                result = create_remaining_inventory_addition_schedule(event_body)
                return format_response(201, result)
            else:
                result = create_initial_inventory_addition_and_title_change(event_body)
                return format_response(201, result)

        else:
            # Return 422 Unprocessable Entity for unsupported action types
            return format_error(
                422,
                f"❌ Unsupported actionType: '{action_type}'",
                {
                    "supported_action_types": [
                        "create-scheduled-inventory-movements",
                        "create-scheduled-price-changes",
                        "create-initial-inventory-addition-and-title-change",
                    ],
                    "received": action_type,
                },
            )

    except ValueError as e:
        print(f"❌ Validation error: {str(e)}")
        return format_error(400, str(e))

    except Exception as e:
        error_message = str(e)
        stack_trace = traceback.format_exc()
        print(f"❌ Unexpected error: {error_message}")
        print(stack_trace)
        return format_error(
            500,
            "❌ Internal server error",
            {"error": error_message, "traceback": stack_trace},
        )
