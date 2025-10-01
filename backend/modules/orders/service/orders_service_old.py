"""
Main Orders service for handling Shopify order operations.
Refactored to use helper modules for better organization.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from modules.integrations.shopify.client import ShopifyClient
from .refund_calculator import RefundCalculator

logger = logging.getLogger(__name__)


class OrdersService:
    """
    Main service for handling order operations.

    This service coordinates order fetching, refund calculations,
    and Shopify operations through specialized helper classes.
    """

    def __init__(self):
        # self.shopify_orchestrator = ShopifyOrchestrator()

        # Initialize helper components
        self.refund_calculator = RefundCalculator()

    # def fetch_product_variants(self, product_id: str) -> List[Dict[str, Any]]:
    #     """
    #     Fetch all variants for a specific product by product ID
    #     """
    #     try:
    #         query = {
    #             "query": f"""{{
    #                 product(id: "{product_id}") {{
    #                     id
    #                     title
    #                     variants(first: 50) {{
    #                         edges {{
    #                             node {{
    #                                 id
    #                                 title
    #                                 price
    #                                 inventoryQuantity
    #                                 inventoryItem {{ id }}
    #                             }}
    #                         }}
    #                     }}
    #                 }}
    #             }}"""
    #         }

    #         result = self.shopify_orchestrator._make_shopify_request(query)

    #         if (
    #             not result
    #             or not result.get("data")
    #             or not result["data"].get("product")
    #         ):
    #             return []

    #         product = result["data"]["product"]
    #         variants = []

    #         for variant_edge in product["variants"]["edges"]:
    #             variant = variant_edge["node"]
    #             variants.append(
    #                 {
    #                     "variantId": variant["id"],
    #                     "variantName": variant["title"],
    #                     "price": variant["price"],
    #                     "inventory": variant["inventoryQuantity"],
    #                     "inventoryItemId": variant["inventoryItem"]["id"],
    #                 }
    #             )

    #         return variants

    #     except Exception as e:
    #         logger.error(f"Error fetching product variants for {product_id}: {str(e)}")
    #         return []

    # def calculate_refund_due(
    #     self,
    #     order_data: Dict[str, Any],
    #     refund_type: str,
    #     request_submitted_at: Optional[datetime] = None,
    # ) -> Dict[str, Any]:
    #     """
    #     Calculate refund amount for an order.
    #     Delegates to the RefundCalculator helper.
    #     """
    #     return self.refund_calculator.calculate_refund_due(
    #         order_data, refund_type, request_submitted_at
    #     )

    # def cancel_order(self, order_id: str) -> Dict[str, Any]:
    #     """
    #     Cancel an order.
    #     Delegates to ShopifyOperations helper.
    #     """
    #     return self.shopify_orchestrator.cancel_order(order_id)

    # def cancel_order_with_refund_calculation(
    #     self, 
    #     order_number: str, 
    #     refund_type: str = "refund"
    # ) -> Dict[str, Any]:
    #     """
    #     Complete order cancellation workflow: fetch order, calculate refund, cancel order.
        
    #     Args:
    #         order_number: The order number to cancel
    #         refund_type: Type of refund (refund, store_credit, etc.)
            
    #     Returns:
    #         Dict containing success status, order data, and refund calculation
    #     """
    #     try:
    #         logger.info(f"Starting order cancellation workflow for {order_number}")
            
    #         # 1. Fetch order details
    #         order_result = self.fetch_order_details_by_email_or_order_number(
    #             order_number=order_number
    #         )
    #         if not order_result["success"]:
    #             return {
    #                 "success": False,
    #                 "error": f"Failed to fetch order details: {order_result['message']}",
    #                 "order_data": None,
    #                 "refund_calculation": None
    #             }
            
    #         shopify_order_data = order_result["data"]
    #         order_id = shopify_order_data.get("id", "")
            
    #         # 2. Calculate refund amount
    #         refund_calculation = self.calculate_refund_due(
    #             shopify_order_data, refund_type
    #         )
            
    #         # 3. Cancel order
    #         cancel_result = self.cancel_order(order_id)
            
    #         if not cancel_result["success"]:
    #             return {
    #                 "success": False,
    #                 "error": f"Failed to cancel order: {cancel_result.get('message', 'Unknown error')}",
    #                 "order_data": shopify_order_data,
    #                 "refund_calculation": refund_calculation,
    #                 "shopify_errors": cancel_result.get("shopify_errors", [])
    #             }
            
    #         # 4. Return success with all data
    #         return {
    #             "success": True,
    #             "order_data": shopify_order_data,
    #             "refund_calculation": refund_calculation,
    #             "cancel_result": cancel_result
    #         }
            
    #     except Exception as e:
    #         logger.error(f"Error in cancel_order_with_refund_calculation: {str(e)}")
    #         return {
    #             "success": False,
    #             "error": f"Unexpected error: {str(e)}",
    #             "order_data": None,
    #             "refund_calculation": None
    #         }

    # def create_refund_or_credit(
    #     self, order_id: str, amount: float, refund_type: str
    # ) -> Dict[str, Any]:
    #     """
    #     Create either a refund or store credit based on refund_type.
    #     Delegates to ShopifyOperations helper.
    #     """
    #     return self.shopify_orchestrator.create_refund(order_id, amount, refund_type)

    # def check_existing_refunds(self, order_id: str) -> Dict[str, Any]:
    #     """
    #     Check for existing refunds on an order.
    #     Returns structured data about any refunds found.
    #     """
    #     try:
    #         logger.info(f"Checking for existing refunds on order: {order_id}")

    #         # Prepare GraphQL query for refunds
    #         query = {
    #             "query": """
    #                 query getOrderRefunds($id: ID!) {
    #                     order(id: $id) {
    #                         id
    #                         name
    #                         refunds {
    #                             id
    #                             createdAt
    #                             updatedAt
    #                             note
    #                             legacyResourceId
    #                             totalRefundedSet {
    #                                 presentmentMoney {
    #                                     amount
    #                                     currencyCode
    #                                 }
    #                             }
    #                             transactions(first: 10) {
    #                                 edges {
    #                                     node {
    #                                         id
    #                                         kind
    #                                         status
    #                                         amount
    #                                         gateway
    #                                         createdAt
    #                                     }
    #                                 }
    #                             }
    #                             refundLineItems(first: 10) {
    #                                 edges {
    #                                     node {
    #                                         id
    #                                         quantity
    #                                         lineItem {
    #                                             id
    #                                             title
    #                                         }
    #                                     }
    #                                 }
    #                             }
    #                         }
    #                     }
    #                 }
    #             """,
    #             "variables": {"id": order_id},
    #         }

    #         response = self.shopify_orchestrator._make_shopify_request(query=query)

    #         if not response or "data" not in response or not response["data"]["order"]:
    #             return {
    #                 "success": False,
    #                 "message": "Failed to check existing refunds or order not found",
    #             }

    #         order_data = response["data"]["order"]

    #         # Handle both GraphQL response format and test data format
    #         refunds_data = order_data.get("refunds", [])
    #         if isinstance(refunds_data, dict) and "edges" in refunds_data:
    #             # GraphQL format: { edges: [...] }
    #             refunds_edges = refunds_data["edges"]
    #         elif isinstance(refunds_data, list):
    #             # Test data format: [...] (direct list)
    #             refunds_edges = [{"node": refund} for refund in refunds_data]
    #         else:
    #             refunds_edges = []

    #         processed_refunds = []
    #         total_amount = 0.0
    #         pending_refunds = 0
    #         resolved_refunds = 0
    #         pending_amount = 0.0
    #         resolved_amount = 0.0

    #         for edge in refunds_edges:
    #             refund = edge["node"]

    #             # Calculate transaction amounts and determine status
    #             transactions_edges = refund.get("transactions", {}).get("edges", [])
    #             if isinstance(refund.get("transactions"), list):
    #                 # Handle test data format where transactions is direct list
    #                 transactions_edges = [
    #                     {"node": t} for t in refund.get("transactions", [])
    #                 ]

    #             refund_amount = 0.0
    #             refund_status = "completed"  # Default to completed

    #             transactions = []
    #             for transaction_edge in transactions_edges:
    #                 transaction = transaction_edge["node"]
    #                 amount = float(transaction.get("amount", 0))
    #                 status = transaction.get("status", "SUCCESS")

    #                 # Determine overall refund status based on transactions
    #                 if status == "PENDING":
    #                     refund_status = "pending"

    #                 refund_amount += amount
    #                 transactions.append(
    #                     {
    #                         "id": transaction.get("id"),
    #                         "kind": transaction.get("kind"),
    #                         "status": status,
    #                         "amount": transaction.get("amount"),
    #                         "gateway": transaction.get("gateway"),
    #                         "created_at": transaction.get("createdAt"),
    #                     }
    #                 )

    #             # If no transactions, check totalRefundedSet
    #             if refund_amount == 0.0:
    #                 total_refunded_set = refund.get("totalRefundedSet", {})
    #                 if total_refunded_set:
    #                     presentment_money = total_refunded_set.get(
    #                         "presentmentMoney", {}
    #                     )
    #                     refund_amount = float(presentment_money.get("amount", 0))

    #             # Process line items
    #             line_items = []
    #             line_items_edges = refund.get("refundLineItems", {}).get("edges", [])
    #             for line_item_edge in line_items_edges:
    #                 line_item_node = line_item_edge["node"]
    #                 line_item = line_item_node.get("lineItem", {})
    #                 line_items.append(
    #                     {
    #                         "id": line_item.get("id"),
    #                         "title": line_item.get("title"),
    #                         "quantity": line_item_node.get("quantity"),
    #                     }
    #                 )

    #             # Count pending vs resolved
    #             if refund_status == "pending":
    #                 pending_refunds += 1
    #                 pending_amount += refund_amount
    #             else:
    #                 resolved_refunds += 1
    #                 resolved_amount += refund_amount

    #             total_amount += refund_amount

    #             # Create status display
    #             status_display = f"${refund_amount:.2f} ({'Pending' if refund_status == 'pending' else 'Completed'})"

    #             processed_refunds.append(
    #                 {
    #                     "id": refund.get("id"),
    #                     "total_refunded": str(refund_amount),
    #                     "amount": refund_amount,
    #                     "status": refund_status,
    #                     "status_display": status_display,
    #                     "pending_amount": refund_amount
    #                     if refund_status == "pending"
    #                     else 0.0,
    #                     "completed_amount": refund_amount
    #                     if refund_status == "completed"
    #                     else 0.0,
    #                     "currency": refund.get("totalRefundedSet", {})
    #                     .get("presentmentMoney", {})
    #                     .get("currencyCode", "USD"),
    #                     "created_at": refund.get("createdAt"),
    #                     "updated_at": refund.get("updatedAt"),
    #                     "note": refund.get("note", ""),
    #                     "transactions": transactions,
    #                     "line_items": line_items,
    #                 }
    #             )

    #         return {
    #             "success": True,
    #             "has_refunds": len(processed_refunds) > 0,
    #             "total_refunds": len(processed_refunds),
    #             "pending_refunds": pending_refunds,
    #             "resolved_refunds": resolved_refunds,
    #             "pending_amount": pending_amount,
    #             "resolved_amount": resolved_amount,
    #             "total_amount": total_amount,
    #             "order_id": order_data.get("id"),
    #             "order_number": order_data.get("name"),
    #             "refunds": processed_refunds,
    #         }

    #     except Exception as e:
    #         logger.error(f"Error checking existing refunds for order {order_id}: {e}")
    #         return {
    #             "success": False,
    #             "message": f"Error checking existing refunds: {str(e)}",
    #         }
