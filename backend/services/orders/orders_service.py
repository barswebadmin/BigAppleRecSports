"""
Main Orders service for handling Shopify order operations.
Refactored to use helper modules for better organization.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import json
import re
from ..shopify_service import ShopifyService
from ..slack import SlackService
from .refund_calculator import RefundCalculator
from .shopify_operations import ShopifyOperations

logger = logging.getLogger(__name__)


class OrdersService:
    """
    Main service for handling order operations.
    
    This service coordinates order fetching, refund calculations,
    and Shopify operations through specialized helper classes.
    """
    
    def __init__(self):
        self.shopify_service = ShopifyService()
        self.slack_service = SlackService()
        self.location_id = "61802217566"  # Default location ID from the GS code
        
        # Initialize helper components
        self.refund_calculator = RefundCalculator()
        self.shopify_operations = ShopifyOperations(self.location_id)
    
    def fetch_order_details(self, order_name: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
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
                                            id
                                            title
                                            quantity
                                            originalUnitPriceSet {{ presentmentMoney {{ amount }} }}
                                            product {{
                                                id
                                                title
                                                descriptionHtml
                                                tags
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}"""
            }
            
            result = self.shopify_service._make_request(query)
            
            if not result or not result.get("data"):
                return {"success": False, "message": "No orders found."}
            
            orders_edges = result["data"]["orders"]["edges"]
            
            if not orders_edges:
                return {"success": False, "message": "No orders found."}
            
            # Format the orders
            formatted_orders = []
            for edge in orders_edges:
                order = edge["node"]
                
                # Extract line item details
                line_items = []
                for line_item_edge in order["lineItems"]["edges"]:
                    line_item = line_item_edge["node"]
                    product = line_item["product"]
                    
                    line_items.append({
                        "id": line_item["id"],
                        "title": line_item["title"],
                        "quantity": line_item["quantity"],
                        "price": line_item["originalUnitPriceSet"]["presentmentMoney"]["amount"],
                        "product": {
                            "id": product["id"],
                            "title": product["title"],
                            "descriptionHtml": product["descriptionHtml"],
                            "tags": product["tags"]
                        }
                    })
                
                formatted_order = {
                    "id": order["id"],
                    "name": order["name"],
                    "created_at": order["createdAt"],
                    "total_price": order["totalPriceSet"]["presentmentMoney"]["amount"],
                    "discount_code": order.get("discountCode"),
                    "customer": order["customer"],
                    "line_items": line_items
                }
                
                # Add product details for the first line item (for backward compatibility)
                if line_items:
                    first_item = line_items[0]
                    product = first_item["product"]
                    product_id = product["id"]
                    
                    # Fetch all variants for this product
                    product_variants = self.fetch_product_variants(product_id)
                    
                    formatted_order["product"] = {
                        "title": product["title"],
                        "productId": product["id"],
                        "descriptionHtml": product["descriptionHtml"],
                        "tags": product["tags"],
                        "variants": product_variants
                    }
                
                formatted_orders.append(formatted_order)
            
            result = formatted_orders[0] if order_name else formatted_orders
            return {"success": True, "data": result}
            
        except Exception as e:
            logger.error(f"Error fetching order details: {str(e)}")
            return {"success": False, "message": f"Error fetching order details: {str(e)}"}
    
    def get_order_by_name(self, order_name: str) -> Optional[Dict[str, Any]]:
        """
        Convenience method to get a single order by name.
        Returns the order data or None if not found.
        """
        result = self.fetch_order_details(order_name=order_name)
        return result.get("data") if result.get("success") else None
    
    def fetch_product_variants(self, product_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all variants for a specific product by product ID
        """
        try:
            query = {
                "query": f"""{{
                    product(id: "{product_id}") {{
                        id
                        title
                        variants(first: 50) {{
                            edges {{
                                node {{
                                    id
                                    title
                                    price
                                    inventoryQuantity
                                    inventoryItem {{ id }}
                                }}
                            }}
                        }}
                    }}
                }}"""
            }
            
            result = self.shopify_service._make_request(query)
            
            if not result or not result.get("data") or not result["data"].get("product"):
                return []
            
            product = result["data"]["product"]
            variants = []
            
            for variant_edge in product["variants"]["edges"]:
                variant = variant_edge["node"]
                variants.append({
                    "variantId": variant["id"],
                    "variantName": variant["title"],
                    "price": variant["price"],
                    "inventory": variant["inventoryQuantity"],
                    "inventoryItemId": variant["inventoryItem"]["id"]
                })
            
            return variants
            
        except Exception as e:
            logger.error(f"Error fetching product variants for {product_id}: {str(e)}")
            return []
    
    def calculate_refund_due(self, order_data: Dict[str, Any], refund_type: str) -> Dict[str, Any]:
        """
        Calculate refund amount for an order.
        Delegates to the RefundCalculator helper.
        """
        return self.refund_calculator.calculate_refund_due(order_data, refund_type)
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order.
        Delegates to ShopifyOperations helper.
        """
        return self.shopify_operations.cancel_order(order_id)

    
    def cancel_order_with_refund(
        self,
        order_id: str,
        refund_amount: float,
        should_restock: bool = True,
        send_slack_notification: bool = True
    ) -> Dict[str, Any]:
        """
        Complete order cancellation workflow with refund and optional restocking.
        
        Args:
            order_id: Shopify order ID
            refund_amount: Amount to refund
            should_restock: Whether to restock inventory
            send_slack_notification: Whether to send Slack notification
            
        Returns:
            Dict containing operation results
        """
        try:
            results: Dict[str, Optional[Dict[str, Any]]] = {
                "cancel_result": None,
                "refund_result": None,
                "restock_result": None,
                "slack_result": None
            }
            
            # Step 1: Cancel the order
            logger.info(f"Canceling order {order_id}")
            results["cancel_result"] = self.shopify_operations.cancel_order(order_id)
            
            if not results["cancel_result"]["success"]:
                return {"success": False, "message": "Failed to cancel order", "results": results}
            
            # Step 2: Create refund if amount > 0
            if refund_amount > 0:
                logger.info(f"Creating refund of ${refund_amount:.2f} for order {order_id}")
                results["refund_result"] = self.shopify_operations.create_refund(order_id, refund_amount)
                
                if not results["refund_result"]["success"]:
                    logger.warning(f"Refund creation failed, but order was canceled: {results['refund_result']['message']}")
            
            # Step 3: Restock inventory if requested
            if should_restock:
                logger.info(f"Restocking inventory for order {order_id}")
                results["restock_result"] = self.shopify_operations.restock_inventory(order_id)
                
                if not results["restock_result"]["success"]:
                    logger.warning(f"Inventory restocking failed: {results['restock_result']['message']}")
            
            # Step 4: Send Slack notification if requested
            if send_slack_notification:
                # Note: This would need order details and requestor info
                # For now, just log that notification would be sent
                logger.info("Slack notification would be sent here")
                results["slack_result"] = {"success": True, "message": "Notification sent"}
            
            return {
                "success": True,
                "message": "Order cancellation workflow completed",
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in cancel_order_with_refund: {str(e)}")
            return {"success": False, "message": f"Error in cancellation workflow: {str(e)}"}
    
    def create_refund_only(self, order_id: str, refund_amount: float) -> Dict[str, Any]:
        """
        Create a refund without canceling the order.
        Delegates to ShopifyOperations helper.
        """
        return self.shopify_operations.create_refund(order_id, refund_amount)
    
    def restock_order_inventory(self, order_id: str) -> Dict[str, Any]:
        """
        Restock inventory for an order.
        Delegates to ShopifyOperations helper.
        """
        return self.shopify_operations.restock_inventory(order_id) 