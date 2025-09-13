from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
import logging
from datetime import datetime, timezone
import dateutil.parser
from services.orders import OrdersService
from services.slack import SlackService
from models.requests import RefundSlackNotificationRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/refunds", tags=["refunds"])

orders_service = OrdersService()
slack_service = SlackService()


@router.post("/send-to-slack")
async def send_refund_to_slack(
    request: RefundSlackNotificationRequest,
    slackChannelName: str = Query(
        None, description="Optional slack channel name to override default"
    ),
    mentionStrategy: str = Query(
        None, description="Optional mention strategy: 'sportAliases' or 'user|{name}'"
    ),
) -> Dict[str, Any]:
    """
    Validate order and email, then send refund request to Slack
    This endpoint validates the email matches the order's customer email,
    fetches and caches the full order details, then sends to Slack
    """
    try:
        logger.info("🚀 === REFUND REQUEST START ===")
        logger.info("📦 Incoming request data:")
        logger.info(f"   Order Number: {request.order_number}")
        logger.info(f"   Requestor Email: {request.requestor_email}")
        logger.info(f"   Requestor Name: {request.requestor_name}")
        logger.info(f"   Refund Type: {request.refund_type}")
        logger.info(f"   Notes: {request.notes}")
        logger.info(f"   Sheet Link: {request.sheet_link}")
        logger.info(f"   Request Submitted At: {request.request_submitted_at}")

        # Step 0: Parse and format request submission timestamp early
        from utils.date_utils import format_date_and_time

        if request.request_submitted_at:
            try:
                request_submitted_datetime = dateutil.parser.parse(
                    request.request_submitted_at
                )
                request_initiated_at = format_date_and_time(request_submitted_datetime)
                logger.info(
                    f"✅ Using provided submission timestamp: {request_initiated_at}"
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Failed to parse submission timestamp '{request.request_submitted_at}': {e}"
                )
                request_submitted_datetime = datetime.now(timezone.utc)
                request_initiated_at = format_date_and_time(request_submitted_datetime)
                logger.info(
                    f"📅 Using fallback submission timestamp: {request_initiated_at}"
                )
        else:
            request_submitted_datetime = datetime.now(timezone.utc)
            request_initiated_at = format_date_and_time(request_submitted_datetime)
            logger.info(
                f"📅 Using current time as submission timestamp: {request_initiated_at}"
            )

        logger.info(
            f"🔍 Processing refund Slack notification for order {request.order_number}"
        )

        # Add simple flow tracking
        logger.info("🏁 FLOW: Starting refund processing workflow")

        # Step 1: Fetch order details and validate email
        logger.info(
            f"🔎 Step 1: Fetching order details for order: {request.order_number}"
        )
        order_result = orders_service.fetch_order_details_by_email_or_order_name(
            order_name=request.order_number
        )
        logger.info(
            f"📊 Order fetch result success: {order_result.get('success', 'Unknown')}"
        )
        if not order_result.get("success"):
            logger.info(
                f"📊 Order fetch result message: {order_result.get('message', 'No message')}"
            )
        else:
            logger.info(
                f"📊 Order fetch successful - order data keys: {list(order_result.get('data', {}).keys())}"
            )

        if not order_result["success"]:
            error_type = order_result.get("error_type", "order_not_found")
            error_message = order_result.get("message", "Unknown error")

            logger.error(
                f"❌ Order lookup failed for {request.order_number}: {error_message} (type: {error_type})"
            )

            # Handle different error types
            if error_type in ["connection_error", "api_error"]:
                # Connection/API errors - log and return error to GAS, don't email customer
                logger.error(
                    "🚨 Shopify connection/API error - not sending customer email"
                )
                print(f"🚨 Shopify connection error: {error_message}")

                raise HTTPException(
                    status_code=503,  # Service Unavailable
                    detail={
                        "error": "shopify_connection_error",
                        "message": "Unable to connect to Shopify. Please try again later.",
                        "user_message": "There was a technical issue connecting to our system. Please try submitting your refund request again in a few minutes.",
                    },
                )
            else:
                # Legitimate "order not found" - send notification to Slack (which emails customer)
                logger.info("📤 Sending 'order not found' notification to Slack")
                requestor_info = {
                    "name": request.requestor_name,
                    "email": request.requestor_email,
                    "refund_type": request.refund_type,
                    "notes": request.notes,
                }

                try:
                    slack_result = slack_service.send_refund_request_notification(
                        requestor_info=requestor_info,
                        sheet_link=request.sheet_link or "",
                        error_type="order_not_found",
                        raw_order_number=request.order_number,
                        request_initiated_at=request_initiated_at,
                        slack_channel_name=slackChannelName,
                        mention_strategy=mentionStrategy,
                    )
                    logger.info(
                        f"✅ Slack notification sent successfully: {slack_result.get('success', 'Unknown status')}"
                    )
                except Exception as slack_error:
                    logger.error(
                        f"❌ Failed to send Slack notification: {str(slack_error)}"
                    )
                    logger.error(f"❌ Slack error type: {type(slack_error).__name__}")

                logger.info("🚫 Raising 406 HTTPException for order not found")
                raise HTTPException(
                    status_code=406,
                    detail=f"Order {request.order_number} not found in Shopify",
                )

        # Step 2: Extract order data
        logger.info("🏁 FLOW: Step 2 - Extracting order data and validating email")
        order_data = order_result[
            "data"
        ]  # Changed from order_result["order"] to order_result["data"]
        order_customer_email = order_data.get("customer", {}).get("email", "").lower()
        provided_email = request.requestor_email.lower()
        logger.info(
            f"📧 Email validation: order={order_customer_email}, provided={provided_email}"
        )

        if order_customer_email != provided_email:
            logger.error(
                f"Email mismatch for order {request.order_number}: {order_customer_email} != {provided_email}"
            )

            # Send email mismatch error to Slack
            requestor_info = {
                "name": request.requestor_name,
                "email": request.requestor_email,
                "refund_type": request.refund_type,
                "notes": request.notes,
            }

            slack_result = slack_service.send_refund_request_notification(
                order_data={"order": order_data},
                requestor_info=requestor_info,
                sheet_link=request.sheet_link or "",
                error_type="email_mismatch",
                raw_order_number=request.order_number,
                order_customer_email=order_customer_email,
                slack_channel_name=slackChannelName,
                mention_strategy=mentionStrategy,
            )

            raise HTTPException(
                status_code=409,
                detail=f"Email {request.requestor_email} does not match order customer email",
            )

        # Step 3: Check for existing refunds (duplicate detection)
        logger.info(
            "🏁 FLOW: Step 3 - Checking for existing refunds (DUPLICATE DETECTION)"
        )
        logger.info(
            f"🔎 Step 3: Checking for existing refunds on order: {order_data['id']}"
        )
        existing_refunds_result = orders_service.check_existing_refunds(
            order_data["id"]
        )
        logger.info(
            f"📋 Duplicate check completed: {existing_refunds_result.get('success')}"
        )

        if existing_refunds_result.get("success") and existing_refunds_result.get(
            "has_refunds"
        ):
            logger.warning(
                f"⚠️ Duplicate refund detected for order {request.order_number}"
            )
            logger.info(
                f"📊 Existing refunds: {existing_refunds_result.get('total_refunds', 0)} found"
            )

            # Send duplicate refund error to Slack
            requestor_info = {
                "name": request.requestor_name,
                "email": request.requestor_email,
                "refund_type": request.refund_type,
                "notes": request.notes,
            }

            try:
                slack_result = slack_service.send_refund_request_notification(
                    order_data={"order": order_data},
                    requestor_info=requestor_info,
                    sheet_link=request.sheet_link or "",
                    error_type="duplicate_refund",
                    raw_order_number=request.order_number,
                    existing_refunds_data=existing_refunds_result,
                    slack_channel_name=slackChannelName,
                    mention_strategy=mentionStrategy,
                )
                logger.info(
                    f"✅ Slack duplicate refund notification sent successfully: {slack_result.get('success', 'Unknown status')}"
                )
            except Exception as slack_error:
                logger.error(
                    f"❌ Failed to send Slack duplicate refund notification: {str(slack_error)}"
                )
                logger.error(f"❌ Slack error type: {type(slack_error).__name__}")

            logger.info("🚫 Raising 409 HTTPException for duplicate refund")
            raise HTTPException(
                status_code=409,
                detail=f"Order {request.order_number} already has {existing_refunds_result.get('total_refunds', 0)} refund(s) processed",
            )

        # Step 4: Calculate refund information (this caches the calculation)
        refund_calculation = orders_service.calculate_refund_due(
            order_data, request.refund_type, request_submitted_datetime
        )

        # Step 5.5: Fetch customer data for profile linking
        logger.info(
            f"🔍 Step 5.5: Fetching customer data for email: {request.requestor_email}"
        )
        customer_result = orders_service.shopify_service.get_customer_by_email(
            request.requestor_email
        )
        customer_data = (
            customer_result.get("customer") if customer_result.get("success") else None
        )
        if customer_data:
            logger.info(
                f"✅ Customer found: {customer_data.get('firstName', '')} {customer_data.get('lastName', '')}"
            )
        else:
            logger.info(f"📭 No customer found for email: {request.requestor_email}")

        # Step 6: Prepare requestor info for Slack
        requestor_info = {
            "name": request.requestor_name,
            "email": request.requestor_email,
            "refund_type": request.refund_type,
            "notes": request.notes,
            "customer_data": customer_data,  # Include customer data for profile linking
        }

        # Step 7: Send notification to Slack (handles both success and fallback cases)
        slack_result = slack_service.send_refund_request_notification(
            order_data={"order": order_data},
            refund_calculation=refund_calculation,
            requestor_info=requestor_info,
            sheet_link=request.sheet_link or "",
            request_initiated_at=request_initiated_at,
            slack_channel_name=slackChannelName,
            mention_strategy=mentionStrategy,
        )

        if not slack_result["success"]:
            error_message = slack_result.get(
                "error", slack_result.get("message", "Unknown error")
            )
            logger.error(f"❌ Failed to send Slack notification: {error_message}")
            logger.error(f"📊 Full Slack result: {slack_result}")

            # Return 500 error with detailed Slack error information
            # This properly indicates a server failure while providing debugging details
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "slack_notification_failed",
                    "message": f"Order found but Slack notification failed: {error_message}",
                    "order_data": {
                        "order_number": request.order_number,
                        "requestor_email": request.requestor_email,
                        "refund_type": request.refund_type,
                        "refund_amount": refund_calculation.get("refund_amount", 0),
                        "refund_calculation_success": refund_calculation.get(
                            "success", False
                        ),
                        "refund_calculation_message": refund_calculation.get(
                            "message", ""
                        ),
                        "order_customer_email": order_customer_email,
                    },
                    "slack_error": {
                        "error": error_message,
                        "full_response": slack_result,
                    },
                },
            )

        # Determine message based on whether refund calculation succeeded
        if refund_calculation.get("success"):
            message = "Refund request sent to Slack successfully"
        else:
            message = "Refund request sent to Slack with fallback message (season info missing)"

        return {
            "success": True,
            "message": message,
            "data": {
                "order_number": request.order_number,
                "requestor_email": request.requestor_email,
                "refund_type": request.refund_type,
                "refund_amount": refund_calculation.get("refund_amount", 0),
                "refund_calculation_success": refund_calculation.get("success", False),
                "refund_calculation_message": refund_calculation.get("message", ""),
                "order_customer_email": order_customer_email,
                "slack_result": slack_result,
            },
        }

    except HTTPException as http_exc:
        logger.error(
            f"🚫 HTTPException raised - Status: {http_exc.status_code}, Detail: {http_exc.detail}"
        )
        raise
    except Exception as e:
        logger.error(
            f"💥 UNEXPECTED ERROR processing refund Slack notification for order {request.order_number}"
        )
        logger.error(f"💥 Error type: {type(e).__name__}")
        logger.error(f"💥 Error message: {str(e)}")
        logger.error(f"💥 Error details: {e}")

        # More descriptive error message
        error_details = {
            "error": "internal_server_error",
            "message": f"Failed to process refund request for order {request.order_number}",
            "details": str(e),
            "error_type": type(e).__name__,
        }

        logger.error("🚫 Raising 500 HTTPException for unexpected error")
        raise HTTPException(status_code=500, detail=error_details)


@router.post("/test/validate-deny-action")
async def validate_deny_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test endpoint to validate deny action payload structure.
    Used for testing to ensure correct data is being sent to GAS.
    """
    try:
        from services.slack.tests.deny_action_validator import DenyActionValidator

        validation_result = DenyActionValidator.validate_payload(payload)

        return {
            "success": True,
            "message": "Payload validation completed",
            "validation": validation_result,
            "received_payload": payload,
        }

    except Exception as e:
        logger.error(f"Error validating deny action payload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint for the refunds service"""
    return {"status": "healthy", "service": "refunds"}
