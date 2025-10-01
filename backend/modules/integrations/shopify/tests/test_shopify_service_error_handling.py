"""Test ShopifyService error handling for network and request failures."""

import pytest
from unittest.mock import Mock, patch
import requests
from backend.services.shopify.shopify_service import ShopifyService


class TestShopifyServiceErrorHandling:
    """Test how ShopifyService handles various error scenarios."""

    @pytest.fixture
    def shopify_service(self):
        """Create a ShopifyService instance for testing."""
        with patch(
            "backend.services.shopify.shopify_service.config"
        ) as mock_config:
            mock_config.shopify_token = "test_token"
            mock_config.graphql_url = (
                "https://test.myshopify.com/admin/api/2023-10/graphql.json"
            )
            mock_config.rest_url = "https://test.myshopify.com/admin/api/2023-10"
            service = ShopifyService()
            return service

    def test_connection_error_handling(self, shopify_service):
        """Test handling of network connection errors."""
        test_query = {"query": "{ shop { name } }"}

        with patch("requests.post") as mock_post:
            # Simulate connection error
            mock_post.side_effect = requests.exceptions.ConnectionError(
                "Connection refused"
            )

            result = shopify_service._make_shopify_request(test_query)

            # Should return structured error response
            assert isinstance(result, dict)
            assert result["error"] == "connection_error"
            assert result["error_type"] == "network_failure"
            assert "Failed to connect to Shopify" in result["message"]
            assert "network connectivity" in result["engineering_note"]

    def test_timeout_error_handling(self, shopify_service):
        """Test handling of request timeout errors."""
        test_query = {"query": "{ shop { name } }"}

        with patch("requests.post") as mock_post:
            # Simulate timeout error
            mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

            result = shopify_service._make_shopify_request(test_query)

            # Should return structured error response
            assert isinstance(result, dict)
            assert result["error"] == "timeout_error"
            assert result["error_type"] == "request_timeout"
            assert "timed out after 30 seconds" in result["message"]
            assert "network latency" in result["engineering_note"]

    def test_generic_request_exception_handling(self, shopify_service):
        """Test handling of generic request exceptions."""
        test_query = {"query": "{ shop { name } }"}

        with patch("requests.post") as mock_post:
            # Simulate generic request exception
            mock_post.side_effect = requests.exceptions.RequestException(
                "SSL handshake failed"
            )

            result = shopify_service._make_shopify_request(test_query)

            # Should return structured error response
            assert isinstance(result, dict)
            assert result["error"] == "request_exception"
            assert result["error_type"] == "unknown_request_failure"
            assert "Unexpected request error" in result["message"]
            assert "SSL issues" in result["engineering_note"]

    def test_dns_resolution_error(self, shopify_service):
        """Test handling of DNS resolution errors (a type of connection error)."""
        test_query = {"query": "{ shop { name } }"}

        with patch("requests.post") as mock_post:
            # Simulate DNS resolution error
            mock_post.side_effect = requests.exceptions.ConnectionError(
                "Failed to resolve 'test.myshopify.com'"
            )

            result = shopify_service._make_shopify_request(test_query)

            # Should return connection error
            assert result["error"] == "connection_error"
            assert "DNS resolution" in result["engineering_note"]

    def test_ssl_error_with_fallback_failure(self, shopify_service):
        """Test SSL error with fallback also failing."""
        test_query = {"query": "{ shop { name } }"}

        with patch("requests.post") as mock_post:
            # First call fails with SSL error, second call (fallback) fails with connection error
            mock_post.side_effect = [
                requests.exceptions.SSLError("SSL certificate verification failed"),
                requests.exceptions.ConnectionError("Connection refused"),
            ]

            result = shopify_service._make_shopify_request(test_query)

            # Should return None for fallback failure (maintaining current behavior)
            assert result is None

    def test_successful_request_after_ssl_fallback(self, shopify_service):
        """Test successful request after SSL error triggers fallback."""
        test_query = {"query": "{ shop { name } }"}

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"shop": {"name": "Test Shop"}},
            "extensions": {"cost": {"requestedQueryCost": 1}},
        }

        with patch("requests.post") as mock_post:
            # First call fails with SSL error, second call (fallback) succeeds
            mock_post.side_effect = [
                requests.exceptions.SSLError("SSL certificate verification failed"),
                mock_response,
            ]

            result = shopify_service._make_shopify_request(test_query)

            # Should return successful response
            assert isinstance(result, dict)
            assert "data" in result
            assert result["data"]["shop"]["name"] == "Test Shop"

    def test_error_response_structure(self, shopify_service):
        """Test that all error responses have consistent structure."""
        test_query = {"query": "{ shop { name } }"}

        error_scenarios = [
            (requests.exceptions.ConnectionError("test"), "connection_error"),
            (requests.exceptions.Timeout("test"), "timeout_error"),
            (requests.exceptions.RequestException("test"), "request_exception"),
        ]

        for exception, expected_error_type in error_scenarios:
            with patch("requests.post") as mock_post:
                mock_post.side_effect = exception

                result = shopify_service._make_shopify_request(test_query)

                # Verify consistent error structure
                assert isinstance(result, dict)
                assert "error" in result
                assert "error_type" in result
                assert "message" in result
                assert "engineering_note" in result
                assert result["error"] == expected_error_type


