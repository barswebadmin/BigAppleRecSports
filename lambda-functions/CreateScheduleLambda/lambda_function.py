__version__ = "1.0.0"

import boto3
import json
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
import traceback

# Initialize EventBridge Scheduler client
scheduler_client = boto3.client("scheduler")

def lambda_handler(event, context):
    """
    Update an EventBridge schedule if it exists, otherwise create a new one.
    """

    try:
        event_body = json.loads(event["body"]) if "body" in event else event

        action = event_body.get("action")
        schedule_name = event_body.get("scheduleName")
        group_name = event_body.get("groupName")

        if not all([schedule_name, group_name]):
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "❌ Missing required parameters! Must provide scheduleName, newDatetime, and groupName.",
                    "received": event_body
                }, indent=2)
            }
        
        # ✅ Branch: Special PATCH for veteran count only
        if action == "update-scheduled-inventory-move-with-num-eligible-veterans":
            num_vets = event_body.get("numEligibleVeterans")
            if num_vets is None:
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "❌ Missing numEligibleVeterans for action update-inventory-move-with-num-eligible-veterans."
                    }, indent=2)
                }

            try:
                existing_schedule = scheduler_client.get_schedule(Name=schedule_name, GroupName=group_name)
                current_target = existing_schedule.get("Target", {})
                current_input_str = current_target.get("Input", "{}")
                try:
                    current_input_json = json.loads(current_input_str)
                except json.JSONDecodeError:
                    current_input_json = {}

                current_input_json["numEligibleVeterans"] = num_vets
                updated_input_str = json.dumps(current_input_json)

                response = scheduler_client.update_schedule(
                    Name=schedule_name,
                    GroupName=group_name,
                    ScheduleExpression=existing_schedule["ScheduleExpression"],
                    ScheduleExpressionTimezone=existing_schedule.get("ScheduleExpressionTimezone", "America/New_York"),
                    FlexibleTimeWindow={"Mode": "OFF"},
                    Target={**current_target, "Input": updated_input_str},
                    State="ENABLED"
                )

                print("✅ Patched schedule Input:")
                print(json.dumps(response, indent=2, default=str))

                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": f"✅ Updated numEligibleVeterans to {num_vets} in schedule '{schedule_name}'",
                        "aws_response": response
                    }, indent=2)
                }

            except scheduler_client.exceptions.ResourceNotFoundException:
                return {
                    "statusCode": 404,
                    "body": json.dumps({
                        "error": f"❌ Schedule '{schedule_name}' not found in group '{group_name}'"
                    }, indent=2)
                }

        # ✅ Default flow: create/update based on datetime
        new_datetime = event_body.get("newDatetime")

        if not new_datetime:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "❌ Missing required newDatetime for schedule update/creation.",
                    "received": event_body
                }, indent=2)
            }
        
        try:
            utc_dt = datetime.strptime(new_datetime, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))
            eastern_dt = utc_dt.astimezone(ZoneInfo("America/New_York")) - timedelta(minutes=1)
            formatted_datetime = eastern_dt.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "❌ Invalid datetime format",
                    "expected_format": "YYYY-MM-DDTHH:MM:SS",
                    "received": new_datetime
                }, indent=2)
            }

        updated_input = json.dumps(event_body)

        print("🧪 Attempting to update EventBridge Scheduler:")
        print(json.dumps(event_body, indent=2))

        try:
            existing_schedule = scheduler_client.get_schedule(Name=schedule_name, GroupName=group_name)
            current_target = existing_schedule.get("Target", {})
            timezone = existing_schedule.get("ScheduleExpressionTimezone", "America/New_York")

            response = scheduler_client.update_schedule(
                Name=schedule_name,
                GroupName=group_name,
                ScheduleExpression=f"at({formatted_datetime})",
                ScheduleExpressionTimezone=timezone,
                FlexibleTimeWindow={"Mode": "OFF"},
                Target={**current_target, "Input": updated_input},
                State="ENABLED"
            )

            print("✅ Updated schedule:")
            print(json.dumps(response, indent=2, default=str))

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": f"✅ Schedule '{schedule_name}' updated successfully!",
                    "new_expression": f"at({formatted_datetime})",
                    "aws_response": response
                }, indent=2)
            }

        except scheduler_client.exceptions.ResourceNotFoundException:
            print("⚠️ Schedule not found. Creating new one...")

            # Provide the required `Arn` and `RoleArn`
            # lambda_arn = event_body.get("targetArn")
            # role_arn = event_body.get("roleArn")

            # if not lambda_arn or not role_arn:
            #     return {
            #         "statusCode": 400,
            #         "body": json.dumps({
            #             "error": "❌ Missing targetArn or roleArn for new schedule creation.",
            #             "required_keys": ["targetArn", "roleArn"]
            #         }, indent=2)
            #     }

            response = scheduler_client.create_schedule(
                Name=schedule_name,
                GroupName=group_name,
                ScheduleExpression=f"at({formatted_datetime})",
                ScheduleExpressionTimezone="America/New_York",
                FlexibleTimeWindow={"Mode": "OFF"},
                Target={
                    "Arn": "arn:aws:lambda:us-east-1:084375563770:function:MoveInventoryLambda",
                    "RoleArn": "arn:aws:iam::084375563770:role/service-role/Amazon_EventBridge_Scheduler_LAMBDA_3bc414251c",
                    "Input": updated_input
                },
                ActionAfterCompletion="NONE",
                State="ENABLED",
                Description=""
            )

            print("✅ Created new schedule:")
            print(json.dumps(response, indent=2, default=str))

            return {
                "statusCode": 201,
                "body": json.dumps({
                    "message": f"✅ Schedule '{schedule_name}' created successfully!",
                    "new_expression": f"at({formatted_datetime})",
                    "aws_response": response
                }, indent=2)
            }

    except Exception as e:
        print("❌ Error:", traceback.format_exc())
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "❌ Failed to update or create schedule",
                "message": str(e)
            }, indent=2)
        }