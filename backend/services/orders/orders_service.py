"""
Main Orders service for handling Shopify order operations.
Refactored to use helper modules for better organization.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from ..shopify import ShopifyService
from .refund_calculator import RefundCalculator

logger = logging.getLogger(__name__)


class OrdersService:
    """
    Main service for handling order operations.

    This service coordinates order fetching, refund calculations,
    and Shopify operations through specialized helper classes.
    """

    def __init__(self):
        self.shopify_service = ShopifyService()

        # Initialize helper components
        self.refund_calculator = RefundCalculator()

    def fetch_order_details_by_email_or_order_name(
        self, order_name: Optional[str] = None, email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch order details from Shopify by order name or email
        Based on fetchShopifyOrderDetails from ShopifyUtils.gs
        """
        try:
            if not order_name and not email:
                return {
                    "success": False,
                    "message": "Must provide either orderName or email.",
                }

            # Normalize order name
            if order_name:
                order_name = (
                    order_name if order_name.startswith("#") else f"#{order_name}"
                )
                search_type = f"name:{order_name}"
                query_str = f'orders(first: 1, query: "{search_type}")'
            else:
                search_type = f"email:{email}"
                query_str = f'orders(first: 10, sortKey: UPDATED_AT, reverse: true, query: "{search_type}")'

            logger.info(
                f"Fetching orders by {'orderName' if order_name else 'email'}: {search_type}"
            )

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

            # DEBUG: Log the exact query being sent
            logger.info("🔍 === SHOPIFY ORDER SEARCH DEBUG ===")
            logger.info("📤 Query being sent to Shopify:")
            logger.info(f"   Search type: {search_type}")
            logger.info(f"   GraphQL query: {query_str}")
            logger.info(f"   Full query: {query}")

            result = self.shopify_service._make_shopify_request(query)

            # DEBUG: Log the raw response
            logger.info("📥 Raw Shopify response:")
            logger.info(f"   Response type: {type(result)}")
            logger.info(f"   Response: {result}")

            # Check for connection/network errors (result is None)
            if result is None:
                logger.error("🚨 Network connection to Shopify failed")
                return {
                    "success": False,
                    "message": "Unable to connect to Shopify. Please try again later.",
                    "error_type": "connection_error",
                }

            # Check for Shopify API errors (error dict returned)
            if isinstance(result, dict) and "error" in result:
                error_type = result["error"]
                status_code = result.get("status_code", "unknown")

                logger.error(f"🚨 Shopify API error ({status_code}): {error_type}")

                if error_type == "authentication_error":
                    return {
                        "success": False,
                        "message": "Shopify authentication failed. Please contact support.",
                        "error_type": "config_error",
                    }
                elif error_type == "store_not_found":
                    return {
                        "success": False,
                        "message": "Shopify store configuration error. Please contact support.",
                        "error_type": "config_error",
                    }
                elif error_type == "server_error":
                    return {
                        "success": False,
                        "message": "Shopify is temporarily unavailable. Please try again later.",
                        "error_type": "server_error",
                    }
                else:
                    return {
                        "success": False,
                        "message": "Unable to connect to Shopify. Please try again later.",
                        "error_type": "api_error",
                    }

            # Check for empty/invalid response data
            if not result.get("data"):
                logger.error(f"❌ Invalid or empty data in Shopify response: {result}")
                return {
                    "success": False,
                    "message": "Unable to connect to Shopify. Please try again later.",
                    "error_type": "api_error",
                }

            orders_edges = result["data"]["orders"]["edges"]

            # DEBUG: Log what orders were found
            logger.info(f"📋 Orders found: {len(orders_edges)}")
            if orders_edges:
                for i, edge in enumerate(orders_edges):
                    order = edge["node"]
                    logger.info(
                        f"   Order {i+1}: name='{order.get('name')}', id='{order.get('id')}', createdAt='{order.get('createdAt')}'"
                    )

            if not orders_edges:
                logger.error(f"❌ No orders found in edges: {orders_edges}")
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

                    line_items.append(
                        {
                            "id": line_item["id"],
                            "title": line_item["title"],
                            "quantity": line_item["quantity"],
                            "price": line_item["originalUnitPriceSet"][
                                "presentmentMoney"
                            ]["amount"],
                            "product": {
                                "id": product["id"],
                                "title": product["title"],
                                "descriptionHtml": product["descriptionHtml"],
                                "tags": product["tags"],
                            },
                        }
                    )

                formatted_order = {
                    "id": order["id"],
                    "name": order["name"],
                    "created_at": order["createdAt"],
                    "total_price": order["totalPriceSet"]["presentmentMoney"]["amount"],
                    "discount_code": order.get("discountCode"),
                    "customer": order["customer"],
                    "line_items": line_items,
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
                        "variants": product_variants,
                    }

                formatted_orders.append(formatted_order)

            result = formatted_orders[0] if order_name else formatted_orders
            return {"success": True, "data": result}

        except Exception as e:
            logger.error(f"Error fetching order details: {str(e)}")
            return {
                "success": False,
                "message": f"Error fetching order details: {str(e)}",
            }

    def get_order_by_name(self, order_name: str) -> Optional[Dict[str, Any]]:
        """
        Convenience method to get a single order by name.
        Returns the order data or None if not found.
        """
        result = self.fetch_order_details_by_email_or_order_name(order_name=order_name)
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

            result = self.shopify_service._make_shopify_request(query)

            if (
                not result
                or not result.get("data")
                or not result["data"].get("product")
            ):
                return []

            product = result["data"]["product"]
            variants = []

            for variant_edge in product["variants"]["edges"]:
                variant = variant_edge["node"]
                variants.append(
                    {
                        "variantId": variant["id"],
                        "variantName": variant["title"],
                        "price": variant["price"],
                        "inventory": variant["inventoryQuantity"],
                        "inventoryItemId": variant["inventoryItem"]["id"],
                    }
                )

            return variants

        except Exception as e:
            logger.error(f"Error fetching product variants for {product_id}: {str(e)}")
            return []

    def calculate_refund_due(
        self,
        order_data: Dict[str, Any],
        refund_type: str,
        request_submitted_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculate refund amount for an order.
        Delegates to the RefundCalculator helper.
        """
        return self.refund_calculator.calculate_refund_due(
            order_data, refund_type, request_submitted_at
        )

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order.
        Delegates to ShopifyOperations helper.
        """
        return self.shopify_service.cancel_order(order_id)

    def create_refund_or_credit(
        self, order_id: str, amount: float, refund_type: str
    ) -> Dict[str, Any]:
        """
        Create either a refund or store credit based on refund_type.
        Delegates to ShopifyOperations helper.
        """
        return self.shopify_service.create_refund(order_id, amount, refund_type)

    def check_existing_refunds(self, order_id: str) -> Dict[str, Any]:
        """
        Check for existing refunds on an order.
        Returns structured data about any refunds found.
        """
        try:
            logger.info(f"Checking for existing refunds on order: {order_id}")

            # Prepare GraphQL query for refunds
            query = {
                "query": """
                    query getOrderRefunds($id: ID!) {
                        order(id: $id) {
                            id
                            name
                            refunds {
                                id
                                createdAt
                                updatedAt
                                note
                                legacyResourceId
                                totalRefundedSet {
                                    presentmentMoney {
                                        amount
                                        currencyCode
                                    }
                                }
                                transactions(first: 10) {
                                    edges {
                                        node {
                                            id
                                            kind
                                            status
                                            amount
                                            gateway
                                            createdAt
                                        }
                                    }
                                }
                                refundLineItems(first: 10) {
                                    edges {
                                        node {
                                            id
                                            quantity
                                            lineItem {
                                                id
                                                title
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                """,
                "variables": {"id": order_id},
            }

            response = self.shopify_service._make_shopify_request(query=query)

            if not response or "data" not in response or not response["data"]["order"]:
                return {
                    "success": False,
                    "message": "Failed to check existing refunds or order not found",
                }

            order_data = response["data"]["order"]

            # Handle both GraphQL response format and test data format
            refunds_data = order_data.get("refunds", [])
            if isinstance(refunds_data, dict) and "edges" in refunds_data:
                # GraphQL format: { edges: [...] }
                refunds_edges = refunds_data["edges"]
            elif isinstance(refunds_data, list):
                # Test data format: [...] (direct list)
                refunds_edges = [{"node": refund} for refund in refunds_data]
            else:
                refunds_edges = []

            processed_refunds = []
            total_amount = 0.0
            pending_refunds = 0
            resolved_refunds = 0
            pending_amount = 0.0
            resolved_amount = 0.0

            for edge in refunds_edges:
                refund = edge["node"]

                # Calculate transaction amounts and determine status
                transactions_edges = refund.get("transactions", {}).get("edges", [])
                if isinstance(refund.get("transactions"), list):
                    # Handle test data format where transactions is direct list
                    transactions_edges = [
                        {"node": t} for t in refund.get("transactions", [])
                    ]

                refund_amount = 0.0
                refund_status = "completed"  # Default to completed

                transactions = []
                for transaction_edge in transactions_edges:
                    transaction = transaction_edge["node"]
                    amount = float(transaction.get("amount", 0))
                    status = transaction.get("status", "SUCCESS")

                    # Determine overall refund status based on transactions
                    if status == "PENDING":
                        refund_status = "pending"

                    refund_amount += amount
                    transactions.append(
                        {
                            "id": transaction.get("id"),
                            "kind": transaction.get("kind"),
                            "status": status,
                            "amount": transaction.get("amount"),
                            "gateway": transaction.get("gateway"),
                            "created_at": transaction.get("createdAt"),
                        }
                    )

                # If no transactions, check totalRefundedSet
                if refund_amount == 0.0:
                    total_refunded_set = refund.get("totalRefundedSet", {})
                    if total_refunded_set:
                        presentment_money = total_refunded_set.get(
                            "presentmentMoney", {}
                        )
                        refund_amount = float(presentment_money.get("amount", 0))

                # Process line items
                line_items = []
                line_items_edges = refund.get("refundLineItems", {}).get("edges", [])
                for line_item_edge in line_items_edges:
                    line_item_node = line_item_edge["node"]
                    line_item = line_item_node.get("lineItem", {})
                    line_items.append(
                        {
                            "id": line_item.get("id"),
                            "title": line_item.get("title"),
                            "quantity": line_item_node.get("quantity"),
                        }
                    )

                # Count pending vs resolved
                if refund_status == "pending":
                    pending_refunds += 1
                    pending_amount += refund_amount
                else:
                    resolved_refunds += 1
                    resolved_amount += refund_amount

                total_amount += refund_amount

                # Create status display
                status_display = f"${refund_amount:.2f} ({'Pending' if refund_status == 'pending' else 'Completed'})"

                processed_refunds.append(
                    {
                        "id": refund.get("id"),
                        "total_refunded": str(refund_amount),
                        "amount": refund_amount,
                        "status": refund_status,
                        "status_display": status_display,
                        "pending_amount": refund_amount
                        if refund_status == "pending"
                        else 0.0,
                        "completed_amount": refund_amount
                        if refund_status == "completed"
                        else 0.0,
                        "currency": refund.get("totalRefundedSet", {})
                        .get("presentmentMoney", {})
                        .get("currencyCode", "USD"),
                        "created_at": refund.get("createdAt"),
                        "updated_at": refund.get("updatedAt"),
                        "note": refund.get("note", ""),
                        "transactions": transactions,
                        "line_items": line_items,
                    }
                )

            return {
                "success": True,
                "has_refunds": len(processed_refunds) > 0,
                "total_refunds": len(processed_refunds),
                "pending_refunds": pending_refunds,
                "resolved_refunds": resolved_refunds,
                "pending_amount": pending_amount,
                "resolved_amount": resolved_amount,
                "total_amount": total_amount,
                "order_id": order_data.get("id"),
                "order_name": order_data.get("name"),
                "refunds": processed_refunds,
            }

        except Exception as e:
            logger.error(f"Error checking existing refunds for order {order_id}: {e}")
            return {
                "success": False,
                "message": f"Error checking existing refunds: {str(e)}",
            }
