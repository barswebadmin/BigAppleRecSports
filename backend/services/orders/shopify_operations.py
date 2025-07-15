"""
Shopify operations utilities.
Handles order cancellation, refunds, and inventory management.
"""

from typing import Dict, Any, Optional, List
import logging
import json
from ..shopify_service import ShopifyService

logger = logging.getLogger(__name__)


class ShopifyOperations:
    """Helper class for Shopify order operations like cancellation and refunds."""
    
    def __init__(self, location_id: str = "61802217566"):
        self.shopify_service = ShopifyService()
        self.location_id = location_id
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel a Shopify order
        Based on cancelShopifyOrder from ShopifyUtils.gs
        """
        try:
            mutation = {
                "query": """
                    mutation orderCancel($notifyCustomer: Boolean, $orderId: ID!, $reason: OrderCancelReason!, $refund: Boolean!, $restock: Boolean!, $staffNote: String) {
                        orderCancel(notifyCustomer: $notifyCustomer, orderId: $orderId, reason: $reason, refund: $refund, restock: $restock, staffNote: $staffNote) {
                            job {
                                id
                                done
                            }
                            orderCancelUserErrors {
                                field
                                message
                            }
                            userErrors {
                                field
                                message
                            }
                        }
                    }
                """,
                "variables": {
                    "notifyCustomer": False,
                    "orderId": order_id,
                    "reason": "CUSTOMER",
                    "refund": False,
                    "restock": False,
                }
            }
            
            print(f"\n🔍 === SHOPIFY CANCEL ORDER DEBUG ===")
            print(f"📤 Sending mutation to Shopify:")
            print(f"   Order ID: {order_id}")
            print(f"   Mutation variables: {mutation['variables']}")
            print(f"   Mutation query (first 200 chars): {mutation['query'][:200]}...")
            
            response_data = self.shopify_service._make_request(mutation)
            
            print(f"📥 Raw Shopify response:")
            print(f"   Type: {type(response_data)}")
            print(f"   Response: {response_data}")
            print("=== END SHOPIFY CANCEL ORDER DEBUG ===\n")
            
            if response_data is None:
                return {"success": False, "message": "Failed to cancel order - no response from Shopify API", "raw_response": None}
            
            if "data" not in response_data:
                # Check for GraphQL errors in response
                if "errors" in response_data:
                    return {"success": False, "message": f"Failed to cancel order - GraphQL errors: {response_data['errors']}", "raw_response": response_data}
                return {"success": False, "message": f"Failed to cancel order - invalid response format. Response: {response_data}", "raw_response": response_data}
            
            if "orderCancel" not in response_data["data"]:
                return {"success": False, "message": f"Failed to cancel order - missing orderCancel in response. Data keys: {list(response_data['data'].keys())}", "raw_response": response_data}
            
            data = response_data["data"]["orderCancel"]
            
            if data.get("userErrors") or data.get("orderCancelUserErrors"):
                errors = data.get("userErrors", []) + data.get("orderCancelUserErrors", [])
                return {"success": False, "message": f"Order cancellation failed: {errors}", "raw_response": response_data, "shopify_errors": errors}
            
            return {"success": True, "data": data, "raw_response": response_data}
            
        except Exception as e:
            logger.error(f"Error canceling order: {str(e)}")
            return {"success": False, "message": f"Error canceling order: {str(e)}", "raw_response": "Exception occurred before response"}
    
    def create_refund(self, order_id: str, refund_amount: float) -> Dict[str, Any]:
        """
        Create a refund for a Shopify order
        Based on createShopifyRefund from ShopifyUtils.gs
        """
        try:
            # Step 1: Fetch order transactions
            order_details_query = {
                "query": """
                    query getOrderDetails($id: ID!) {
                        order(id: $id) {
                            id
                            transactions {
                                id
                                kind
                                gateway
                                parentTransaction { id }
                            }
                        }
                    }
                """,
                "variables": {"id": order_id}
            }
            
            response = self.shopify_service._make_request(order_details_query)
            if not response or "data" not in response:
                return {"success": False, "message": "Failed to fetch order details for refund"}
            
            order = response["data"]["order"]
            transactions = order.get("transactions", [])
            
            # Find the capture transaction
            capture_transaction = None
            for transaction in transactions:
                if transaction["kind"] == "CAPTURE":
                    capture_transaction = transaction
                    break
            
            if not capture_transaction:
                return {"success": False, "message": "No capture transaction found for refund"}
            
            # Get gateway and parent transaction ID
            gateway = capture_transaction["gateway"]
            parent_transaction_id = capture_transaction.get("parentTransaction", {}).get("id") or capture_transaction["id"]
            
            # Step 2: Create the refund mutation (matching Google Apps Script format)
            refund_mutation = {
                "query": """
                    mutation CreateRefund($input: RefundInput!) {
                        refundCreate(input: $input) {
                            refund {
                                id
                                note
                                totalRefundedSet {
                                    presentmentMoney {
                                        amount
                                    }
                                }
                            }
                            userErrors {
                                field
                                message
                            }
                        }
                    }
                """,
                "variables": {
                    "input": {
                        "notify": True,
                        "orderId": order_id,
                        "note": f"Refund issued via Slack workflow for ${refund_amount:.2f}",
                        "transactions": [
                            {
                                "orderId": order_id,
                                "gateway": gateway,
                                "kind": "REFUND",
                                "amount": str(refund_amount),
                                "parentId": parent_transaction_id
                            }
                        ]
                    }
                }
            }
            
            refund_response = self.shopify_service._make_request(refund_mutation)
            if not refund_response or "data" not in refund_response:
                return {"success": False, "message": "Failed to create refund"}
            
            refund_data = refund_response["data"]["refundCreate"]
            
            if refund_data.get("userErrors"):
                errors = refund_data["userErrors"]
                return {"success": False, "message": f"Refund creation failed: {errors}"}
            
            return {"success": True, "data": refund_data["refund"]}
            
        except Exception as e:
            logger.error(f"Error creating refund: {str(e)}")
            return {"success": False, "message": f"Error creating refund: {str(e)}"}
    
    def restock_inventory(self, order_id: str) -> Dict[str, Any]:
        """
        Restock inventory for an order
        Based on restockOrder from ShopifyUtils.gs
        """
        try:
            # First, get the order details with line items
            order_query = {
                "query": """
                    query getOrderForRestock($id: ID!) {
                        order(id: $id) {
                            id
                            lineItems(first: 10) {
                                edges {
                                    node {
                                        id
                                        quantity
                                        variant {
                                            id
                                            inventoryItem {
                                                id
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                """,
                "variables": {"id": order_id}
            }
            
            response = self.shopify_service._make_request(order_query)
            if not response or "data" not in response:
                return {"success": False, "message": "Failed to fetch order for restocking"}
            
            order = response["data"]["order"]
            line_items = order.get("lineItems", {}).get("edges", [])
            
            if not line_items:
                return {"success": False, "message": "No line items found for restocking"}
            
            # Restock each item
            restock_results = []
            for item_edge in line_items:
                item = item_edge["node"]
                quantity = item["quantity"]
                inventory_item_id = item["variant"]["inventoryItem"]["id"]
                
                # Adjust inventory
                adjust_mutation = {
                    "query": """
                        mutation inventoryAdjustQuantity($input: InventoryAdjustQuantityInput!) {
                            inventoryAdjustQuantity(input: $input) {
                                inventoryLevel {
                                    id
                                    available
                                }
                                userErrors {
                                    field
                                    message
                                }
                            }
                        }
                    """,
                    "variables": {
                        "input": {
                            "inventoryLevelId": f"gid://shopify/InventoryLevel/{inventory_item_id}?inventory_item_id={inventory_item_id}",
                            "availableDelta": quantity
                        }
                    }
                }
                
                adjust_response = self.shopify_service._make_request(adjust_mutation)
                if adjust_response and "data" in adjust_response:
                    adjust_data = adjust_response["data"]["inventoryAdjustQuantity"]
                    if adjust_data.get("userErrors"):
                        restock_results.append({
                            "item_id": item["id"],
                            "success": False,
                            "error": adjust_data["userErrors"]
                        })
                    else:
                        restock_results.append({
                            "item_id": item["id"],
                            "success": True,
                            "quantity_restocked": quantity
                        })
                else:
                    restock_results.append({
                        "item_id": item["id"],
                        "success": False,
                        "error": "Failed to adjust inventory"
                    })
            
            # Check if all restocks were successful
            all_successful = all(result["success"] for result in restock_results)
            
            return {
                "success": all_successful,
                "message": "All items restocked successfully" if all_successful else "Some items failed to restock",
                "restock_results": restock_results
            }
            
        except Exception as e:
            logger.error(f"Error restocking inventory: {str(e)}")
            return {"success": False, "message": f"Error restocking inventory: {str(e)}"} 