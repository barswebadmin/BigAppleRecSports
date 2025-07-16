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
    
    def get_enhanced_order_details(self, order_name: str, email: Optional[str] = None) -> Dict[str, Any]:
        """
        Get enhanced order details with refund calculations, inventory summary, and admin URLs.
        Includes email fallback if order not found by name.
        """
        try:
            # Try to fetch by order number first
            result = self.fetch_order_details(order_name=order_name)
            
            # If order not found by number and email provided, try by email
            if not result["success"] and email:
                logger.info(f"Order {order_name} not found, trying by email: {email}")
                result = self.fetch_order_details(email=email)
            
            if not result["success"]:
                return result
            
            order_data = result["data"]
            
            # Add calculated refund information
            refund_calculation = self.calculate_refund_due(order_data, "refund")
            credit_calculation = self.calculate_refund_due(order_data, "credit")
            inventory_summary = self.get_inventory_summary(order_data)
            
            # Enhance response with additional calculated data
            enhanced_response = {
                "order": order_data,
                "refund_calculation": refund_calculation,
                "credit_calculation": credit_calculation,
                "inventory_summary": inventory_summary,
                "product_urls": {
                    "shopify_admin": f"https://admin.shopify.com/store/09fe59-3/products/{order_data['product']['productId'].split('/')[-1]}",
                    "order_admin": f"https://admin.shopify.com/store/09fe59-3/orders/{order_data['orderId'].split('/')[-1]}"
                }
            }
            
            return {
                "success": True,
                "data": enhanced_response
            }
            
        except Exception as e:
            logger.error(f"Error getting enhanced order details for {order_name}: {str(e)}")
            return {"success": False, "message": f"Error getting enhanced order details: {str(e)}"}
    
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
        Cancel a Shopify order.
        Delegates to ShopifyOperations helper.
        """
        return self.shopify_operations.cancel_order(order_id)
    
    def cancel_order_with_logging(self, order_id: str, order_number: str, is_debug_mode: bool = False) -> Dict[str, Any]:
        """
        Cancel order with enhanced logging for debugging and monitoring.
        Moved from slack router to maintain separation of concerns.
        """
        try:
            if is_debug_mode:
                logger.info(f"🧪 DEBUG MODE: Would cancel order {order_id} in Shopify")
                logger.info(f"🛑 Mocking cancel for order ID: '{order_id}'")
                cancel_result = {"success": True, "message": "Mock order cancellation in debug mode"}
                logger.info(f"🛑 Mock cancel result: {cancel_result}")
                return cancel_result
            else:
                logger.info(f"🚀 PRODUCTION MODE: Making real order cancellation API call")
                logger.info(f"🛑 Attempting to cancel order ID: '{order_id}'")
                cancel_result = self.shopify_operations.cancel_order(order_id)
                logger.info(f"🛑 Cancel result: {cancel_result}")
                return cancel_result
                
        except Exception as e:
            logger.error(f"Error in cancel_order_with_logging for order {order_number}: {str(e)}")
            return {"success": False, "message": f"Error canceling order: {str(e)}"}
    
    def fetch_order_details_with_logging(self, order_name: str, is_debug_mode: bool = False) -> Dict[str, Any]:
        """
        Fetch order details with enhanced logging for debugging and monitoring.
        Moved from slack router to maintain separation of concerns.
        """
        try:
            if is_debug_mode:
                logger.info(f"🧪 DEBUG MODE: Fetching REAL order details for {order_name}")
            else:
                logger.info(f"🚀 PRODUCTION MODE: Making real API calls")
                logger.info(f"📦 Fetching order details for: {order_name}")
            
            order_result = self.fetch_order_details(order_name=order_name)
            
            if is_debug_mode:
                logger.info(f"📦 Order fetch result: success={order_result.get('success')}, keys={list(order_result.keys())}")
            else:
                logger.info(f"📦 Order fetch result: success={order_result.get('success')}, keys={list(order_result.keys())}")
            
            if not order_result["success"]:
                logger.error(f"Failed to fetch order details for {order_name}: {order_result['message']}")
                if not is_debug_mode:
                    logger.info(f"❌ Order fetch failed: {order_result.get('message', 'Unknown error')}")
                return order_result
            
            shopify_order_data = order_result["data"]
            order_id = shopify_order_data.get("id", "")
            
            if not is_debug_mode:
                logger.info(f"📦 Order data keys: {list(shopify_order_data.keys()) if shopify_order_data else 'None'}")
                logger.info(f"📦 Extracted order ID: '{order_id}'")
            
            return order_result
            
        except Exception as e:
            logger.error(f"Error in fetch_order_details_with_logging for order {order_name}: {str(e)}")
            return {"success": False, "message": f"Error fetching order details: {str(e)}"}
    
    def create_refund_or_credit(self, order_id: str, amount: float, refund_type: str) -> Dict[str, Any]:
        """
        Create either a refund or store credit based on refund_type.
        """
        if refund_type.lower() == "credit":
            return self.create_store_credit(order_id, amount)
        else:
            return self.create_refund_only(order_id, amount)

    def create_refund_only(self, order_id: str, refund_amount: float) -> Dict[str, Any]:
        """
        Create a refund without canceling the order.
        Delegates to ShopifyOperations helper.
        """
        return self.shopify_operations.create_refund(order_id, refund_amount)
    
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
                        "note": f"Store Credit issued via Slack workflow for ${credit_amount:.2f}",
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
            
            if not response_data:
                return {"success": False, "message": "Failed to create store credit - no response from Shopify"}
            
            if "errors" in response_data:
                error_msg = f"GraphQL errors: {response_data['errors']}"
                logger.error(f"Shopify GraphQL errors during store credit creation: {error_msg}")
                return {"success": False, "message": error_msg}
            
            credit_data = response_data.get("data", {}).get("refundCreate", {})
            
            if credit_data.get("userErrors"):
                error_msg = f"Store credit creation failed: {credit_data['userErrors']}"
                logger.error(f"Store credit user errors: {error_msg}")
                return {"success": False, "message": error_msg}
            
            # Success case
            refund_info = credit_data.get("refund", {})
            return {
                "success": True, 
                "data": {
                    "creditId": refund_info.get("id"),
                    "amount": refund_info.get("totalRefundedSet", {}).get("presentmentMoney", {}).get("amount", "0")
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating store credit: {str(e)}")
            return {"success": False, "message": f"Error creating store credit: {str(e)}"}

    def create_refund_or_credit_with_logging(self, order_id: str, refund_amount: float, refund_type: str, order_number: str, is_debug_mode: bool = False) -> Dict[str, Any]:
        """
        Create refund or credit with enhanced logging for debugging and monitoring.
        Moved from slack router to maintain separation of concerns.
        """
        try:
            if is_debug_mode:
                logger.info(f"🧪 DEBUG MODE: Would process refund for order {order_number}")
                logger.info(f"🧪 DEBUG MODE: Would create ${refund_amount:.2f} {refund_type}")
                
                # Mock successful refund result for debug mode
                refund_result = {"success": True, "refund_id": f"mock-refund-{order_number.replace('#', '')}"}
                return refund_result
            else:
                # Production mode - make actual Shopify API call
                logger.info(f"🏭 PRODUCTION MODE: Making real {refund_type} API call")
                refund_result = self.create_refund_or_credit(order_id, refund_amount, refund_type)
                
                # Add detailed logging for production debugging
                if not refund_result["success"]:
                    logger.error(f"🚨 PRODUCTION REFUND FAILED: Order {order_number}, Amount ${refund_amount}, Type: {refund_type}")
                    logger.error(f"🚨 ERROR DETAILS: {refund_result.get('message', 'Unknown error')}")
                else:
                    logger.info(f"✅ PRODUCTION REFUND SUCCESS: Order {order_number}, Amount ${refund_amount}, Type: {refund_type}")
                
                return refund_result
                
        except Exception as e:
            logger.error(f"Error in create_refund_or_credit_with_logging for order {order_number}: {str(e)}")
            return {"success": False, "message": f"Error processing refund: {str(e)}"}

    def restock_order_inventory(self, order_id: str) -> Dict[str, Any]:
        """
        Restock inventory for an order.
        Delegates to ShopifyOperations helper.
        """
        return self.shopify_operations.restock_inventory(order_id)
    
    def get_inventory_summary(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get inventory summary for an order's product variants.
        Returns current inventory levels and availability information.
        """
        try:
            product = order_data.get("product", {})
            variants = product.get("variants", [])
            
            if not variants:
                return {
                    "success": False,
                    "message": "No variants found for inventory summary",
                    "variants": []
                }
            
            inventory_summary = {
                "success": True,
                "product_title": product.get("title", "Unknown Product"),
                "total_variants": len(variants),
                "variants": []
            }
            
            total_available = 0
            for variant in variants:
                variant_info = {
                    "variant_id": variant.get("variantId", ""),
                    "variant_name": variant.get("variantName", "Unknown Variant"),
                    "inventory_quantity": variant.get("inventory", 0),
                    "price": variant.get("price", "0"),
                    "inventory_item_id": variant.get("inventoryItemId", "")
                }
                
                total_available += variant_info["inventory_quantity"]
                inventory_summary["variants"].append(variant_info)
            
            inventory_summary["total_available"] = total_available
            
            return inventory_summary
            
        except Exception as e:
            logger.error(f"Error getting inventory summary: {str(e)}")
            return {
                "success": False,
                "message": f"Error getting inventory summary: {str(e)}",
                "variants": []
            } 