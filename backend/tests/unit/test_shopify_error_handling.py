#!/usr/bin/env python3
"""
Comprehensive tests for enhanced Shopify error handling logic.
Tests all the new error detection and classification logic added in recent commits.
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
import requests

# Add the backend directory to Python path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from main import app
from services.orders.orders_service import OrdersService
from services.shopify.shopify_service import ShopifyService

client = TestClient(app)


class TestShopifyErrorHandling:
    """Test suite for enhanced Shopify error handling"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_order_number = "12345"
        self.test_email = "test@example.com"

    def test_shopify_service_handles_401_invalid_token(self):
        """Test ShopifyService properly handles 401 authentication errors"""
        shopify_service = ShopifyService()

        # Mock 401 response with Shopify error format
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = '{"errors":"[API] Invalid API key or access token (unrecognized login or wrong password)"}'
        mock_response.json.return_value = {
            "errors": "[API] Invalid API key or access token (unrecognized login or wrong password)"
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response

            result = shopify_service._make_shopify_request({"query": "test"})

            assert result is not None
            assert result["error"] == "authentication_error"
            assert result["status_code"] == 401
            assert "[API] Invalid API key" in result["shopify_errors"]

    def test_shopify_service_handles_404_invalid_store(self):
        """Test ShopifyService properly handles 404 store not found errors"""
        shopify_service = ShopifyService()

        # Mock 404 response with Shopify error format
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = '{"errors":"Not Found"}'
        mock_response.json.return_value = {"errors": "Not Found"}

        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response

            result = shopify_service._make_shopify_request({"query": "test"})

            assert result is not None
            assert result["error"] == "store_not_found"
            assert result["status_code"] == 404
            assert result["shopify_errors"] == "Not Found"

    def test_shopify_service_handles_500_server_error(self):
        """Test ShopifyService properly handles 5xx server errors"""
        shopify_service = ShopifyService()

        # Mock 500 response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response

            result = shopify_service._make_shopify_request({"query": "test"})

            assert result is not None
            assert result["error"] == "server_error"
            assert result["status_code"] == 500
            assert "Internal Server Error" in result["message"]

    def test_shopify_service_handles_connection_error(self):
        """Test ShopifyService properly handles network connection errors"""
        shopify_service = ShopifyService()

        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Network error")

            result = shopify_service._make_shopify_request({"query": "test"})

            assert result is not None
            assert result["error_type"] == "network_failure"
            assert result["error"] == "connection_error"
            assert "Network error" in result["message"]
            assert "Check network connectivity" in result["engineering_note"]

    def test_shopify_service_handles_timeout_error(self):
        """Test ShopifyService properly handles timeout errors"""
        shopify_service = ShopifyService()

        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("Request timeout")

            result = shopify_service._make_shopify_request({"query": "test"})

            assert result is not None
            assert result["error_type"] == "request_timeout"
            assert result["error"] == "timeout_error"
            assert "Request timeout" in result["message"]
            assert "Check network latency" in result["engineering_note"]

    def test_shopify_service_ssl_fallback_with_401_error(self):
        """Test SSL fallback also handles status code errors correctly"""
        shopify_service = ShopifyService()

        # Mock SSL error on first call, 401 error on fallback
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = '{"errors":"[API] Invalid API key"}'
        mock_response.json.return_value = {"errors": "[API] Invalid API key"}

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [
                requests.exceptions.SSLError("SSL error"),
                mock_response,
            ]

            result = shopify_service._make_shopify_request({"query": "test"})

            assert result is not None
            assert result["error"] == "authentication_error"
            assert result["status_code"] == 401
            assert mock_post.call_count == 2

    def test_orders_service_handles_authentication_error(self):
        """Test OrdersService properly processes authentication errors from Shopify"""
        orders_service = OrdersService()

        # Mock authentication error response from ShopifyService
        auth_error_response = {
            "error": "authentication_error",
            "status_code": 401,
            "shopify_errors": "[API] Invalid API key or access token",
        }

        with patch.object(
            orders_service.shopify_service, "_make_shopify_request"
        ) as mock_request:
            mock_request.return_value = auth_error_response

            result = orders_service.fetch_order_details_by_email_or_order_name(
                order_name=self.test_order_number
            )

            assert result["success"] is False
            assert result["error_type"] == "config_error"
            assert result["status_code"] == 401
            assert "[API] Invalid API key" in result["message"]

    def test_orders_service_handles_store_not_found_error(self):
        """Test OrdersService properly processes store not found errors from Shopify"""
        orders_service = OrdersService()

        # Mock store not found error response from ShopifyService
        store_error_response = {
            "error": "store_not_found",
            "status_code": 404,
            "shopify_errors": "Not Found",
        }

        with patch.object(
            orders_service.shopify_service, "_make_shopify_request"
        ) as mock_request:
            mock_request.return_value = store_error_response

            result = orders_service.fetch_order_details_by_email_or_order_name(
                order_name=self.test_order_number
            )

            assert result["success"] is False
            assert result["error_type"] == "config_error"
            assert result["status_code"] == 404
            assert result["message"] == "Not Found"

    def test_orders_service_handles_server_error(self):
        """Test OrdersService properly processes server errors from Shopify"""
        orders_service = OrdersService()

        # Mock server error response from ShopifyService
        server_error_response = {
            "error": "server_error",
            "status_code": 500,
            "message": "Internal Server Error",
        }

        with patch.object(
            orders_service.shopify_service, "_make_shopify_request"
        ) as mock_request:
            mock_request.return_value = server_error_response

            result = orders_service.fetch_order_details_by_email_or_order_name(
                order_name=self.test_order_number
            )

            assert result["success"] is False
            assert result["error_type"] == "server_error"
            assert "temporarily unavailable" in result["message"]

    def test_orders_service_handles_connection_error(self):
        """Test OrdersService properly processes connection errors (None response)"""
        orders_service = OrdersService()

        with patch.object(
            orders_service.shopify_service, "_make_shopify_request"
        ) as mock_request:
            mock_request.return_value = None  # Connection error

            result = orders_service.fetch_order_details_by_email_or_order_name(
                order_name=self.test_order_number
            )

            assert result["success"] is False
            assert result["error_type"] == "connection_error"
            assert "Unable to connect to Shopify" in result["message"]

    def test_orders_service_order_not_found_empty_response(self):
        """Test OrdersService handles successful response with no orders (order not found)"""
        orders_service = OrdersService()

        # Mock successful response with empty orders
        empty_response = {"data": {"orders": {"edges": []}}}

        with patch.object(
            orders_service.shopify_service, "_make_shopify_request"
        ) as mock_request:
            mock_request.return_value = empty_response

            result = orders_service.fetch_order_details_by_email_or_order_name(
                order_name=self.test_order_number
            )

            assert result["success"] is False
            assert result["error_type"] == "order_not_found"
            assert "No orders found" in result["message"]

    def test_orders_service_order_not_found_missing_structure(self):
        """Test OrdersService handles successful response with missing structure (order not found)"""
        orders_service = OrdersService()

        # Mock successful response with missing orders structure
        malformed_response = {"data": {}}  # Missing 'orders' key

        with patch.object(
            orders_service.shopify_service, "_make_shopify_request"
        ) as mock_request:
            mock_request.return_value = malformed_response

            result = orders_service.fetch_order_details_by_email_or_order_name(
                order_name=self.test_order_number
            )

            assert result["success"] is False
            assert result["error_type"] == "order_not_found"
            assert "No orders found" in result["message"]

    def test_orders_service_order_not_found_no_order_id(self):
        """Test OrdersService handles response with orders but no valid order.id"""
        orders_service = OrdersService()

        # Mock response with order but no ID
        no_id_response = {
            "data": {
                "orders": {
                    "edges": [
                        {
                            "node": {
                                "name": "#12345",
                                # Missing 'id' field
                            }
                        }
                    ]
                }
            }
        }

        with patch.object(
            orders_service.shopify_service, "_make_shopify_request"
        ) as mock_request:
            mock_request.return_value = no_id_response

            result = orders_service.fetch_order_details_by_email_or_order_name(
                order_name=self.test_order_number
            )

            assert result["success"] is False
            assert result["error_type"] == "order_not_found"
            assert "No orders found" in result["message"]

    def test_orders_service_invalid_response_data(self):
        """Test OrdersService handles completely invalid response data as API error"""
        orders_service = OrdersService()

        # Mock response with no 'data' field at all
        invalid_response = {"errors": "Something went wrong"}

        with patch.object(
            orders_service.shopify_service, "_make_shopify_request"
        ) as mock_request:
            mock_request.return_value = invalid_response

            result = orders_service.fetch_order_details_by_email_or_order_name(
                order_name=self.test_order_number
            )

            assert result["success"] is False
            assert result["error_type"] == "api_error"
            assert "Unable to connect to Shopify" in result["message"]


class TestRefundsEndpointErrorHandling:
    """Test error handling in the refunds endpoint"""

    def setup_method(self):
        """Set up test fixtures"""
        self.refund_request = {
            "order_number": "12345",
            "requestor_name": {"first": "Test", "last": "User"},
            "requestor_email": "test@example.com",
            "refund_type": "refund",
            "notes": "",
            "sheet_link": "https://example.com",
            "request_submitted_at": "2025-09-13T00:00:00.000Z",
        }

    @patch("services.orders.OrdersService.fetch_order_details_by_email_or_order_name")
    def test_refunds_endpoint_returns_401_for_auth_error(self, mock_fetch):
        """Test refunds endpoint returns 401 for authentication errors"""
        # Mock authentication error
        mock_fetch.return_value = {
            "success": False,
            "error_type": "config_error",
            "status_code": 401,
            "message": "[API] Invalid API key or access token",
        }

        response = client.post("/refunds/send-to-slack", json=self.refund_request)

        assert response.status_code == 401
        response_data = response.json()
        assert response_data["detail"]["error"] == "shopify_config_error"
        assert "[API] Invalid API key" in response_data["detail"]["errors"]

    @patch("services.orders.OrdersService.fetch_order_details_by_email_or_order_name")
    def test_refunds_endpoint_returns_404_for_store_error(self, mock_fetch):
        """Test refunds endpoint returns 404 for store not found errors"""
        # Mock store not found error
        mock_fetch.return_value = {
            "success": False,
            "error_type": "config_error",
            "status_code": 404,
            "message": "Not Found",
        }

        response = client.post("/refunds/send-to-slack", json=self.refund_request)

        assert response.status_code == 404
        response_data = response.json()
        assert response_data["detail"]["error"] == "shopify_config_error"
        assert response_data["detail"]["errors"] == "Not Found"

    @patch("services.orders.OrdersService.fetch_order_details_by_email_or_order_name")
    def test_refunds_endpoint_returns_503_for_connection_error(self, mock_fetch):
        """Test refunds endpoint returns 503 for connection errors"""
        # Mock connection error
        mock_fetch.return_value = {
            "success": False,
            "error_type": "connection_error",
            "message": "Unable to connect to Shopify. Please try again later.",
        }

        response = client.post("/refunds/send-to-slack", json=self.refund_request)

        assert response.status_code == 503
        response_data = response.json()
        assert response_data["detail"]["error"] == "shopify_connection_error"
        assert "technical issue" in response_data["detail"]["user_message"]

    @patch("services.orders.OrdersService.fetch_order_details_by_email_or_order_name")
    def test_refunds_endpoint_returns_503_for_server_error(self, mock_fetch):
        """Test refunds endpoint returns 503 for server errors"""
        # Mock server error
        mock_fetch.return_value = {
            "success": False,
            "error_type": "server_error",
            "message": "Shopify is temporarily unavailable. Please try again later.",
        }

        response = client.post("/refunds/send-to-slack", json=self.refund_request)

        assert response.status_code == 503
        response_data = response.json()
        assert response_data["detail"]["error"] == "shopify_connection_error"

    @patch("services.slack.slack_service.SlackService.send_refund_request_notification")
    @patch("services.orders.OrdersService.fetch_order_details_by_email_or_order_name")
    def test_refunds_endpoint_returns_406_for_order_not_found(
        self, mock_fetch, mock_slack
    ):
        """Test refunds endpoint returns 406 for legitimate order not found"""
        # Mock order not found (successful Shopify response but no orders)
        mock_fetch.return_value = {
            "success": False,
            "error_type": "order_not_found",
            "message": "No orders found.",
        }

        # Mock successful Slack notification
        mock_slack.return_value = {"success": True}

        response = client.post("/refunds/send-to-slack", json=self.refund_request)

        assert response.status_code == 406
        assert "Order 12345 not found in Shopify" in response.json()["detail"]

        # Verify Slack notification was sent (customer should be emailed)
        mock_slack.assert_called_once()

    @patch("services.orders.OrdersService.fetch_order_details_by_email_or_order_name")
    def test_refunds_endpoint_handles_unexpected_error_type(self, mock_fetch):
        """Test refunds endpoint handles unexpected error types gracefully"""
        # Mock unexpected error type
        mock_fetch.return_value = {
            "success": False,
            "error_type": "unknown_error",
            "message": "Something unexpected happened",
        }

        response = client.post("/refunds/send-to-slack", json=self.refund_request)

        assert response.status_code == 503
        response_data = response.json()
        assert response_data["detail"]["error"] == "shopify_api_error"


class TestShopifyErrorExtractionEdgeCases:
    """Test edge cases in Shopify error message extraction"""

    def test_shopify_service_handles_non_json_error_response(self):
        """Test ShopifyService handles non-JSON error responses"""
        shopify_service = ShopifyService()

        # Mock 401 response with plain text (not JSON)
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.side_effect = ValueError("Not JSON")

        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response

            result = shopify_service._make_shopify_request({"query": "test"})

            assert result is not None
            assert result["error"] == "authentication_error"
            assert result["status_code"] == 401
            assert result["shopify_errors"] == "Unauthorized"  # Falls back to text

    def test_shopify_service_handles_json_without_errors_field(self):
        """Test ShopifyService handles JSON response without 'errors' field"""
        shopify_service = ShopifyService()

        # Mock 404 response with JSON but no 'errors' field
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = '{"message":"Not Found"}'
        mock_response.json.return_value = {"message": "Not Found"}

        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response

            result = shopify_service._make_shopify_request({"query": "test"})

            assert result is not None
            assert result["error"] == "store_not_found"
            assert result["status_code"] == 404
            # Should fall back to response.text when 'errors' field is missing
            assert result["shopify_errors"] == '{"message":"Not Found"}'


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
