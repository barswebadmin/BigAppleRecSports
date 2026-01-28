from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime
import logging
from modules.integrations.shopify.models import FetchOrderRequest
from modules.integrations.shopify import ShopifyClient
from modules.integrations.shopify.services.shopify_normalizers import normalize_order_identifier
from modules.integrations.slack import SlackClient
from modules.refunds.app.calculate_refund_due import calculate_refund_due
from shared.order_fetcher import fetch_order_from_shopify

if TYPE_CHECKING:
    from modules.integrations.shopify.services.shopify_service import ShopifyService

logger = logging.getLogger(__name__)

class OrdersService:
    def __init__(self, shopify_client: Optional[ShopifyClient] = None, shopify_service: Optional['ShopifyService'] = None):
        self.shopify_client = shopify_client or ShopifyClient()
        self.slack_client = SlackClient()
        self._shopify_service = shopify_service

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
        return fetch_order_from_shopify(request_args, self.shopify_client)

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

    @property
    def shopify_service(self) -> 'ShopifyService':
        """Lazy import ShopifyService to avoid circular dependencies."""
        if self._shopify_service is None:
            from modules.integrations.shopify.services.shopify_service import ShopifyService
            self._shopify_service = ShopifyService()
        return self._shopify_service

    def check_existing_refunds(self, order_id: str) -> Dict[str, Any]:
        """
        Check for existing refunds on an order.
        Returns structured data about any refunds found.
        
        Args:
            order_id: Shopify order ID (numeric, GID, or URL format)
        
        Returns:
            Dict with keys:
            - success: bool
            - has_refunds: bool
            - total_refunds: int
            - pending_refunds: int (count)
            - resolved_refunds: int (count)
            - pending_amount: float
            - resolved_amount: float
            - total_amount: float
            - order_id: str
            - order_number: str
            - refunds: List[Dict] with detailed refund information
        """
        try:
            logger.info(f"Checking for existing refunds on order: {order_id}")

            normalized = normalize_order_identifier(order_id)
            if not normalized:
                return {
                    "success": False,
                    "message": f"Invalid order ID format: {order_id}",
                }
            
            digits_only = normalized.get("digits_only")
            if not digits_only:
                return {
                    "success": False,
                    "message": f"Could not extract order ID from: {order_id}",
                }

            query_params = {
                "query": f"id:{digits_only}",
                "first": 1,
                "identifier": order_id
            }
            
            orders = self.shopify_service.get_order_by_identifier(query_params, line_items_first=10)
            if not orders:
                return {
                    "success": False,
                    "message": "Failed to check existing refunds or order not found",
                }
            
            order = orders[0]
            order_id_value = getattr(order, 'id', None)  # type: ignore[attr-defined]
            order_number = getattr(order, 'name', None)  # type: ignore[attr-defined]
            
            refunds = getattr(order, 'refunds', None)  # type: ignore[attr-defined]
            if not refunds:
                return {
                    "success": True,
                    "has_refunds": False,
                    "total_refunds": 0,
                    "pending_refunds": 0,
                    "resolved_refunds": 0,
                    "pending_amount": 0.0,
                    "resolved_amount": 0.0,
                    "total_amount": 0.0,
                    "order_id": order_id_value,
                    "order_number": order_number,
                    "refunds": [],
                }
            
            refund_list = list(refunds) if hasattr(refunds, '__iter__') and not isinstance(refunds, str) else []
            
            processed_refunds = []
            total_amount = 0.0
            pending_refunds_count = 0
            resolved_refunds_count = 0
            pending_amount = 0.0
            resolved_amount = 0.0

            for refund in refund_list:
                refund_id = getattr(refund, 'id', None)  # type: ignore[attr-defined]
                refund_created_at = getattr(refund, 'createdAt', None)  # type: ignore[attr-defined]
                refund_note = getattr(refund, 'note', None) or ""  # type: ignore[attr-defined]
                
                total_refunded_set = getattr(refund, 'totalRefundedSet', None)  # type: ignore[attr-defined]
                refund_amount = 0.0
                refund_status = "completed"
                currency = "USD"
                
                if total_refunded_set:
                    shop_money = getattr(total_refunded_set, 'shopMoney', None)  # type: ignore[attr-defined]
                    if shop_money:
                        amount_str = getattr(shop_money, 'amount', '0')  # type: ignore[attr-defined]
                        currency = getattr(shop_money, 'currencyCode', 'USD')  # type: ignore[attr-defined]
                        try:
                            refund_amount = float(amount_str)
                        except (ValueError, TypeError):
                            refund_amount = 0.0
                
                refund_transactions_conn = getattr(refund, 'transactions', None)  # type: ignore[attr-defined]
                transactions = []
                
                if refund_transactions_conn:
                    transaction_nodes = getattr(refund_transactions_conn, 'nodes', None)  # type: ignore[attr-defined]
                    if transaction_nodes:
                        for trans in transaction_nodes:
                            trans_id = getattr(trans, 'id', None)  # type: ignore[attr-defined]
                            trans_kind = getattr(trans, 'kind', None)  # type: ignore[attr-defined]
                            trans_status = getattr(trans, 'status', None)  # type: ignore[attr-defined]
                            trans_amount_str = getattr(trans, 'amount', None)  # type: ignore[attr-defined]
                            trans_gateway = getattr(trans, 'gateway', None)  # type: ignore[attr-defined]
                            trans_created_at = getattr(trans, 'createdAt', None)  # type: ignore[attr-defined]
                            
                            if trans_kind == 'REFUND':
                                try:
                                    trans_amount = float(trans_amount_str) if trans_amount_str else 0.0
                                    if refund_amount == 0.0:
                                        refund_amount = trans_amount
                                    if trans_status == 'PENDING':
                                        refund_status = "pending"
                                    
                                    transactions.append({
                                        "id": trans_id,
                                        "kind": trans_kind,
                                        "status": trans_status,
                                        "amount": trans_amount_str,
                                        "gateway": trans_gateway,
                                        "created_at": trans_created_at,
                                    })
                                except (ValueError, TypeError):
                                    pass
                
                refund_line_items_conn = getattr(refund, 'refundLineItems', None)  # type: ignore[attr-defined]
                line_items = []
                
                if refund_line_items_conn:
                    line_item_nodes = getattr(refund_line_items_conn, 'nodes', None)  # type: ignore[attr-defined]
                    if line_item_nodes:
                        for line_item_node in line_item_nodes:
                            line_item = getattr(line_item_node, 'lineItem', None)  # type: ignore[attr-defined]
                            quantity = getattr(line_item_node, 'quantity', None)  # type: ignore[attr-defined]
                            
                            if line_item:
                                line_item_id = getattr(line_item, 'id', None)  # type: ignore[attr-defined]
                                line_item_title = getattr(line_item, 'title', None)  # type: ignore[attr-defined]
                                
                                line_items.append({
                                    "id": line_item_id,
                                    "title": line_item_title,
                                    "quantity": quantity,
                                })
                
                if refund_status == "pending":
                    pending_refunds_count += 1
                    pending_amount += refund_amount
                else:
                    resolved_refunds_count += 1
                    resolved_amount += refund_amount

                total_amount += refund_amount
                status_display = f"${refund_amount:.2f} ({'Pending' if refund_status == 'pending' else 'Completed'})"

                processed_refunds.append({
                    "id": refund_id,
                    "total_refunded": str(refund_amount),
                    "amount": refund_amount,
                    "status": refund_status,
                    "status_display": status_display,
                    "pending_amount": refund_amount if refund_status == "pending" else 0.0,
                    "completed_amount": refund_amount if refund_status == "completed" else 0.0,
                    "currency": currency,
                    "created_at": refund_created_at,
                    "updated_at": refund_created_at,
                    "note": refund_note,
                    "transactions": transactions,
                    "line_items": line_items,
                })

            return {
                "success": True,
                "has_refunds": len(processed_refunds) > 0,
                "total_refunds": len(processed_refunds),
                "pending_refunds": pending_refunds_count,
                "resolved_refunds": resolved_refunds_count,
                "pending_amount": pending_amount,
                "resolved_amount": resolved_amount,
                "total_amount": total_amount,
                "order_id": order_id_value,
                "order_number": order_number,
                "refunds": processed_refunds,
            }

        except Exception as e:
            logger.error(f"Error checking existing refunds for order {order_id}: {e}")
            return {
                "success": False,
                "message": f"Error checking existing refunds: {str(e)}",
            }

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