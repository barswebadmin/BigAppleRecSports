from typing import Dict, Any, Optional
from datetime import datetime
from backend.modules.integrations.shopify.models import FetchOrderRequest
from backend.modules.integrations.shopify.models.responses import ShopifyResponse
from backend.modules.integrations.shopify import ShopifyClient
from backend.modules.integrations.slack import SlackClient
from backend.modules.refunds.app.calculate_refund_due import calculate_refund_due
from backend.shared.order_fetcher import fetch_order_details_with_validation

class OrdersService:
    def __init__(self, shopify_client: Optional[ShopifyClient] = None):
        self.shopify_client = shopify_client or ShopifyClient()
        self.slack_client = SlackClient()

    def fetch_order_from_shopify(
        self,
        *,
        request_args: FetchOrderRequest,
    ) -> Dict[str, Any]:
        """
        Fetch order details using FetchOrderRequest.
        This is the primary method for order fetching.
        Delegates to shared utility to avoid circular imports.
        """
        return fetch_order_details_with_validation(request_args, self.shopify_client)

    def calculate_refund_due(
        self,
        order_data: Dict[str, Any],
        refund_type: str,
        request_submitted_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculate refund amount for an order.
        Delegates to the calculate_refund_due function.
        """
        return calculate_refund_due(
            order_data, refund_type, request_submitted_at
        )

    # def fetch_order_details_by_email_or_order_number(
    #     self, 
    #     order_number: Optional[str] = None, 
    #     email: Optional[str] = None
    # ) -> Dict[str, Any]:
    #     """
    #     Legacy method for backward compatibility with orders router.
    #     Converts parameters to FetchOrderRequest and delegates to fetch_order_from_shopify.
    #     """
    #     try:
    #         if not order_number and not email:
    #             return {
    #                 "success": False,
    #                 "message": "Must provide either order_number or email.",
    #             }

    #         # Build FetchOrderRequest from parameters
    #         request_data = {}
    #         if order_number:
    #             request_data["order_number"] = order_number
    #         if email:
    #             request_data["email"] = email

    #         request_args = FetchOrderRequest.create(request_data)
    #         return self.fetch_order_from_shopify(request_args=request_args)
            
    #     except Exception as e:
    #         return {"success": False, "message": str(e)}