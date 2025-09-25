from typing import Dict, Any, Callable
import logging
import json
from config import config

logger = logging.getLogger(__name__)

def cancel_order(order_id: str, request_func: Callable) -> Dict[str, Any]:
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
            },
        }

        print("\n🔍 === SHOPIFY CANCEL ORDER DEBUG ===")
        print("📤 Sending mutation to Shopify:")
        print(f"   Order ID: {order_id}")
        print(f"   Mutation variables: {mutation['variables']}")
        print(f"   Mutation query (first 200 chars): {mutation['query'][:200]}...")

        response_data = request_func(mutation)

        print("📥 Raw Shopify response:")
        print(f"   Type: {type(response_data)}")
        print(f"   Response: {response_data}")
        print("=== END SHOPIFY CANCEL ORDER DEBUG ===\n")

        if response_data is None:
            return {
                "success": False,
                "message": "Failed to cancel order - no response from Shopify API",
                "raw_response": None,
            }

        if "data" not in response_data:
            # Check for GraphQL errors in response
            if "errors" in response_data:
                return {
                    "success": False,
                    "message": f"Failed to cancel order - GraphQL errors: {response_data['errors']}",
                    "raw_response": response_data,
                }
            return {
                "success": False,
                "message": f"Failed to cancel order - invalid response format. Response: {response_data}",
                "raw_response": response_data,
            }

        if "orderCancel" not in response_data["data"]:
            return {
                "success": False,
                "message": f"Failed to cancel order - missing orderCancel in response. Data keys: {list(response_data['data'].keys())}",
                "raw_response": response_data,
            }

        data = response_data["data"]["orderCancel"]

        if data.get("userErrors") or data.get("orderCancelUserErrors"):
            errors = data.get("userErrors", []) + data.get(
                "orderCancelUserErrors", []
            )
            return {
                "success": False,
                "message": f"Order cancellation failed: {errors}",
                "raw_response": response_data,
                "shopify_errors": errors,
            }

        return {"success": True, "data": data, "raw_response": response_data}

    except Exception as e:
        logger.error(f"Error canceling order: {str(e)}")
        return {
            "success": False,
            "message": f"Error canceling order: {str(e)}",
            "raw_response": "Exception occurred before response",
        }


def get_order_details(order_id: str, request_func: Callable) -> Dict[str, Any]:
    """Get order details from Shopify"""
    query = """
        query getOrderDetails($id: ID!) {
            order(id: $id) {
                id
                transactions {
                    id
                    kind
                    gateway
                    parentTransaction {
                        id
                    }
                }
            }
        }
    """
    variables = {"id": order_id}
    response = request_func({"query": query, "variables": variables})
    print("🔍 === SHOPIFY GET ORDER DETAILS DEBUG ===")
    print(json.dumps(response, indent=2))
    if not response or "data" not in response:
        return {
            "success": False,
            "message": "Failed to fetch order details for refund",
        }
    return response["data"]["order"]

def create_refund(
    order_id: str, refund_amount: float, refund_type: str, request_func: Callable
) -> Dict[str, Any]:
    """Create a refund for a Shopify order"""
    try:
        query = """
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
        """

        refund_input = {
            "notify": True,
            "orderId": order_id,
        }

        if refund_type.lower() == "credit":
            refund_input["note"] = (
                f"Store Credit issued via Slack workflow for ${refund_amount:.2f}"
            )
            refund_input["refundMethods"] = [
                {
                    "storeCreditRefund": {
                        "amount": {
                            "amount": str(refund_amount),
                            "currencyCode": "USD",
                        }
                    }
                }
            ]
        else:
            # Lookup transactions for cash/card refund
            order = get_order_details(order_id, request_func)

            if not order or "transactions" not in order:
                return {
                    "success": False,
                    "message": "Failed to fetch transactions from order details",
                }

            transactions = order["transactions"]
            capture_transaction = next(
                (t for t in transactions if t["kind"] == "CAPTURE"), None
            )

            if not capture_transaction:
                return {
                    "success": False,
                    "message": "No capture transaction found for refund",
                }

            gateway = capture_transaction["gateway"]
            parent_transaction_id = (
                capture_transaction.get("parentTransaction", {}).get("id")
                or capture_transaction["id"]
            )

            refund_input["note"] = (
                f"Refund issued via Slack workflow for ${refund_amount:.2f}"
            )
            refund_input["transactions"] = [
                {
                    "orderId": order_id,
                    "gateway": gateway,
                    "kind": "REFUND",
                    "amount": str(refund_amount),
                    "parentId": parent_transaction_id,
                }
            ]

        mutation = {"query": query, "variables": {"input": refund_input}}

        response_data = request_func(mutation)
        if not response_data or "data" not in response_data:
            return {"success": False, "message": "Failed to create refund"}

        refund_data = response_data["data"].get("refundCreate", {})
        if refund_data.get("userErrors"):
            return {
                "success": False,
                "message": f"Refund creation failed: {refund_data['userErrors']}",
            }

        return {"success": True, "data": refund_data.get("refund")}

    except Exception as e:
        logger.error(f"Error creating {refund_type}: {str(e)}")
        return {
            "success": False,
            "message": f"Error creating {refund_type}: {str(e)}",
        }
