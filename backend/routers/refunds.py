from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from services.orders import OrdersService
from services.slack import SlackService
from models.requests import RefundSlackNotificationRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/refunds", tags=["refunds"])

orders_service = OrdersService()
slack_service = SlackService()

@router.post("/send-to-slack")
async def send_refund_to_slack(request: RefundSlackNotificationRequest) -> Dict[str, Any]:
    """
    Validate order and email, then send refund request to Slack
    This endpoint validates the email matches the order's customer email,
    fetches and caches the full order details, then sends to Slack
    """
    try:
        logger.info(f"Processing refund Slack notification for order {request.order_number}")
        
        # Step 1: Fetch order details and validate email
        order_result = orders_service.fetch_order_details_by_email_or_order_name(order_name=request.order_number)
        
        if not order_result["success"]:
            logger.error(f"Order {request.order_number} not found: {order_result['message']}")
            
            # Send order not found error to Slack
            requestor_info = {
                "name": request.requestor_name,
                "email": request.requestor_email,
                "refund_type": request.refund_type,
                "notes": request.notes
            }
            
            slack_result = slack_service.send_refund_request_notification(
                requestor_info=requestor_info,
                sheet_link=request.sheet_link,
                error_type="order_not_found",
                raw_order_number=request.order_number
            )
            
            raise HTTPException(
                status_code=406,
                detail=f"Order {request.order_number} not found in Shopify"
            )
        
        # Step 2: Extract order data
        order_data = order_result["data"]  # Changed from order_result["order"] to order_result["data"]
        order_customer_email = order_data.get("customer", {}).get("email", "").lower()
        provided_email = request.requestor_email.lower()
        
        if order_customer_email != provided_email:
            logger.error(f"Email mismatch for order {request.order_number}: {order_customer_email} != {provided_email}")
            
            # Send email mismatch error to Slack
            requestor_info = {
                "name": request.requestor_name,
                "email": request.requestor_email,
                "refund_type": request.refund_type,
                "notes": request.notes
            }
            
            slack_result = slack_service.send_refund_request_notification(
                order_data={"order": order_data},
                requestor_info=requestor_info,
                sheet_link=request.sheet_link,
                error_type="email_mismatch",
                order_customer_email=order_customer_email
            )
            
            raise HTTPException(
                status_code=409,
                detail=f"Email {request.requestor_email} does not match order customer email"
            )
        
        # Step 3: Calculate refund information (this caches the calculation)
        refund_calculation = orders_service.calculate_refund_due(order_data, request.refund_type)
        
        # Step 4: Prepare requestor info for Slack
        requestor_info = {
            "name": request.requestor_name,
            "email": request.requestor_email,
            "refund_type": request.refund_type,
            "notes": request.notes
        }
        
        # Step 5: Send notification to Slack (handles both success and fallback cases)
        slack_result = slack_service.send_refund_request_notification(
            order_data={"order": order_data},
            refund_calculation=refund_calculation,
            requestor_info=requestor_info,
            sheet_link=request.sheet_link
        )
        
        if not slack_result["success"]:
            error_message = slack_result.get('error', slack_result.get('message', 'Unknown error'))
            logger.error(f"Failed to send Slack notification: {error_message}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "slack_notification_failed",
                    "message": f"Failed to send Slack notification: {error_message}"
                }
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
                "slack_result": slack_result
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing refund Slack notification for order {request.order_number}: {str(e)}")
        logger.error(f"Error details: {type(e).__name__}: {e}")
        
        # More descriptive error message
        error_details = {
            "error": "internal_server_error",
            "message": f"Failed to process refund request for order {request.order_number}",
            "details": str(e),
            "error_type": type(e).__name__
        }
        
        raise HTTPException(
            status_code=500,
            detail=error_details
        )

@router.get("/health")
async def health_check():
    """Health check endpoint for the refunds service"""
    return {"status": "healthy", "service": "refunds"} 