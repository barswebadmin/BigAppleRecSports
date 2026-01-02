"""
Shared utilities for bars-scripts.
Standalone implementations that don't depend on project code.
"""

import os
import time
import requests
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


def load_environment(env: str = "production"):
    """Load environment variables based on specified environment."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    
    if env:
        os.environ["ENVIRONMENT"] = env.lower()


def get_shopify_config(environment: str) -> Dict[str, Any]:
    """Get Shopify configuration based on environment."""
    env = environment.lower()
    
    if env in ["staging", "production"]:
        store_id = os.getenv("SHOPIFY_STORE_ID") or os.getenv("SHOPIFY_STORE")
        # Try multiple token variable names for flexibility
        token = (
            os.getenv("SHOPIFY_TOKEN_ADMIN") or 
            os.getenv("SHOPIFY_TOKEN") or
            os.getenv("SHOPIFY_TOKEN_WRITE_ORDERS_READ_PRODUCTS_CUSTOMERS")
        )
    else:
        store_id = os.getenv("SHOPIFY_DEV_STORE_ID") or os.getenv("SHOPIFY_DEV_STORE")
        token = os.getenv("SHOPIFY_DEV_TOKEN")
    
    if not store_id or not token:
        raise RuntimeError(f"Missing Shopify credentials for environment: {env}")
    
    return {
        "store_id": store_id,
        "token": token,
        "graphql_url": f"https://{store_id}.myshopify.com/admin/api/2025-07/graphql.json",
        "headers": {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": token,
        }
    }


def make_graphql_request(payload: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make a GraphQL request to Shopify API with proper SSL handling.
    
    Args:
        payload: GraphQL query/mutation payload with 'query' and optional 'variables'
        config: Shopify API configuration from get_shopify_config()
        
    Returns:
        Dict containing the JSON response from Shopify
    """
    ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
    verify_ssl = ssl_cert_file if os.path.exists(ssl_cert_file) else True
    
    try:
        response = requests.post(
            config["graphql_url"],
            json=payload,
            headers=config["headers"],
            timeout=30,
            verify=verify_ssl
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def fetch_order(order_number: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch order details from Shopify API."""
    order_num = order_number.strip().lstrip('#')
    
    query = """
    query FetchOrder($q: String!) {
        orders(first: 1, query: $q) {
            edges {
                node {
                    id
                    name
                    email
                    createdAt
                    displayFinancialStatus
                    displayFulfillmentStatus
                    totalPriceSet {
                        shopMoney {
                            amount
                            currencyCode
                        }
                    }
                    customer {
                        id
                        email
                        firstName
                        lastName
                    }
                    cancelledAt
                    cancelReason
                    refunds {
                        id
                        createdAt
                        note
                        totalRefundedSet {
                            presentmentMoney {
                                amount
                                currencyCode
                            }
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        refundLineItems(first: 50) {
                            edges {
                                node {
                                    quantity
                                    restockType
                                    lineItem {
                                        id
                                        name
                                        title
                                    }
                                }
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
                    }
                    transactions {
                        id
                        kind
                        gateway
                        status
                        amount
                        parentTransaction {
                            id
                        }
                    }
                    lineItems(first: 50) {
                        edges {
                            node {
                                id
                                name
                                title
                                quantity
                                product {
                                    title
                                }
                                variant {
                                    id
                                    title
                                    price
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    payload = {
        "query": query,
        "variables": {"q": f"name:#{order_num}"}
    }
    
    ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
    verify_ssl = ssl_cert_file if os.path.exists(ssl_cert_file) else True
    
    try:
        response = requests.post(
            config["graphql_url"],
            json=payload,
            headers=config["headers"],
            timeout=30,
            verify=verify_ssl
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def cancel_order(order_id: str, config: Dict[str, Any], reason: str = "CUSTOMER") -> Dict[str, Any]:
    """Cancel an order using Shopify's orderCancel mutation."""
    mutation = """
    mutation orderCancel($notifyCustomer: Boolean, $orderId: ID!, $reason: OrderCancelReason!, $refund: Boolean!, $restock: Boolean!, $staffNote: String) {
        orderCancel(
            notifyCustomer: $notifyCustomer, 
            orderId: $orderId, 
            reason: $reason, 
            refund: $refund, 
            restock: $restock, 
            staffNote: $staffNote
        ) {
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
    """
    
    payload = {
        "query": mutation,
        "variables": {
            "notifyCustomer": False,
            "orderId": order_id,
            "reason": reason,
            "refund": False,
            "restock": False,
            "staffNote": "Cancelled via cancel_order script"
        }
    }
    
    ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
    verify_ssl = ssl_cert_file if os.path.exists(ssl_cert_file) else True
    
    try:
        response = requests.post(
            config["graphql_url"],
            json=payload,
            headers=config["headers"],
            timeout=30,
            verify=verify_ssl
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def create_refund(
    order_id: str,
    refund_amount: float,
    refund_type: str,
    transactions: list,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a refund using Shopify's refundCreate mutation."""
    mutation = """
    mutation CreateRefund($input: RefundInput!) {
        refundCreate(input: $input) {
            refund {
                id
                createdAt
                note
                totalRefundedSet {
                    shopMoney {
                        amount
                        currencyCode
                    }
                    presentmentMoney {
                        amount
                        currencyCode
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
        refund_input["note"] = f"Store Credit issued for ${refund_amount:.2f}"
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
        capture_transaction = next(
            (t for t in transactions if t.get("kind") in ["CAPTURE", "SALE"] and t.get("status") == "SUCCESS"), 
            None
        )
        
        if not capture_transaction:
            return {"success": False, "message": "No successful capture transaction found for refund"}
        
        gateway = capture_transaction.get("gateway", "shopify_payments")
        parent_trans = capture_transaction.get("parentTransaction")
        if parent_trans and parent_trans.get("id"):
            parent_transaction_id = parent_trans["id"]
        else:
            parent_transaction_id = capture_transaction["id"]
        
        refund_input["note"] = f"Refund issued for ${refund_amount:.2f}"
        refund_input["transactions"] = [
            {
                "orderId": order_id,
                "gateway": gateway,
                "kind": "REFUND",
                "amount": str(refund_amount),
                "parentId": parent_transaction_id
            }
        ]
    
    payload = {
        "query": mutation,
        "variables": {"input": refund_input}
    }
    
    ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
    verify_ssl = ssl_cert_file if os.path.exists(ssl_cert_file) else True
    
    def make_refund_request() -> Dict[str, Any]:
        try:
            response = requests.post(
                config["graphql_url"],
                json=payload,
                headers=config["headers"],
                timeout=30,
                verify=verify_ssl
            )
            response.raise_for_status()
            result = response.json()
            
            if "errors" in result:
                error_messages = [err.get("message", str(err)) for err in result["errors"]]
                return {"success": False, "message": error_messages}
            
            mutation_data = result.get('data', {}).get('refundCreate', {})
            user_errors = mutation_data.get('userErrors', [])
            
            if user_errors:
                error_messages = [f"{err.get('field', '')}: {err.get('message', 'Unknown error')}" for err in user_errors]
                return {"success": False, "message": error_messages}
            
            refund_data = mutation_data.get('refund', {})
            if not refund_data:
                return {"success": False, "message": "Refund creation returned no refund data"}
            
            return {"success": True, "data": refund_data}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    # Simple retry logic with exponential backoff
    max_retries = 3
    base_delay = 1.0
    backoff_factor = 2.0
    last_error: Dict[str, Any] = {"success": False, "error": "Unknown error"}
    
    for attempt in range(max_retries + 1):
        result = make_refund_request()
        if result.get("success") is not False:
            return result
        last_error = result
        if attempt < max_retries:
            delay = base_delay * (backoff_factor ** attempt)
            time.sleep(delay)
    
    return last_error

