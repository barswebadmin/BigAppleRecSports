import json
import traceback
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo

from get_discount_dates_and_prices import get_discount_dates_and_prices
from send_scheduled_price_updates import send_scheduled_price_updates

def lambda_handler(event, context):
    debug_logs = []
    try:
        print("🔵 Raw event received:", json.dumps(event, indent=2))

        event_body = json.loads(event["body"]) if "body" in event else event
        print("🔵 Parsed event body:", json.dumps(event_body, indent=2))

        sport = event_body["sport"] if "sport" in event_body else None
        day = event_body["day"] if "day" in event_body else None
        division = event_body["division"] if "division" in event_body else None
        price = event_body["price"] if "price" in event_body else None
        season_start_date = event_body["seasonStartDate"] if "seasonStartDate" in event_body else None
        sport_start_time = event_body["sportStartTime"] if "sportStartTime" in event_body else None
        off_dates_comma_separated = event_body["offDatesCommaSeparated"] if "offDatesCommaSeparated" in event_body else None
        product_gid = event_body["productGid"] if "productGid" in event_body else None
        open_variant_gid = event_body["openVariantGid"] if "openVariantGid" in event_body else None
        waitlist_variant_gid = event_body["waitlistVariantGid"] if "waitlistVariantGid" in event_body else None
    
        required_fields = ["sport", "day", "division", "price", "seasonStartDate", "sportStartTime", "productGid", "openVariantGid", "waitlistVariantGid"]
        missing_fields = [f for f in required_fields if not event_body.get(f)]
        if missing_fields:
            return {
                'statusCode': 400,
                'body': json.dumps(f"Missing required parameters: {missing_fields}")
            }

        updated_price_schedule = get_discount_dates_and_prices(season_start_date, off_dates_comma_separated, sport_start_time, price)
        
        failed_updates = send_scheduled_price_updates(updated_price_schedule, product_gid, open_variant_gid, waitlist_variant_gid, sport, day, division, season_start_date, off_dates_comma_separated)
        

        if failed_updates:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "message": "⚠️ Some schedules failed to update.",
                    "errors": failed_updates
                }, indent=2)
            }

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "✅ All schedules updated successfully!"
            }, indent=2)
        }

    except Exception as e:
        error_message = str(e)
        stack_trace = traceback.format_exc()

        print("❌ Mega Catch Exception:", error_message)
        print(stack_trace)

        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": error_message,
                "traceback": stack_trace,
                "debug_logs": debug_logs
            }, indent=2)
        }
