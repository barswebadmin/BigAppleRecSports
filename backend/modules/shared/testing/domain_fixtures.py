"""
Shared domain test fixtures.

Provides mock domain objects (orders, customers, refunds, etc.) for testing.
"""

import pytest
from typing import Dict, Any
from datetime import datetime, timedelta


@pytest.fixture
def mock_order_data() -> Dict[str, Any]:
    """
    Mock Shopify order data.
    
    Returns:
        Dict with standard order fields
    """
    created_at = datetime.now() - timedelta(days=5)
    
    return {
        "order": {
            "id": "gid://shopify/Order/1234567890",
            "name": "#TEST1001",
            "orderNumber": 1001,
            "createdAt": created_at.isoformat(),
            "totalPrice": "149.99",
            "subtotalPrice": "129.99",
            "totalTax": "10.00",
            "totalShipping": "10.00",
            "fulfillmentStatus": "UNFULFILLED",
            "financialStatus": "PAID",
            "cancelledAt": None,
            "customer": {
                "id": "gid://shopify/Customer/9876543210",
                "email": "test.customer@example.com",
                "firstName": "Test",
                "lastName": "Customer",
                "phone": "+15551234567"
            },
            "lineItems": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/LineItem/111",
                            "title": "Test Product - XL",
                            "quantity": 1,
                            "originalUnitPrice": "129.99",
                            "variant": {
                                "id": "gid://shopify/ProductVariant/222",
                                "title": "XL",
                                "sku": "TEST-PROD-XL"
                            },
                            "product": {
                                "id": "gid://shopify/Product/333",
                                "title": "Test Product"
                            },
                            "customAttributes": [
                                {
                                    "key": "Season Start",
                                    "value": "2026-03-15"
                                }
                            ]
                        }
                    }
                ]
            },
            "refunds": []
        }
    }


@pytest.fixture
def mock_customer_data() -> Dict[str, Any]:
    """
    Mock Shopify customer data.
    
    Returns:
        Dict with standard customer fields
    """
    return {
        "customer": {
            "id": "gid://shopify/Customer/9876543210",
            "email": "test.customer@example.com",
            "firstName": "Test",
            "lastName": "Customer",
            "phone": "+15551234567",
            "createdAt": "2025-01-01T00:00:00Z",
            "numberOfOrders": 3,
            "amountSpent": "449.97",
            "tags": ["kickball", "spring-2026"],
            "defaultAddress": {
                "address1": "123 Test St",
                "city": "New York",
                "province": "NY",
                "zip": "10001",
                "country": "US"
            }
        }
    }


@pytest.fixture
def mock_refund_request() -> Dict[str, Any]:
    """
    Mock refund request data.
    
    Returns:
        Dict with standard refund request fields
    """
    return {
        "email": "test.customer@example.com",
        "order_number": "#TEST1001",
        "refund_type": "refund",
        "request_submitted_at": datetime.now().isoformat(),
        "requestor_name": {
            "first": "Test",
            "last": "Customer"
        },
        "notes": "Changed my mind about this order",
        "sheet_link": "https://docs.google.com/spreadsheets/d/test123"
    }


@pytest.fixture
def mock_order_with_refund() -> Dict[str, Any]:
    """
    Mock order data that already has a refund.
    
    Returns:
        Dict with order data including existing refund
    """
    order_data = mock_order_data()
    order_data["order"]["refunds"] = [
        {
            "id": "gid://shopify/Refund/555",
            "createdAt": (datetime.now() - timedelta(days=1)).isoformat(),
            "totalRefunded": "50.00",
            "refundLineItems": {
                "edges": [
                    {
                        "node": {
                            "lineItem": {
                                "id": "gid://shopify/LineItem/111"
                            },
                            "quantity": 1,
                            "restockType": "RETURN"
                        }
                    }
                ]
            }
        }
    ]
    return order_data


@pytest.fixture
def mock_fulfilled_order() -> Dict[str, Any]:
    """
    Mock order data that has been fulfilled.
    
    Returns:
        Dict with fulfilled order data
    """
    order_data = mock_order_data()
    order_data["order"]["fulfillmentStatus"] = "FULFILLED"
    return order_data


@pytest.fixture
def mock_cancelled_order() -> Dict[str, Any]:
    """
    Mock order data that has been cancelled.
    
    Returns:
        Dict with cancelled order data
    """
    order_data = mock_order_data()
    order_data["order"]["cancelledAt"] = (datetime.now() - timedelta(hours=2)).isoformat()
    order_data["order"]["financialStatus"] = "REFUNDED"
    return order_data


def create_mock_line_item(
    title: str = "Test Product",
    quantity: int = 1,
    price: str = "99.99",
    season_start: str = None
) -> Dict[str, Any]:
    """
    Create a mock line item.
    
    Args:
        title: Product title
        quantity: Quantity ordered
        price: Unit price
        season_start: Optional season start date
        
    Returns:
        Mock line item dict
    """
    line_item = {
        "id": f"gid://shopify/LineItem/{hash(title)}",
        "title": title,
        "quantity": quantity,
        "originalUnitPrice": price,
        "variant": {
            "id": f"gid://shopify/ProductVariant/{hash(title)}",
            "title": "Default",
            "sku": f"TEST-{title.upper().replace(' ', '-')}"
        },
        "product": {
            "id": f"gid://shopify/Product/{hash(title)}",
            "title": title
        },
        "customAttributes": []
    }
    
    if season_start:
        line_item["customAttributes"].append({
            "key": "Season Start",
            "value": season_start
        })
    
    return line_item

