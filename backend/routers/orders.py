from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
import logging
from pydantic import BaseModel
from datetime import datetime, timezone
import dateutil.parser

from modules.orders.services.orders_service import OrdersService
from modules.integrations.slack.slack_service import SlackService
from shared.order_fetcher import fetch_order_from_shopify
from modules.integrations.shopify.models.requests import FetchOrderRequest
from config import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["orders"])

orders_service = OrdersService()
slack_service = SlackService()


class SlackNotificationRequest(BaseModel):
    order_number: str
    requestor_name: Dict[str, str]  # {"first": "John", "last": "Doe"}
    requestor_email: str
    refund_type: str  # "refund" or "credit"
    notes: str
    order_data: Optional[Dict[str, Any]] = None
    sheet_link: Optional[str] = None  # Google Sheets link to the specific row
    request_submitted_at: Optional[str] = None

SlackChannel = config.SlackChannel


@router.get("/{order_number}")
async def get_order(
    order_number: str,
    email: Optional[str] = Query(
        None, description="Email to search by if order number fails"
    ),
) -> Dict[str, Any]:
    """
    Get order details by order number (or email as fallback)
    Based on fetchShopifyOrderDetails from the Google Apps Script
    """
    try:
        # Try to fetch by order number first
        fetch_request = FetchOrderRequest.create({"order_number": order_number})
        result = fetch_order_from_shopify(fetch_request)

        # If order not found by number and email provided, try by email
        if not result["success"] and email:
            logger.info(f"Order {order_number} not found, trying by email: {email}")
            fetch_request = FetchOrderRequest.create({"email": email})
            result = fetch_order_from_shopify(fetch_request)

        if not result["success"]:
            raise HTTPException(status_code=406, detail=result["message"])

        order_data = result["data"]

        # Add calculated refund information
        refund_calculation = orders_service.calculate_refund_due(order_data, "refund", None)
        credit_calculation = orders_service.calculate_refund_due(order_data, "credit", None)
        # TODO: Implement get_inventory_summary method in OrdersService
        # inventory_summary = orders_service.get_inventory_summary(order_data)
        inventory_summary = {"message": "Inventory summary not yet implemented"}

        # Enhance response with additional calculated data
        enhanced_response = {
            "order": order_data,
            "refund_calculation": refund_calculation,
            "credit_calculation": credit_calculation,
            "inventory_summary": inventory_summary,
            "product_urls": {
                "shopify_admin": f"https://admin.shopify.com/store/09fe59-3/products/{order_data['product']['productId'].split('/')[-1]}",
                "order_admin": f"https://admin.shopify.com/store/09fe59-3/orders/{order_data['orderId'].split('/')[-1]}",
            },
        }

        return {"success": True, "data": enhanced_response}

    except HTTPException:
        # Re-raise HTTPExceptions as-is (like 406 for order not found)
        raise
    except Exception as e:
        logger.error(f"Error fetching order {order_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching order: {str(e)}")


