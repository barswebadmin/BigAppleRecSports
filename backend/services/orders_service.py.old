import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import json
import re
from .shopify_service import ShopifyService
from .slack_service import SlackService
from utils.date_utils import extract_season_dates, calculate_refund_amount

logger = logging.getLogger(__name__)

class OrdersService:
    def __init__(self):
        self.shopify_service = ShopifyService()
        self.slack_service = SlackService()
        self.location_id = "61802217566"  # Default location ID from the GS code
    
    def fetch_order_details(self, order_name: str = None, email: str = None) -> Dict[str, Any]:
        """
        Fetch order details from Shopify by order name or email
        Based on fetchShopifyOrderDetails from ShopifyUtils.gs
        """
        try:
            if not order_name and not email:
                return {"success": False, "message": "Must provide either orderName or email."}
            
            # Normalize order name
            if order_name:
                order_name = order_name if order_name.startswith('#') else f"#{order_name}"
                search_type = f"name:{order_name}"
                query_str = f'orders(first: 1, query: "{search_type}")'
            else:
                search_type = f"email:{email}"
                query_str = f'orders(first: 10, sortKey: UPDATED_AT, reverse: true, query: "{search_type}")'
            
            logger.info(f"Fetching orders by {'orderName' if order_name else 'email'}: {search_type}")
            
            query = {
                "query": f"""{{
                    {query_str} {{
                        edges {{
                            node {{
                                id
                                name
                                createdAt
                                discountCode
                                totalPriceSet {{ presentmentMoney {{ amount }} }}
                                customer {{ id email }}
                                lineItems(first: 10) {{
                                    edges {{
                                        node {{
                                            product {{
                                                id title descriptionHtml tags
                                                variants(first: 10) {{
                                                    edges {{ 
                                                        node {{ 
                                                            id title inventoryItem {{id}} inventoryQuantity 
                                                        }} 
                                                    }}
                                                }}
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}"""
            }
            
            response_data = self.shopify_service._make_request(query)
            response = {"success": response_data is not None, "data": response_data}
            
            if not response["success"]:
                return {"success": False, "message": "Shopify fetch order API call failed."}
            
            orders = response["data"]["data"]["orders"]["edges"]
            
            if not orders:
                return {"success": False, "message": "No orders found."}
            
            formatted_orders = []
            for order_edge in orders:
                order = order_edge["node"]
                product = order["lineItems"]["edges"][0]["node"]["product"] if order["lineItems"]["edges"] else None
                
                if not product:
                    continue  # Skip orders with no products
                
                formatted_order = {
                    "orderId": order["id"],
                    "orderName": order["name"],
                    "orderCreatedAt": order["createdAt"],
                    "discountCode": order.get("discountCode"),
                    "totalAmountPaid": float(order["totalPriceSet"]["presentmentMoney"]["amount"]),
                    "customer": {
                        "id": order["customer"]["id"] if order["customer"] else "N/A",
                        "email": order["customer"]["email"] if order["customer"] else "N/A"
                    },
                    "product": {
                        "title": product["title"],
                        "productId": product["id"],
                        "descriptionHtml": product["descriptionHtml"],
                        "tags": product["tags"],
                        "variants": [
                            {
                                "variantId": variant["node"]["id"],
                                "variantName": variant["node"]["title"],
                                "inventory": variant["node"]["inventoryQuantity"],
                                "inventoryItemId": variant["node"]["inventoryItem"]["id"]
                            }
                            for variant in product["variants"]["edges"]
                        ]
                    }
                }
                formatted_orders.append(formatted_order)
            
            result = formatted_orders[0] if order_name else formatted_orders
            return {"success": True, "data": result}
            
        except Exception as e:
            logger.error(f"Error fetching order details: {str(e)}")
            return {"success": False, "message": f"Error fetching order details: {str(e)}"}
    
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
            
            response_data = self.shopify_service._make_request(mutation)
            response = {"success": response_data is not None, "data": response_data}
            
            if not response["success"]:
                return {"success": False, "message": "Failed to cancel order"}
            
            data = response["data"]["data"]["orderCancel"]
            
            if data.get("userErrors") or data.get("orderCancelUserErrors"):
                errors = data.get("userErrors", []) + data.get("orderCancelUserErrors", [])
                return {"success": False, "message": f"Order cancellation failed: {errors}"}
            
            return {"success": True, "data": data}
            
        except Exception as e:
            logger.error(f"Error canceling order: {str(e)}")
            return {"success": False, "message": f"Error canceling order: {str(e)}"}
    
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
            
            response_data = self.shopify_service._make_request(order_details_query)
            response = {"success": response_data is not None, "data": response_data}
            
            if not response["success"]:
                return {"success": False, "message": "Failed to fetch order transactions"}
            
            order_data = response["data"]["data"]["order"]
            
            if not order_data.get("transactions"):
                return {"success": False, "message": "No transactions found for this order"}
            
            # Find capture transaction
            capture_transaction = None
            for transaction in order_data["transactions"]:
                if transaction["kind"] == "CAPTURE":
                    capture_transaction = transaction
                    break
            
            if not capture_transaction:
                return {"success": False, "message": "No capture transaction found for refund"}
            
            gateway = capture_transaction["gateway"]
            parent_transaction_id = (
                capture_transaction["parentTransaction"]["id"] 
                if capture_transaction.get("parentTransaction") 
                else capture_transaction["id"]
            )
            
            # Step 2: Create refund
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
                        "note": f"Refund issued via API workflow for ${refund_amount:.2f}",
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
            
            refund_response_data = self.shopify_service._make_request(refund_mutation)
            refund_response = {"success": refund_response_data is not None, "data": refund_response_data}
            
            if not refund_response["success"]:
                return {"success": False, "message": "Failed to create refund"}
            
            refund_data = refund_response["data"]["data"]["refundCreate"]
            
            if refund_data.get("userErrors"):
                return {
                    "success": False, 
                    "message": f"Refund creation failed: {refund_data['userErrors']}"
                }
            
            return {
                "success": True, 
                "data": {
                    "refundId": refund_data["refund"]["id"],
                    "amount": refund_data["refund"]["totalRefundedSet"]["presentmentMoney"]["amount"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating refund: {str(e)}")
            return {"success": False, "message": f"Error creating refund: {str(e)}"}
    
    def create_store_credit(self, order_id: str, credit_amount: float) -> Dict[str, Any]:
        """
        Create store credit for a Shopify order
        Based on createShopifyStoreCredit from ShopifyUtils.gs
        """
        try:
            store_credit_mutation = {
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
                        "note": f"Store Credit issued via API workflow for ${credit_amount:.2f}",
                        "refundMethods": [{
                            "storeCreditRefund": {
                                "amount": {
                                    "amount": str(credit_amount),
                                    "currencyCode": "USD"
                                }
                            }
                        }]
                    }
                }
            }
            
            response_data = self.shopify_service._make_request(store_credit_mutation)
            response = {"success": response_data is not None, "data": response_data}
            
            if not response["success"]:
                return {"success": False, "message": "Failed to create store credit"}
            
            credit_data = response["data"]["data"]["refundCreate"]
            
            if credit_data.get("userErrors"):
                return {
                    "success": False, 
                    "message": f"Store credit creation failed: {credit_data['userErrors']}"
                }
            
            return {
                "success": True, 
                "data": {
                    "creditId": credit_data["refund"]["id"],
                    "amount": credit_data["refund"]["totalRefundedSet"]["presentmentMoney"]["amount"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating store credit: {str(e)}")
            return {"success": False, "message": f"Error creating store credit: {str(e)}"}
    
    def restock_inventory(self, inventory_item_id: str, quantity: int = 1) -> Dict[str, Any]:
        """
        Restock inventory for a product variant
        Based on restockInventory from restockInventory.gs
        """
        try:
            mutation = {
                "query": """
                    mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
                        inventoryAdjustQuantities(input: $input) {
                            userErrors { field message }
                            inventoryAdjustmentGroup {
                                createdAt
                                reason
                                changes { name delta }
                            }
                        }
                    }
                """,
                "variables": {
                    "input": {
                        "reason": "movement_created",
                        "name": "available",
                        "changes": [
                            {
                                "delta": quantity,
                                "inventoryItemId": inventory_item_id,
                                "locationId": f"gid://shopify/Location/{self.location_id}"
                            }
                        ]
                    }
                }
            }
            
            response_data = self.shopify_service._make_request(mutation)
            response = {"success": response_data is not None, "data": response_data}
            
            if not response["success"]:
                return {"success": False, "message": "Failed to restock inventory"}
            
            inventory_data = response["data"]["data"]["inventoryAdjustQuantities"]
            
            if inventory_data.get("userErrors"):
                return {
                    "success": False, 
                    "message": f"Inventory restock failed: {inventory_data['userErrors']}"
                }
            
            return {"success": True, "data": inventory_data["inventoryAdjustmentGroup"]}
            
        except Exception as e:
            logger.error(f"Error restocking inventory: {str(e)}")
            return {"success": False, "message": f"Error restocking inventory: {str(e)}"}
    
    def calculate_refund_due(self, order_data: Dict[str, Any], refund_type: str = "refund") -> Dict[str, Any]:
        """
        Calculate refund amount based on timing and season dates
        Based on getRefundDue from getRefundDue.gs
        """
        try:
            product = order_data.get("product", {})
            description_html = product.get("descriptionHtml", "")
            total_amount_paid = order_data.get("totalAmountPaid", 0)
            
            if total_amount_paid == 0:
                return {
                    "success": True,
                    "refund_amount": 0,
                    "message": "No payment was made for this order"
                }
            
            # Extract season dates from product description
            season_start_date, off_dates = extract_season_dates(description_html)
            
            if not season_start_date:
                return {
                    "success": False,
                    "message": "Could not extract season dates from product description"
                }
            
            # Calculate refund amount based on timing
            refund_amount, refund_text = calculate_refund_amount(
                season_start_date, off_dates, total_amount_paid, refund_type
            )
            
            return {
                "success": True,
                "refund_amount": refund_amount,
                "refund_text": refund_text,
                "season_start_date": season_start_date,
                "off_dates": off_dates
            }
            
        except Exception as e:
            logger.error(f"Error calculating refund due: {str(e)}")
            return {"success": False, "message": f"Error calculating refund due: {str(e)}"}
    
    def get_inventory_summary(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get inventory summary for different registration types
        Based on the inventory logic from approveRefundRequest.gs
        """
        try:
            product = order_data.get("product", {})
            variants = product.get("variants", [])
            
            inventory_order = ['veteran', 'early', 'open', 'waitlist']
            
            inventory_list = {}
            
            for variant in variants:
                variant_name = variant["variantName"].lower()
                
                if 'veteran' in variant_name:
                    inventory_list['veteran'] = {
                        "name": "Veteran Registration",
                        "variantId": variant["variantId"],
                        "inventory": variant["inventory"],
                        "inventoryItemId": variant["inventoryItemId"]
                    }
                elif any(term in variant_name for term in ['wtnb', 'trans']):
                    inventory_list['early'] = {
                        "name": "Early Registration",
                        "variantId": variant["variantId"],
                        "inventory": variant["inventory"],
                        "inventoryItemId": variant["inventoryItemId"]
                    }
                elif 'open' in variant_name:
                    inventory_list['open'] = {
                        "name": "Open Registration",
                        "variantId": variant["variantId"],
                        "inventory": variant["inventory"],
                        "inventoryItemId": variant["inventoryItemId"]
                    }
                elif 'waitlist' in variant_name:
                    inventory_list['waitlist'] = {
                        "name": "Coming Off Waitlist Registration",
                        "variantId": variant["variantId"],
                        "inventory": variant["inventory"],
                        "inventoryItemId": variant["inventoryItemId"]
                    }
            
            return {
                "success": True,
                "inventory_order": inventory_order,
                "inventory_list": inventory_list
            }
            
        except Exception as e:
            logger.error(f"Error getting inventory summary: {str(e)}")
            return {"success": False, "message": f"Error getting inventory summary: {str(e)}"} 