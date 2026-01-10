"""
Shared utilities for bars-scripts.
Standalone implementations that don't depend on project code.
"""

import os
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional, Type, List, Tuple, TypeVar, List, Type, Tuple
from dotenv import load_dotenv

from pydantic import BaseModel


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
            os.getenv("shopify/token.admin") or
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


CUSTOMER_FIELDS = """
    id
    firstName
    lastName
    email
    displayName
    phone
    tags
    numberOfOrders
    createdAt
    updatedAt
    state
    verifiedEmail
    addresses {
        address1
        address2
        city
        province
        zip
        country
    }
    defaultAddress {
        address1
        address2
        city
        province
        zip
        country
    }
    orders(first: 5, sortKey: CREATED_AT, reverse: true) {
        edges {
            node {
                id
                name
                createdAt
            }
        }
    }
"""


PRODUCT_FIELDS = """
    id
    title
    description
    descriptionHtml
    vendor
    handle
    status
    productType
    tags
    createdAt
    updatedAt
    publishedAt
    onlineStoreUrl
    onlineStorePreviewUrl
    totalInventory
    tracksInventory
    featuredImage {
        url
        altText
        width
        height
    }
    images(first: 50) {
        edges {
            node {
                url
                altText
                width
                height
            }
        }
    }
    media(first: 50) {
        edges {
            node {
                ... on MediaImage {
                    image {
                        url
                        altText
                        width
                        height
                    }
                }
                ... on Video {
                    sources {
                        url
                        mimeType
                        format
                        height
                        width
                    }
                    preview {
                        image {
                            url
                            altText
                        }
                    }
                }
                ... on ExternalVideo {
                    host
                    embeddedUrl
                    originUrl
                    preview {
                        image {
                            url
                            altText
                        }
                    }
                }
                ... on Model3d {
                    sources {
                        url
                        mimeType
                        format
                    }
                    preview {
                        image {
                            url
                            altText
                        }
                    }
                }
            }
        }
    }
    options {
        id
        name
        values
    }
    metafields(first: 50) {
        edges {
            node {
                id
                key
                value
                namespace
                type
                description
            }
        }
    }
    collections(first: 50) {
        edges {
            node {
                id
                title
                handle
                description
            }
        }
    }
    seo {
        title
        description
    }
    priceRange {
        minVariantPrice {
            amount
            currencyCode
        }
        maxVariantPrice {
            amount
            currencyCode
        }
    }
    compareAtPriceRange {
        minVariantCompareAtPrice {
            amount
            currencyCode
        }
        maxVariantCompareAtPrice {
            amount
            currencyCode
        }
    }
    giftCardTemplateSuffix
    requiresSellingPlan
    sellingPlanGroups(first: 10) {
        edges {
            node {
                id
                name
                summary
            }
        }
    }
"""


ORDER_FIELDS = f"""
    id
    name
    email
    createdAt
    updatedAt
    phone
    displayFinancialStatus
    displayFulfillmentStatus
    subtotalLineItemsQuantity
    cancelledAt
    cancelReason
    totalPriceSet {{
        shopMoney {{
            amount
            currencyCode
        }}
        presentmentMoney {{
            amount
            currencyCode
        }}
    }}
    discountApplications(first: 10) {{
        edges {{
            node {{
                ... on DiscountCodeApplication {{
                    code
                }}
                ... on ScriptDiscountApplication {{
                    title
                }}
                ... on AutomaticDiscountApplication {{
                    title
                }}
            }}
        }}
    }}
    billingAddress {{
        firstName
        lastName
        address1
        address2
        city
        province
        zip
        country
        phone
    }}
    shippingAddress {{
        firstName
        lastName
        address1
        address2
        city
        province
        zip
        country
        phone
    }}
    customer {{
{CUSTOMER_FIELDS}
    }}
    refunds {{
        id
        createdAt
        note
        totalRefundedSet {{
            presentmentMoney {{
                amount
                currencyCode
            }}
            shopMoney {{
                amount
                currencyCode
            }}
        }}
        refundLineItems(first: 50) {{
            edges {{
                node {{
                    quantity
                    restockType
                    lineItem {{
                        id
                        name
                        title
                    }}
                }}
            }}
        }}
        transactions(first: 10) {{
            edges {{
                node {{
                    id
                    kind
                    status
                    amount
                    gateway
                    createdAt
                }}
            }}
        }}
    }}
    transactions {{
        id
        kind
        gateway
        status
        amount
        createdAt
        parentTransaction {{
            id
        }}
    }}
    lineItems(first: 50) {{
        edges {{
            node {{
                id
                name
                title
                quantity
                fulfillableQuantity
                fulfillmentStatus
                originalUnitPriceSet {{
                    shopMoney {{
                        amount
                        currencyCode
                    }}
                    presentmentMoney {{
                        amount
                        currencyCode
                    }}
                }}
                discountedUnitPriceSet {{
                    shopMoney {{
                        amount
                        currencyCode
                    }}
                    presentmentMoney {{
                        amount
                        currencyCode
                    }}
                }}
                originalTotalSet {{
                    shopMoney {{
                        amount
                        currencyCode
                    }}
                    presentmentMoney {{
                        amount
                        currencyCode
                    }}
                }}
                discountedTotalSet {{
                    shopMoney {{
                        amount
                        currencyCode
                    }}
                    presentmentMoney {{
                        amount
                        currencyCode
                    }}
                }}
                customAttributes {{
                    key
                    value
                }}
                product {{
{PRODUCT_FIELDS}
                }}
                variant {{
                    id
                    title
                    displayName
                    price
                    sku
                    inventoryQuantity
                    inventoryItem {{
                        id
                    }}
                }}
            }}
        }}
    }}
"""


