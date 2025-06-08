import boto3
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def send_scheduled_price_updates(updated_price_schedule, product_gid, open_variant_gid, waitlist_variant_gid, sport, day, division, season_start_date, off_dates_comma_separated):
    print("📍 Entered send_scheduled_price_updates()")

    scheduler_client = boto3.client("scheduler")

    sport_slug_map = {
        "bowling": "bowl",
        "dodgeball": "db",
        "kickball": "kb",
        "pickleball": "pb"
    }

    sport_slug = sport_slug_map.get(sport.lower(), sport.lower())
    print(f"🏷 Using sport slug: {sport_slug}")

    scheduled_updates = []
    failed_updates = []

    for i in range(4):
        try:
            timestamp = updated_price_schedule[i]["timestamp"]
            updated_price = updated_price_schedule[i]["updated_price"]

            safe_division = division.lower().replace('+', '').replace(' ', '')  # remove '+' and any spaces if needed
            schedule_name = f"adjust-prices-{sport_slug}-{day.lower()}-{safe_division}Div-week-{i+1}"
            group_name = f"adjust-prices-week-{i+1}"

            print(f"🔵 Checking existing schedule: {schedule_name} in {group_name}")

            try:
                existing_schedule = scheduler_client.get_schedule(
                    Name=schedule_name,
                    GroupName=group_name
                )
                print(f"✅ Found existing schedule: {existing_schedule}")
            except scheduler_client.exceptions.ResourceNotFoundException:
                msg = f"⚠️ Schedule {schedule_name} not found. Skipping."
                print(msg)
                failed_updates.append(msg)
                scheduled_updates.append(msg)
                continue
            except Exception as e:
                print(f"❌ Error fetching existing schedule: {e}")
                raise

            current_target = existing_schedule.get("Target", {})
            schedule_timezone = existing_schedule.get("ScheduleExpressionTimezone", "America/New_York")

            updated_input = json.dumps({
                "scheduleName": schedule_name,
                "productGid": product_gid,
                "openVariantGid": open_variant_gid,
                "waitlistVariantGid": waitlist_variant_gid,
                "updatedPrice": updated_price,
                "seasonStartDate": season_start_date,
                "offDatesCommaSeparated": off_dates_comma_separated
            })

            print(f"📤 Updating schedule {schedule_name} with timestamp {timestamp} and new price {updated_price}")

            try:
                response = scheduler_client.update_schedule(
                    Name=schedule_name,
                    GroupName=group_name,
                    ScheduleExpression=f"at({timestamp})",
                    ScheduleExpressionTimezone=schedule_timezone,
                    FlexibleTimeWindow={"Mode": "OFF"},
                    Target={**current_target, "Input": updated_input},
                    State="ENABLED"
                )
                print(f"✅ Updated schedule: {response}")

                scheduled_updates.append({
                    "name": schedule_name,
                    "group": group_name,
                    "timestamp": timestamp,
                    "price": updated_price,
                    "status": "✅ updated successfully"
                })
            except Exception as update_err:
                msg = {
                    "name": schedule_name,
                    "group": group_name,
                    "timestamp": timestamp,
                    "price": updated_price,
                    "status": f"❌ Failed to update: {str(update_err)}"
                }
                print(f"❌ Failed to update schedule: {msg}")
                failed_updates.append(msg)
                scheduled_updates.append(msg)

        except Exception as outer_err:
            msg = f"❌ Unexpected error for week {i+1}: {str(outer_err)}"
            print(msg)
            failed_updates.append(msg)
            scheduled_updates.append(msg)

    print("📋 Final Scheduled Updates:\n" + json.dumps(scheduled_updates, indent=2, default=str))
    return failed_updates