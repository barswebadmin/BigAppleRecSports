__version__ = "1.0.0"

import json
import traceback
from typing import Dict, Any

from bars_common_utils.event_utils import parse_event_body
from bars_common_utils.response_utils import format_response, format_error
import inventory_movement_scheduler as inv_sched
import price_change_scheduler as price_sched
import inventory_addition_scheduler as add_sched


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Route requests to appropriate scheduling functions based on actionType

    Supported actionTypes:
    - create-scheduled-inventory-movements: Schedule inventory moves between variants
    - create-scheduled-price-changes: Schedule price changes throughout a season
    - create-initial-inventory-addition-and-title-change: Schedule initial inventory addition and title update
    - add-inventory-to-live-product: Schedule remaining inventory addition to live product
    """
    try:
        print("🔄 ScheduleChangesForShopifyProductsLambda invoked")
        print(f"📥 Raw event: {json.dumps(event, indent=2)}")

        # Parse event body
        event_body = parse_event_body(event)
        print(f"📋 Parsed event body: {json.dumps(event_body, indent=2)}")

        # Route by action type (single-step). Orchestration can be added behind a feature flag later.
        action_type = event_body.get("actionType")
        if not action_type:
            return format_response(400, json.dumps({"message": "Missing required field: actionType"}))

        if action_type == "create-scheduled-inventory-movements":
            result = inv_sched.create_scheduled_inventory_movements(event_body)
            return format_response(201, json.dumps({"success": True, "data": result}, default=str))

        elif action_type == "create-scheduled-price-changes":
            result = price_sched.create_scheduled_price_changes(event_body)
            return format_response(200, json.dumps({"success": True, "data": result}, default=str))

        elif action_type == "create-initial-inventory-addition-and-title-change":
            # Determine which of the two inventory-addition flows to call based on groupName
            if event_body.get("groupName") == "add-remaining-inventory-to-live-product":
                result = add_sched.create_remaining_inventory_addition_schedule(event_body)
            else:
                result = add_sched.create_initial_inventory_addition_and_title_change(event_body)
            return format_response(201, json.dumps({"success": True, "data": result}, default=str))

        elif action_type == "add-inventory-to-live-product":
            result = add_sched.create_remaining_inventory_addition_schedule(event_body)
            return format_response(201, json.dumps({"success": True, "data": result}, default=str))

        else:
            return format_response(
                422,
                json.dumps(
                    {
                        "message": f"Unsupported actionType: '{action_type}'",
                        "details": {
                            "supported_action_types": [
                                "create-scheduled-inventory-movements",
                                "create-scheduled-price-changes",
                                "create-initial-inventory-addition-and-title-change",
                            ],
                            "received": action_type,
                        },
                    }
                ),
            )

    except ValueError as e:
        print(f"❌ Validation error: {str(e)}")
        return format_response(400, json.dumps({"message": str(e)}))

    except Exception as e:
        error_message = str(e)
        stack_trace = traceback.format_exc()
        print(f"❌ Unexpected error: {error_message}")
        print(stack_trace)
        return format_response(
            500,
            json.dumps(
                {
                    "message": "Internal server error",
                    "details": {"error": error_message, "traceback": stack_trace},
                }
            ),
        )