def get_customer_fields() -> str:
    """Returns GraphQL customer fields as a string fragment."""
    return CUSTOMER_FIELDS


def get_order_fields() -> str:
    """Returns GraphQL order fields as a string fragment."""
    return ORDER_FIELDS


def get_product_fields() -> str:
    """Returns GraphQL product fields as a string fragment."""
    return PRODUCT_FIELDS


def query_with_pydantic_model(
    model_class: Any,
    field_name: str,
    query_args: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
    environment: str = "production"
) -> Dict[str, Any]:
    """
    DEPRECATED: This function is deprecated. Use sgqlc via model.build_query() methods instead.
    
    Execute a GraphQL query using a Pydantic model for automatic query generation and response parsing.
    
    Args:
        model_class: Pydantic model class representing the data structure
        field_name: GraphQL field name to query (e.g., "product", "order")
        query_args: Optional arguments for the GraphQL query (e.g., {"id": "gid://shopify/Product/123"})
        config: Optional Shopify config dict. If not provided, will be generated from environment.
        environment: Environment to use if config is not provided
        
    Returns:
        Dict containing the GraphQL response
        
    Note:
        This function is deprecated. Models now have build_query() methods that use sgqlc.
        Example: Customer.build_query(query_str="email:test@example.com")
    """
    import warnings
    warnings.warn(
        "query_with_pydantic_model is deprecated. Use model.build_query() methods with sgqlc instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    if config is None:
        load_environment(environment)
        config = get_shopify_config(environment)
    
    # Try to use model's build_query method if available
    if hasattr(model_class, 'build_query'):
        raise NotImplementedError(
            f"Use {model_class.__name__}.build_query() directly instead of this deprecated function."
        )
    
    raise NotImplementedError(
        "query_with_pydantic_model is deprecated. Use sgqlc via model.build_query() methods."
    )


def make_graphql_request(
    payload: Dict[str, Any],
    config: Dict[str, Any],
    model_type: Optional[Any] = None,
    connection_field: Optional[str] = None
) -> Any:
    """
    Make a GraphQL request to Shopify API.
    
    Args:
        payload: GraphQL query/mutation payload with 'query' and optional 'variables'
        config: Shopify API configuration from get_shopify_config()
        model_type: Optional (unused, kept for backward compatibility)
        connection_field: Optional (unused, kept for backward compatibility)
        
    Returns:
        ShopifyResponse instance with raw response data (no parsing)
    """
    from models import ShopifyResponse
    
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
        response_data = response.json()
        
        # Check for GraphQL errors
        if "errors" in response_data:
            return ShopifyResponse(
                success=False,
                message="GraphQL errors",
                data=[],
                errors=response_data["errors"]
            )
        
        # Return successful response with raw data
        return ShopifyResponse(
            success=True,
            message="Request successful",
            data=response_data.get("data", {}),
            errors=None
        )
    except requests.exceptions.RequestException as e:
        return ShopifyResponse(
            success=False,
            message=f"Request failed: {str(e)}",
            data=[],
            errors=[{"error": str(e)}]
        )




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
                                    """ + get_product_fields() + """
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
