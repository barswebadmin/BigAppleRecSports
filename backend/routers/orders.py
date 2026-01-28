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
from backend.config import config

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
    Legacy endpoint - Slack refund functionality removed.
    This endpoint is kept for backward compatibility but no longer processes refunds via Slack.
    """
    logger.warning(f"Legacy endpoint called: /send-to-slack for order {request.order_number}")
    return {
        "success": False,
        "message": "Slack refund functionality has been removed. Please use the new refund processing system.",
        "data": {
            "order_number": request.order_number,
            "requestor_email": request.requestor_email,
        }
    }