class TestCreateProductErrorHandling:
    """Test create_product function error handling."""

    def test_none_response_handling(self):
        """Test create_product handles None response from Shopify service."""
        # Mock the ShopifyService to return None
        with patch(
            "backend.services.products.create_product_complete_proces.create_product.create_product.ShopifyService"
        ) as mock_service_class:
            mock_service = Mock()
            mock_service._make_shopify_request.return_value = None
            mock_service_class.return_value = mock_service

            # Mock a simple request dict (avoiding complex Pydantic model validation)
            mock_request = Mock()
            mock_request.important_dates = Mock()
            mock_request.important_dates.vet_date = "2025-09-20"
            mock_request.important_dates.early_date = "2025-09-21"
            mock_request.important_dates.open_date = "2025-09-22"
            mock_request.important_dates.closing_party_date = "2025-09-23"

            # Import and patch the create_product function to bypass validation
            from backend.services.products.create_product_complete_proces.create_product.create_product import (
                create_product,
            )

            # Mock the date validation to pass
            with patch(
                "backend.services.products.create_product_complete_proces.create_product.create_product.validate_important_dates"
            ) as mock_validate:
                mock_validate.return_value = ([], [])  # No issues, no warnings

                result = create_product(mock_request)

                # Should return structured error
                assert result["success"] is False
                assert result["step_failed"] == "shopify_request"
                assert "No response received" in result["details"]

    def test_engineering_error_response_handling(self):
        """Test create_product handles engineering error responses."""
        # Mock the ShopifyService to return engineering error
        with patch(
            "backend.services.products.create_product_complete_proces.create_product.create_product.ShopifyService"
        ) as mock_service_class:
            mock_service = Mock()
            mock_service._make_shopify_request.return_value = {
                "error": "connection_error",
                "error_type": "network_failure",
                "message": "Failed to connect to Shopify: Connection refused",
                "engineering_note": "Check network connectivity, DNS resolution, and Shopify endpoint availability",
            }
            mock_service_class.return_value = mock_service

            # Mock a simple request dict
            mock_request = Mock()
            mock_request.important_dates = Mock()
            mock_request.important_dates.vet_date = "2025-09-20"
            mock_request.important_dates.early_date = "2025-09-21"
            mock_request.important_dates.open_date = "2025-09-22"
            mock_request.important_dates.closing_party_date = "2025-09-23"

            from backend.services.products.create_product_complete_proces.create_product.create_product import (
                create_product,
            )

            # Mock the date validation to pass
            with patch(
                "backend.services.products.create_product_complete_proces.create_product.create_product.validate_important_dates"
            ) as mock_validate:
                mock_validate.return_value = ([], [])  # No issues, no warnings

                result = create_product(mock_request)

                # Should return structured error with engineering info
                assert result["success"] is False
                assert result["step_failed"] == "shopify_request"
                assert result["error_type"] == "network_failure"
                assert "Failed to connect to Shopify" in result["error"]
                assert "network connectivity" in result["details"]
