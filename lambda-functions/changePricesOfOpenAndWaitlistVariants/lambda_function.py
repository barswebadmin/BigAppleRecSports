import json
import urllib.request

from validate_season_dates import validate_season_dates
from update_shopify_price import update_shopify_price

# ✅ This is the Lambda entrypoint:
def lambda_handler(event, context):
    print("📦 changePricesOfOpenAndWaitlistVariants Lambda invoked with event:")
    print(json.dumps(event, indent=2))
    
    try:
        if isinstance(event, dict) and "body" in event:
            print("1")
            try:
                print("2")
                event_body = json.loads(event["body"])
            except Exception as e:
                print(f"❌ Failed to parse event['body']: {e}")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Could not parse request body", "rawBody": event["body"]})
                }
        else:
            print("4")
            event_body = event
        
        print("5")

        schedule_name = event_body.get("scheduleName")
        product_gid = event_body.get("productGid")
        open_variant_gid = event_body.get("openVariantGid")
        waitlist_variant_gid = event_body.get("waitlistVariantGid")
        updated_price = event_body.get("updatedPrice")
        season_start_date = event_body.get("seasonStartDate")
        off_dates_comma_separated = event_body.get("offDatesCommaSeparated")

        missing_fields = [key for key in ["product_gid", "open_variant_gid", "waitlist_variant_gid", "updated_price", "season_start_date"]
                          if not locals().get(key)]

        if missing_fields:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "❌ Missing required fields",
                    "missingFields": missing_fields
                })
            }

        # 💡 Run and log validation result
        validation_result = validate_season_dates(product_gid, season_start_date, off_dates_comma_separated)
        if not validation_result["match"]:
            print(json.dumps({
                "statusCode": 406,
                "body": json.dumps({
                    "error": "❌ Season dates mismatch",
                    "details": validation_result
                })
            }))
            return {
                "statusCode": 406,
                "body": json.dumps({
                    "error": "❌ Season dates mismatch",
                    "details": validation_result
                })
            }

        # 💡 Run and log update
        try:
            updated = update_shopify_price(product_gid, open_variant_gid, waitlist_variant_gid, updated_price)
            print(json.dumps({
                "statusCode": 200,
                "body": json.dumps({
                    "message": "✅ Price update successful!",
                    "updatedVariants": updated,
                    "validatedAgainst": validation_result
                })
            }))
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "✅ Price update successful!",
                    "updatedVariants": updated,
                    "validatedAgainst": validation_result
                })
            }
        except Exception as e:
            print(json.dumps({
                "statusCode": 502,
                "body": json.dumps({
                    "error": "❌ Price update failed",
                    "reason": str(e)
                })
            }))
            return {
                "statusCode": 502,
                "body": json.dumps({
                    "error": "❌ Price update failed",
                    "reason": str(e)
                })
            }

    except Exception as e:
        print(json.dumps({
            "statusCode": 500,
            "body": json.dumps({
                "error": "❌ Lambda crashed",
                "message": str(e)
            })
        }))
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "❌ Lambda crashed",
                "message": str(e)
            })
        }