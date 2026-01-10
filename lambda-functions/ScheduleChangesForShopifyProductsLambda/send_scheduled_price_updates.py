import json
from aws_clients import get_scheduler_client

def send_scheduled_price_updates(action, updated_price_schedule, product_gid, open_variant_gid, waitlist_variant_gid, sport, day, division, season_start_date, off_dates_comma_separated):
    print("📍 Entered send_scheduled_price_updates()")

    # Lazily construct scheduler client (avoids boto3 import at module import time)
    scheduler_client = get_scheduler_client()

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

            safe_division = division.lower().replace('+', '').replace(' ', '')
            schedule_name = f"adjust-prices-{sport_slug}-{day.lower()}-{safe_division}Div-week-{i+1}"
            group_name = f"adjust-prices-week-{i+1}"

            updated_input = json.dumps({
                "action": action,
                "scheduleName": schedule_name,
                "productGid": product_gid,
                "openVariantGid": open_variant_gid,
                "waitlistVariantGid": waitlist_variant_gid,
                "updatedPrice": updated_price,
                "seasonStartDate": season_start_date,
                "offDatesCommaSeparated": off_dates_comma_separated
            })

            print(f"🔍 Checking or updating schedule {schedule_name} for {timestamp}")

            try:
                existing_schedule = scheduler_client.get_schedule(Name=schedule_name, GroupName=group_name)
                current_target = existing_schedule.get("Target", {})
                schedule_timezone = existing_schedule.get("ScheduleExpressionTimezone", "America/New_York")

                response = scheduler_client.update_schedule(
                    Name=schedule_name,
                    GroupName=group_name,
                    ScheduleExpression=f"at({timestamp})",
                    ScheduleExpressionTimezone=schedule_timezone,
                    FlexibleTimeWindow={"Mode": "OFF"},
                    Target={**current_target, "Input": updated_input},
                    State="ENABLED"
                )
                print(f"✅ Updated existing schedule: {schedule_name}")
                scheduled_updates.append({
                    "name": schedule_name,
                    "group": group_name,
                    "timestamp": timestamp,
                    "price": updated_price,
                    "status": "✅ updated successfully"
                })

            except scheduler_client.exceptions.ResourceNotFoundException:
                print(f"⚠️ Schedule {schedule_name} not found. Creating new one...")

                response = scheduler_client.create_schedule(
                    Name=schedule_name,
                    GroupName=group_name,
                    ScheduleExpression=f"at({timestamp})",
                    ScheduleExpressionTimezone="America/New_York",
                    FlexibleTimeWindow={"Mode": "OFF"},
                    Target={
                        "Arn": "arn:aws:lambda:us-east-1:084375563770:function:changePricesOfOpenAndWaitlistVariants",
                        "RoleArn": "arn:aws:iam::084375563770:role/service-role/Amazon_EventBridge_Scheduler_LAMBDA_3bc414251c",
                        "Input": updated_input
                    },
                    ActionAfterCompletion="NONE",
                    State="ENABLED",
                    Description=""
                )
                print(f"✅ Created new schedule: {schedule_name}")
                scheduled_updates.append({
                    "name": schedule_name,
                    "group": group_name,
                    "timestamp": timestamp,
                    "price": updated_price,
                    "status": "✅ created successfully"
                })

            except Exception as e:
                msg = {
                    "name": schedule_name,
                    "group": group_name,
                    "timestamp": timestamp,
                    "price": updated_price,
                    "status": f"❌ Failed to update or create: {str(e)}"
                }
                print(f"❌ Update/Create error: {msg}")
                failed_updates.append(msg)
                scheduled_updates.append(msg)

        except Exception as outer_err:
            msg = f"❌ Unexpected error for week {i+1}: {str(outer_err)}"
            print(msg)
            failed_updates.append(msg)
            scheduled_updates.append(msg)

    print("📋 Final Scheduled Updates:\n" + json.dumps(scheduled_updates, indent=2, default=str))
    return failed_updates