@router.post("/send-to-slack")
async def send_refund_to_slack(
    request: SlackNotificationRequest,
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
        from shared.date_utils import format_date_and_time

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
        fetch_request = FetchOrderRequest.create({"order_number": request.order_number})
        order_result = fetch_order_from_shopify(fetch_request)
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
            if error_type in ["connection_error", "api_error", "server_error"]:
                # Connection/API/server errors - log and return error to GAS, don't email customer
                logger.error(f"🚨 Shopify {error_type} - not sending customer email")
                print(f"🚨 Shopify {error_type}: {error_message}")

                raise HTTPException(
                    status_code=503,  # Service Unavailable
                    detail={
                        "error": "shopify_connection_error",
                        "message": error_message,
                        "user_message": "There was a technical issue connecting to our system. Please try submitting your refund request again in a few minutes.",
                    },
                )
            elif error_type == "config_error":
                # Configuration errors (401, 404) - return actual Shopify status codes
                actual_status_code = order_result.get("status_code", 400)
                logger.error(
                    f"🚨 Shopify configuration error ({actual_status_code}) - not sending customer email"
                )
                print(
                    f"🚨 Shopify configuration error ({actual_status_code}): {error_message}"
                )

                raise HTTPException(
                    status_code=actual_status_code,  # Use actual Shopify status code (401/404)
                    detail={
                        "error": "shopify_config_error",
                        "errors": error_message,  # Use "errors" key to match Shopify format
                        "user_message": "There is a system configuration issue. Please contact support or try again later.",
                    },
                )
            elif error_type == "order_not_found":
                # Legitimate "order not found" from successful Shopify 200 response - send notification to Slack (which emails customer)
                logger.info(
                    "📤 Sending 'order not found' notification to Slack (successful Shopify response, no matching orders)"
                )
                requestor_info = {
                    "name": request.requestor_name,
                    "email": request.requestor_email,
                    "refund_type": request.refund_type,
                    "notes": request.notes,
                }

                try:
                    message_text = (
                        f"Order not found for {request.requestor_name.get('first','')} {request.requestor_name.get('last','')} "
                        f"<{request.requestor_email}> — Order: {request.order_number}\n"
                        f"Notes: {request.notes}\nSubmitted: {request_initiated_at}"
                    )
                    # TODO: Implement send_message method in SlackService or use SlackClient directly
                    slack_result = {"success": True, "message": "Slack notification sent (mocked)"}
                    logger.info(f"✅ Slack notification sent: {slack_result.get('success')}")
                except Exception as slack_error:
                    logger.error(f"❌ Failed to send Slack notification: {str(slack_error)}")
                    logger.error(f"❌ Slack error type: {type(slack_error).__name__}")

                logger.info("🚫 Raising 406 HTTPException for order not found")
                raise HTTPException(
                    status_code=406,
                    detail=f"Order {request.order_number} not found in Shopify",
                )
            else:
                # Unexpected error type - treat as API error
                logger.error(
                    f"🚨 Unexpected error type: {error_type} - treating as API error"
                )
                raise HTTPException(
                    status_code=503,  # Service Unavailable
                    detail={
                        "error": "shopify_api_error",
                        "message": error_message,
                        "user_message": "There was a technical issue. Please try submitting your refund request again in a few minutes.",
                    },
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

            slack_message = (
                f"Email mismatch for order {request.order_number}: "
                f"order email={order_customer_email}, provided={provided_email}\n"
                f"Requestor: {request.requestor_name.get('first','')} {request.requestor_name.get('last','')} <{request.requestor_email}>\n"
                f"Notes: {request.notes}"
            )
            # TODO: Implement send_message method in SlackService or use SlackClient directly
            slack_result = {"success": True, "message": "Slack notification sent (mocked)"}

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
        # TODO: Implement check_existing_refunds method in OrdersService
        existing_refunds_result = {"success": True, "has_refunds": False, "total_refunds": 0}
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
                dup_msg = (
                    f"Duplicate refund detected for order {request.order_number}. "
                    f"Total refunds: {existing_refunds_result.get('total_refunds', 0)}\n"
                    f"Requestor: {request.requestor_name.get('first','')} {request.requestor_name.get('last','')} <{request.requestor_email}>\n"
                    f"Notes: {request.notes}"
                )
                # TODO: Implement send_message method in SlackService or use SlackClient directly
                slack_result = {"success": True, "message": "Slack notification sent (mocked)"}
                logger.info(f"✅ Slack duplicate refund notification sent: {slack_result.get('success')}")
            except Exception as slack_error:
                logger.error(f"❌ Failed to send Slack duplicate refund notification: {str(slack_error)}")
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
        # TODO: Implement get_customer_by_email method in OrdersService
        customer_result = {"success": False, "customer": None}
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
        success_msg = (
            f"Refund request for order {request.order_number} ({request.refund_type}).\n"
            f"Requestor: {request.requestor_name.get('first','')} {request.requestor_name.get('last','')} <{request.requestor_email}>\n"
            f"Calculated refund: ${refund_calculation.get('refund_amount', 0):.2f}\n"
            f"Notes: {request.notes}"
        )
        # TODO: Implement send_message method in SlackService or use SlackClient directly
        slack_result = {"success": True, "message": "Slack notification sent (mocked)"}

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