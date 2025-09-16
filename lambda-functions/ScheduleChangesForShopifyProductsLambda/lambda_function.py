__version__ = "1.0.0"

import json
import traceback
from typing import Dict, Any

from bars_common_utils.event_utils import parse_event_body
from bars_common_utils.response_utils import format_response, format_error, map_exception_to_http_status
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
    - add-inventory-to-live-product: Schedule remaining inventory addition to live product
    """
    try:
        print("🔄 ScheduleChangesForShopifyProductsLambda invoked")
        print(f"📥 Raw event: {json.dumps(event, indent=2)}")

        # Parse event body
        event_body = parse_event_body(event)
        print(f"📋 Parsed event body: {json.dumps(event_body, indent=2)}")

        # Orchestrated flow: set-live -> add-remaining (optional) -> schedule-moves -> price-changes
        # Require actionType of the orchestrated entry point
        action_type = event_body.get("actionType")
        if not action_type:
            return format_error(400, "Missing required field: actionType")

        steps = []
        # Entry can be any of the four; construct ordered steps accordingly
        # Use presence of fields/groupName to determine which functions apply
        # 1) set-live (create_initial_inventory_addition_and_title_change)
        if action_type == "create-initial-inventory-addition-and-title-change":
            steps.append(("set-live", create_initial_inventory_addition_and_title_change))
            # If group indicates remaining-inventory path call that instead
            if event_body.get("groupName") == "add-remaining-inventory-to-live-product":
                steps[-1] = ("add-remaining-inventory", create_remaining_inventory_addition_schedule)

            # 2) optional add-remaining-inventory if explicit inventoryToAdd present and not already chosen
            if (
                event_body.get("inventoryToAdd")
                and steps[-1][0] != "add-remaining-inventory"
            ):
                steps.append(("add-remaining-inventory", create_remaining_inventory_addition_schedule))

            # 3) schedule inventory moves if variants provided
            steps.append(("schedule-inventory-moves", create_scheduled_inventory_movements))
            # 4) schedule price changes
            steps.append(("schedule-price-changes", create_scheduled_price_changes))

        elif action_type == "add-inventory-to-live-product":
            steps.append(("add-remaining-inventory", create_remaining_inventory_addition_schedule))
            steps.append(("schedule-inventory-moves", create_scheduled_inventory_movements))
            steps.append(("schedule-price-changes", create_scheduled_price_changes))

        elif action_type == "create-scheduled-inventory-movements":
            steps.append(("schedule-inventory-moves", create_scheduled_inventory_movements))
            steps.append(("schedule-price-changes", create_scheduled_price_changes))

        elif action_type == "create-scheduled-price-changes":
            steps.append(("schedule-price-changes", create_scheduled_price_changes))

        else:
            return format_error(
                422,
                f"Unsupported actionType: '{action_type}'",
                {
                    "supported_action_types": [
                        "create-scheduled-inventory-movements",
                        "create-scheduled-price-changes",
                        "create-initial-inventory-addition-and-title-change",
                        "add-inventory-to-live-product",
                    ],
                    "received": action_type,
                },
            )

        results = []
        for step_name, func in steps:
            print(f"➡️ Running step: {step_name}")
            try:
                data = func(event_body)
                # Success envelope per step
                results.append({
                    "step": step_name,
                    "success": True,
                    "data": data,
                })
            except Exception as e:
                status, body = map_exception_to_http_status(e)
                body["step"] = step_name
                return format_response(status, body)

        # Final success: return the list of step results
        http_status = 200 if action_type in {"create-scheduled-inventory-movements", "create-scheduled-price-changes"} else 201
        return format_response(http_status, {
            "success": True,
            "steps": results,
        })

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
