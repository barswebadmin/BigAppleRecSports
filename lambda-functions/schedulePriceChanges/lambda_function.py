__version__ = "1.0.0"

import json
import traceback

from bars_common_utils.event_utils import parse_event_body, validate_required_fields, get_field_safe
from bars_common_utils.response_utils import format_response, format_error
from get_discount_dates_and_prices import get_discount_dates_and_prices
from send_scheduled_price_updates import send_scheduled_price_updates

def lambda_handler(event, context):
    """
    Handle scheduling price changes for a sport season
    Testing deployment with common utils layer - 6/7/25
    """
    try:
        print("🔵 Raw event received:", json.dumps(event, indent=2))

        # Parse and validate event
        event_body = parse_event_body(event)
        print("🔵 Parsed event body:", json.dumps(event_body, indent=2))

        # Validate required fields
        required_fields = [
            "sport", "day", "division", "price", 
            "seasonStartDate", "sportStartTime", "productGid", 
            "openVariantGid", "waitlistVariantGid"
        ]
        event_body = validate_required_fields(event_body, required_fields)

        # Calculate price schedule
        updated_price_schedule = get_discount_dates_and_prices(
            season_start_date=event_body["seasonStartDate"],
            off_dates_comma_separated=get_field_safe(event_body, "offDatesCommaSeparated"),
            sport_start_time=event_body["sportStartTime"],
            price=event_body["price"]
        )
        
        # Update schedules
        failed_updates = send_scheduled_price_updates(
            updated_price_schedule=updated_price_schedule,
            product_gid=event_body["productGid"],
            open_variant_gid=event_body["openVariantGid"],
            waitlist_variant_gid=event_body["waitlistVariantGid"],
            sport=event_body["sport"],
            day=event_body["day"],
            division=event_body["division"],
            season_start_date=event_body["seasonStartDate"],
            off_dates_comma_separated=get_field_safe(event_body, "offDatesCommaSeparated")
        )

        if failed_updates:
            return format_error(
                400,
                "Some schedules failed to update",
                {"errors": failed_updates}
            )

        return format_response(200, {
            "message": "✅ All schedules updated successfully!"
        })

    except ValueError as e:
        return format_error(400, str(e))
    except Exception as e:
        error_message = str(e)
        stack_trace = traceback.format_exc()
        print("❌ Mega Catch Exception:", error_message)
        print(stack_trace)
        return format_error(500, "Lambda crashed", {
            "error": error_message,
            "traceback": stack_trace
        })
