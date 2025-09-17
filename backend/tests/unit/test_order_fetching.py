#!/usr/bin/env python3
"""
Comprehensive tests for order fetching functionality.
Tests both Shopify API integration and backend API endpoints.
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Add the backend directory to Python path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from main import app
from services.orders.orders_service import OrdersService
from services.shopify.shopify_service import ShopifyService

client = TestClient(app)


class TestOrderFetching:
    """Test suite for order fetching functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_order_number = "42234"
        self.test_email = "jdazz87@gmail.com"
        self.test_order_id = "gid://shopify/Order/5875167625310"

        # Sample order data that should be returned from Shopify
        self.expected_order_data = {
            "id": self.test_order_id,
            "name": f"#{self.test_order_number}",
            "createdAt": "2025-09-09T05:16:45Z",
            "discountCode": None,
            "totalPriceSet": {"presentmentMoney": {"amount": "2.0"}},
            "customer": {
                "id": "gid://shopify/Customer/7103723110494",
                "email": self.test_email,
            },
            "lineItems": {
                "edges": [
                    {
                        "node": {
                            "id": "gid://shopify/LineItem/14099423494238",
                            "title": "joe test product",
                            "quantity": 1,
                            "originalUnitPriceSet": {
                                "presentmentMoney": {"amount": "2.0"}
                            },
                            "product": {
                                "id": "gid://shopify/Product/7350462185566",
                                "title": "joe test product",
                                "descriptionHtml": "<h1>Test Product</h1>",
                                "tags": [],
                            },
                        }
                    }
                ]
            },
        }

        # Mock successful Shopify GraphQL response
        self.mock_shopify_response = {
            "data": {"orders": {"edges": [{"node": self.expected_order_data}]}}
        }

    def test_orders_service_fetch_by_order_number_success(self):
        """Test OrdersService successfully fetches order by number"""
        orders_service = OrdersService()

        # Mock the Shopify service to return successful response
        with patch.object(
            orders_service.shopify_service, "_make_shopify_request"
        ) as mock_request:
            mock_request.return_value = self.mock_shopify_response

            result = orders_service.fetch_order_details_by_email_or_order_number(
                order_number=self.test_order_number
            )

            assert result["success"] is True
            assert result["data"]["name"] == f"#{self.test_order_number}"
            assert result["data"]["customer"]["email"] == self.test_email

            # Verify the GraphQL queries were called (order fetch + product variants)
            assert mock_request.call_count == 2
            # First call should be for order details
            first_call_query = mock_request.call_args_list[0][0][0]["query"]
            assert f"name:#{self.test_order_number}" in first_call_query

    def test_orders_service_fetch_by_order_number_with_hash_prefix(self):
        """Test OrdersService handles order number with # prefix correctly"""
        orders_service = OrdersService()

        with patch.object(
            orders_service.shopify_service, "_make_shopify_request"
        ) as mock_request:
            mock_request.return_value = self.mock_shopify_response

            # Test with # prefix - should not double-prefix
            result = orders_service.fetch_order_details_by_email_or_order_number(
                order_number=f"#{self.test_order_number}"
            )

            assert result["success"] is True

            # Verify the query doesn't have double # prefix (check first call - order search)
            first_call_query = mock_request.call_args_list[0][0][0]["query"]
            assert f"name:#{self.test_order_number}" in first_call_query
            assert f"name:##{self.test_order_number}" not in first_call_query

    def test_orders_service_fetch_by_email_success(self):
        """Test OrdersService successfully fetches order by email"""
        orders_service = OrdersService()

        with patch.object(
            orders_service.shopify_service, "_make_shopify_request"
        ) as mock_request:
            mock_request.return_value = self.mock_shopify_response

            result = orders_service.fetch_order_details_by_email_or_order_number(
                email=self.test_email
            )

            assert result["success"] is True
            # Email search returns a list of orders, check the first one
            assert len(result["data"]) > 0
            first_order = result["data"][0]
            assert first_order["customer"]["email"] == self.test_email

            # Verify the GraphQL query used email search (check first call - order search)
            first_call_query = mock_request.call_args_list[0][0][0]["query"]
            assert f"email:{self.test_email}" in first_call_query

    def test_orders_service_no_order_found(self):
        """Test OrdersService handles case when order is not found"""
        orders_service = OrdersService()

        # Mock empty response (no orders found)
        empty_response = {"data": {"orders": {"edges": []}}}

        with patch.object(
            orders_service.shopify_service, "_make_shopify_request"
        ) as mock_request:
            mock_request.return_value = empty_response

            result = orders_service.fetch_order_details_by_email_or_order_number(
                order_number="nonexistent"
            )

            assert result["success"] is False
            assert "No orders found" in result["message"]

    def test_orders_service_handles_shopify_api_failure(self):
        """Test OrdersService handles Shopify API failures gracefully"""
        orders_service = OrdersService()

        with patch.object(
            orders_service.shopify_service, "_make_shopify_request"
        ) as mock_request:
            # Mock API failure (returns None)
            mock_request.return_value = None

            result = orders_service.fetch_order_details_by_email_or_order_number(
                order_number=self.test_order_number
            )

            assert result["success"] is False
            assert "Unable to connect to Shopify" in result["message"]

    def test_orders_service_handles_malformed_shopify_response(self):
        """Test OrdersService handles malformed Shopify responses"""
        orders_service = OrdersService()

        # Mock malformed response (missing expected structure)
        malformed_response = {
            "data": {}  # Missing orders key
        }

        with patch.object(
            orders_service.shopify_service, "_make_shopify_request"
        ) as mock_request:
            mock_request.return_value = malformed_response

            result = orders_service.fetch_order_details_by_email_or_order_number(
                order_number=self.test_order_number
            )

            assert result["success"] is False

    @patch(
        "services.orders.orders_service.OrdersService.fetch_order_details_by_email_or_order_number"
    )
    def test_get_order_endpoint_success(self, mock_fetch):
        """Test /orders/{order_number} endpoint returns order successfully"""
        # Mock successful order fetch with processed data structure
        mock_fetch.return_value = {
            "success": True,
            "data": {
                "id": self.test_order_id,
                "orderId": self.test_order_id,
                "name": f"#{self.test_order_number}",
                "created_at": "2025-09-09T05:16:45Z",
                "total_price": "2.0",
                "discount_code": None,
                "customer": {
                    "id": "gid://shopify/Customer/7103723110494",
                    "email": self.test_email,
                },
                "line_items": [
                    {
                        "id": "gid://shopify/LineItem/14099423494238",
                        "title": "joe test product",
                        "quantity": 1,
                        "price": "2.0",
                        "product": {
                            "id": "gid://shopify/Product/7350462185566",
                            "title": "joe test product",
                            "descriptionHtml": "<h1>Test Product</h1>",
                            "tags": [],
                        },
                    }
                ],
                "product": {
                    "title": "joe test product",
                    "productId": "gid://shopify/Product/7350462185566",
                    "descriptionHtml": "<h1>Test Product</h1>",
                    "tags": [],
                    "variants": [],
                },
            },
        }

        response = client.get(f"/orders/{self.test_order_number}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["order"]["name"] == f"#{self.test_order_number}"

    @patch(
        "services.orders.orders_service.OrdersService.fetch_order_details_by_email_or_order_number"
    )
    def test_get_order_endpoint_not_found(self, mock_fetch):
        """Test /orders/{order_number} endpoint handles order not found"""
        # Mock order not found
        mock_fetch.return_value = {"success": False, "message": "Order not found"}

        response = client.get("/orders/nonexistent")

        assert response.status_code == 406
        assert "Order not found" in response.json()["detail"]

    @patch(
        "services.orders.orders_service.OrdersService.fetch_order_details_by_email_or_order_number"
    )
    def test_get_order_endpoint_with_email_fallback(self, mock_fetch):
        """Test /orders/{order_number} endpoint uses email fallback when order not found"""
        # First call (order number) fails, second call (email) succeeds
        mock_fetch.side_effect = [
            {"success": False, "message": "Order not found"},
            {
                "success": True,
                "data": {
                    "id": self.test_order_id,
                    "orderId": self.test_order_id,
                    "name": f"#{self.test_order_number}",
                    "created_at": "2025-09-09T05:16:45Z",
                    "total_price": "2.0",
                    "discount_code": None,
                    "customer": {
                        "id": "gid://shopify/Customer/7103723110494",
                        "email": self.test_email,
                    },
                    "line_items": [],
                    "product": {
                        "title": "joe test product",
                        "productId": "gid://shopify/Product/7350462185566",
                        "descriptionHtml": "<h1>Test Product</h1>",
                        "tags": [],
                        "variants": [],
                    },
                },
            },
        ]

        response = client.get(f"/orders/nonexistent?email={self.test_email}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify both order number and email searches were attempted
        assert mock_fetch.call_count == 2
        mock_fetch.assert_any_call(order_number="nonexistent")
        mock_fetch.assert_any_call(email=self.test_email)


class TestShopifyServiceSSLHandling:
    """Test SSL handling in ShopifyService"""

    @patch("requests.post")
    def test_shopify_service_ssl_fallback(self, mock_post):
        """Test ShopifyService falls back to no SSL verification on SSL errors"""
        from requests.exceptions import SSLError

        # Force real API calls for testing
        with patch.dict(os.environ, {"FORCE_REAL_API": "true"}):
            # First call raises SSL error, second succeeds
            mock_post.side_effect = [
                SSLError("Certificate verification failed"),
                Mock(status_code=200, json=lambda: {"data": {"orders": {"edges": []}}}),
            ]

            shopify_service = ShopifyService()
            result = shopify_service._make_shopify_request({"query": "test"})

            assert result is not None
            assert mock_post.call_count == 2

        # First call should have verify=True, second should have verify=False
        first_call_kwargs = mock_post.call_args_list[0][1]
        second_call_kwargs = mock_post.call_args_list[1][1]

        assert first_call_kwargs.get("verify") is True
        assert second_call_kwargs.get("verify") is False


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
