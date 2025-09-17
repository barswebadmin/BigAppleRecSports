"""
Tests for the Shopify webhooks router.

Tests the HTTP endpoint that receives Shopify product update webhooks
and verifies enhanced logging and response structure.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from main import app


class TestWebhooksRouter:
    """Test the webhooks router endpoint"""

    @pytest.fixture
    def client(self):
        """FastAPI test client fixture"""
        return TestClient(app)

    @pytest.fixture
    def mock_webhook_signature(self):
        """Mock webhook signature verification to always pass"""
        with patch(
            "services.webhooks.WebhooksService.verify_webhook_signature",
            return_value=True,
        ):
            yield

    @pytest.fixture
    def sample_product_data(self):
        """Sample product data for testing"""
        return {
            "id": 7350462185566,
            "title": "Big Apple Dodgeball - Tuesday - Open Division - Fall 2025",
            "handle": "big-apple-dodgeball-tuesday-open-division-fall-2025",
            "variants": [
                {
                    "id": 41558875045982,
                    "title": "Veteran Registration",
                    "inventory_quantity": 10,
                },
                {
                    "id": 41558875078750,
                    "title": "Early Registration",
                    "inventory_quantity": 11,
                },
            ],
        }

    def test_product_update_webhook_with_inventory(
        self, client, mock_webhook_signature, sample_product_data
    ):
        """Test webhook endpoint returns enhanced product info for products with inventory"""

        # Headers from Shopify
        headers = {
            "x-shopify-topic": "products/update",
            "x-shopify-hmac-sha256": "test-signature",
            "content-type": "application/json",
        }

        response = client.post(
            "/webhooks/shopify",
            headers=headers,
            json=sample_product_data,
        )

        assert response.status_code == 200

        # Verify enhanced response structure
        response_data = response.json()
        assert response_data["success"] is True
        assert "still has inventory" in response_data["message"]

        # Verify detailed product information is included
        assert "product_info" in response_data
        product_info = response_data["product_info"]

        assert product_info["id"] == 7350462185566
        assert (
            product_info["title"]
            == "Big Apple Dodgeball - Tuesday - Open Division - Fall 2025"
        )
        assert product_info["total_inventory"] == 21  # 10 + 11
        assert product_info["sold_out"] is False
        assert "admin.shopify.com" in product_info["admin_url"]
        assert "myshopify.com/products/big-apple-dodgeball" in product_info["store_url"]

    @patch("services.webhooks.integrations.gas_client.GASClient.send_to_waitlist_form")
    def test_product_update_webhook_sold_out(
        self, mock_gas_send, client, mock_webhook_signature, sample_product_data
    ):
        """Test webhook endpoint returns enhanced product info for sold out products"""

        # Mock GAS response
        mock_gas_send.return_value = {"success": True, "response": "Added to waitlist"}

        # Make all variants have zero inventory
        for variant in sample_product_data["variants"]:
            variant["inventory_quantity"] = 0

        headers = {
            "x-shopify-topic": "products/update",
            "x-shopify-hmac-sha256": "test-signature",
            "content-type": "application/json",
        }

        response = client.post(
            "/webhooks/shopify",
            headers=headers,
            json=sample_product_data,
        )

        assert response.status_code == 200

        # Verify enhanced response structure for sold out product
        response_data = response.json()
        assert response_data["success"] is True
        assert "sold out" in response_data["message"]
        assert "waitlist form updated" in response_data["message"]

        # Verify detailed product information
        assert "product_info" in response_data
        product_info = response_data["product_info"]

        assert product_info["id"] == 7350462185566
        assert (
            product_info["title"]
            == "Big Apple Dodgeball - Tuesday - Open Division - Fall 2025"
        )
        assert product_info["total_inventory"] == 0
        assert product_info["sold_out"] is True
        assert "admin.shopify.com" in product_info["admin_url"]
        assert "myshopify.com/products/big-apple-dodgeball" in product_info["store_url"]

        # Verify waitlist processing data is included
        assert "parsed_product" in response_data
        assert "waitlist_result" in response_data

        # Verify GAS was called for sold out product
        mock_gas_send.assert_called_once()

    def test_invalid_signature_returns_401(self, client, sample_product_data):
        """Test that invalid webhook signature returns 401"""

        # Mock signature verification to fail
        with patch(
            "services.webhooks.WebhooksService.verify_webhook_signature",
            return_value=False,
        ):
            headers = {
                "x-shopify-topic": "products/update",
                "x-shopify-hmac-sha256": "invalid-signature",
                "content-type": "application/json",
            }

            response = client.post(
                "/webhooks/shopify",
                headers=headers,
                json=sample_product_data,
            )

            assert response.status_code == 401
            assert "Invalid webhook signature" in response.json()["detail"]

    def test_order_create_webhook(self, client, mock_webhook_signature):
        """Test order create webhooks are processed correctly"""

        headers = {
            "x-shopify-topic": "orders/create",
            "x-shopify-hmac-sha256": "test-signature",
            "content-type": "application/json",
        }

        # Provide a realistic order payload for testing
        order_payload = {
            "order_number": 12345,
            "contact_email": "customer@example.com",
            "customer": {"first_name": "Test", "last_name": "Customer"},
            "line_items": [{"variant_title": "Standard Registration"}]
        }

        response = client.post(
            "/webhooks/shopify",
            headers=headers,
            json=order_payload,
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert "standard order processed" in response_data["message"]
        assert "is_email_mismatch" in response_data
        assert "is_waitlist_registration" in response_data
        assert response_data["order_number"] == 12345

    def test_unknown_webhook_type(self, client, mock_webhook_signature):
        """Test unknown webhook types are logged and handled gracefully"""

        headers = {
            "x-shopify-topic": "customers/create",  # Unknown webhook type
            "x-shopify-hmac-sha256": "test-signature",
            "content-type": "application/json",
        }

        response = client.post(
            "/webhooks/shopify",
            headers=headers,
            json={"id": 123, "email": "test@example.com"},
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert "Webhook received and logged for event type: customers/create" in response_data["message"]
        assert response_data["event_type"] == "customers/create"
