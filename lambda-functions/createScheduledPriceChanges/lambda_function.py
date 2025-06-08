import boto3
import datetime
import json

def lambda_handler(event, context):
    # joe test 6.7.25 - testing GitHub deployment - take 3 with debug
    scheduler = boto3.client('scheduler')
    print("🔵 Raw event received:", json.dumps(event, indent=2))

    event_body = json.loads(event["body"]) if "body" in event else event
    print("🔵 Parsed event body:", json.dumps(event_body, indent=2))

    schedule_name = event_body["scheduleName"] if "scheduleName" in event_body else NONE
    group_name = event_body["groupName"] if "groupName" in event_body else None
    schedule_time = "2025-06-02T12:00:00"  # ISO 8601
    timezone = "America/New_York"

    try:
        response = scheduler.create_schedule(
            Name=schedule_name,
            GroupName=group_name,
            ScheduleExpression=f"at({schedule_time})",
            ScheduleExpressionTimezone=timezone,
            FlexibleTimeWindow={ "Mode": "OFF" },
            Target={
                "Arn": "arn:aws:lambda:us-east-1:084375563770:function:changePricesOfOpenAndWaitlistVariants",
                "RoleArn": "arn:aws:iam::084375563770:role/service-role/Amazon_EventBridge_Scheduler_LAMBDA_3bc414251c",
                "Input": "{}"
            },
            ActionAfterCompletion="NONE",
            Description="Created by Lambda"
        )
        return {
            "statusCode": 200,
            "body": f"✅ Schedule created: {response['ScheduleArn']}"
        }

    except scheduler.exceptions.ConflictException:
        return {
            "statusCode": 400,
            "body": "❌ Schedule with this name already exists."
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": f"❌ Failed to create schedule: {str(e)}"
        }