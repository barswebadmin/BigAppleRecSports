from typing import Dict, Any, Optional
from backend.models.shopify.requests import FetchOrderRequest
from backend.new_structure_target.clients.shopify.builders.shopify_normalizers import normalize_order_id, normalize_order_number
from new_structure_target.clients.shopify.shopify_service import ShopifyService
from new_structure_target.clients.slack.slack_service import SlackService

class OrdersService:
    def __init__(self):
        self.shopify_service = ShopifyService()
        self.slack_service = SlackService()

    def fetch_order_from_shopify(
        self,
        *,
        request_args: FetchOrderRequest,
    ) -> Dict[str, Any]:

        try:
            fetched_order = self.shopify_service.fetch_order(request_args=request_args)
        except Exception as e:
            return {"success": False, "message": str(e)}
        return fetched_order
        # if normalized_order_id:
        #     return self.shopify_service.get_order_details(order_id=normalized_order_id.get("digits_only"))
        # if normalized_order_number:
        #     return self.shopify_service.get_order_details(order_number=normalized_order_number.get("with_hash"))
        # return {"success": False, "message": "No valid order ID or order number provided"}