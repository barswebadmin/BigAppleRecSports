"""
Tests for the new Webhooks Service implementation

Tests the core webhook processing logic with real Shopify webhook data.
"""

import json
import pytest
from unittest.mock import patch, Mock
from services.webhooks_service import WebhooksService


class TestWebhooksService:
    
    def setup_method(self):
        """Setup test fixtures"""
        self.service = WebhooksService()
        
        # Real webhook data from your example
        self.sample_headers = {
            'host': 'cba70bd4fd91.ngrok-free.app',
            'user-agent': 'Shopify-Captain-Hook',
            'content-type': 'application/json',
            'x-shopify-api-version': 'unstable',
            'x-shopify-event-id': '95046202-9fe4-4bba-9057-d7cd5707b99f',
            'x-shopify-hmac-sha256': '5F0ishm/o/miAa3+uuwOBZ0BfB5/oYtiB9pv/l2rYRA=',
            'x-shopify-product-id': '7350462185566',
            'x-shopify-shop-domain': '09fe59-3.myshopify.com',
            'x-shopify-topic': 'products/update',
            'x-shopify-triggered-at': '2025-09-12T00:48:41.964744581Z',
            'x-shopify-webhook-id': '494ab038-85da-4f93-a37a-742cd9b02b5a'
        }
        
        self.sample_product_data = {
            "id": 7350462185566,
            "title": "joe test product - dodgeball",
            "variants": [
                {
                    "id": 41558875045982,
                    "title": "Veteran Registration",
                    "inventory_quantity": 0
                },
                {
                    "id": 41558875078750,
                    "title": "Early Registration",
                    "inventory_quantity": 0
                },
                {
                    "id": 41558875111518,
                    "title": "Open Registration", 
                    "inventory_quantity": 21
                },
                {
                    "id": 41558917742686,
                    "title": "Coming off Waitlist Reg",
                    "inventory_quantity": 0
                }
            ]
        }
    
    def test_verify_webhook_signature(self):
        """Test webhook signature verification in various scenarios"""
        import hmac
        import hashlib
        import base64
        
        test_body = b'{"id": 7350462185566, "title": "joe test product - dodgeball", "variants": []}'
        
        # Should return True when no secret is configured (development mode)
        assert self.service.verify_webhook_signature(test_body, "any-signature") is True
        
        # Should return True when valid signature provided with configured secret
        with patch.dict('os.environ', {'SHOPIFY_WEBHOOK_SECRET': 'test-webhook-secret-123'}):
            service = WebhooksService()  # Create new service to pick up env var
            secret = b"test-webhook-secret-123"
            
            # Generate correct signature using the same algorithm Shopify uses
            expected_signature = hmac.new(secret, test_body, hashlib.sha256).digest()
            base64_signature = base64.b64encode(expected_signature).decode()
            
            assert service.verify_webhook_signature(test_body, base64_signature) is True
        
        # Should return False when invalid signatures provided with configured secret
        with patch.dict('os.environ', {'SHOPIFY_WEBHOOK_SECRET': 'test-webhook-secret-123'}):
            service = WebhooksService()  # Create new service to pick up env var
            
            assert service.verify_webhook_signature(test_body, "invalid-signature") is False
            assert service.verify_webhook_signature(test_body, "") is False
            assert service.verify_webhook_signature(test_body, "SGVsbG8gV29ybGQ=") is False  # Valid base64 but wrong signature
    
    def test_is_product_update(self):
        """Test identifying product update webhooks"""
        # Should return True for product update webhooks
        headers = {"x-shopify-topic": "products/update"}
        assert self.service.is_product_update(headers) is True
        
        # Should return False for non-product-update webhooks
        headers = {"x-shopify-topic": "orders/create"}
        assert self.service.is_product_update(headers) is False
        
        # Should return False when no topic header present
        headers = {}
        assert self.service.is_product_update(headers) is False
    
    def test_product_has_zero_inventory(self):
        """Test detecting products with zero inventory"""
        # Should return True when all variants have zero inventory
        product_data = {
            "variants": [
                {"inventory_quantity": 0},
                {"inventory_quantity": 0},
                {"inventory_quantity": 0}
            ]
        }
        assert self.service.product_has_zero_inventory(product_data) is True
        
        # Should return False when some variants have inventory
        assert self.service.product_has_zero_inventory(self.sample_product_data) is False  # Has inventory = 21
        
        product_data = {
            "variants": [
                {"inventory_quantity": 0},
                {"inventory_quantity": 5},  # Has inventory
                {"inventory_quantity": 0}
            ]
        }
        assert self.service.product_has_zero_inventory(product_data) is False
        
        # Should return False when no variants present
        product_data = {"variants": []}
        assert self.service.product_has_zero_inventory(product_data) is False
        
        product_data = {}
        assert self.service.product_has_zero_inventory(product_data) is False
    
    def test_parse_shopify_webhook_for_waitlist_form(self):
        """Test parsing Shopify webhook product data for waitlist form"""
        # Should parse standard title correctly (per user specification)
        product_data = {"id": 7450381877342, "title": "Big Apple Dodgeball - Tuesday - Open Division - Fall 2025"}
        result = self.service.parse_shopify_webhook_for_waitlist_form(product_data)
        
        expected = {
            "product_url": "https://admin.shopify.com/store/09fe59-3/products/7450381877342",
            "sport": "Dodgeball",
            "day": "Tuesday", 
            "division": "Open",
            "other_identifier": None
        }
        assert result == expected
        
        # Should handle complex title with cleanup
        product_data = {"id": 123, "title": "Big Apple Sports Classic - Kickball - 2025 - Teammate Sign Up"}
        result = self.service.parse_shopify_webhook_for_waitlist_form(product_data)
        
        expected = {
            "product_url": "https://admin.shopify.com/store/09fe59-3/products/123",
            "sport": "Kickball",
                "day": None,
                "division": None,
            "other_identifier": "Sports Classic - Teammate Sign Up"
        }
        assert result == expected
        
        # Should handle multi-sport titles
        product_data = {"id": 456, "title": "Big Apple Kickball and Dodgeball - September tournament"}
        result = self.service.parse_shopify_webhook_for_waitlist_form(product_data)
        
        expected = {
            "product_url": "https://admin.shopify.com/store/09fe59-3/products/456",
            "sport": "Kickball and Dodgeball", 
                "day": None,
                "division": None,
            "other_identifier": "September tournament"
        }
        assert result == expected
        
        # Should parse various complex scenarios correctly
        test_cases = [
            {
                "title": "WEDNESDAY SMALL BALL DODGEBALL - WTNB+ Division - Spring 2025",
                "expected": {
                    "sport": "Dodgeball",
                    "day": "Wednesday",
                    "division": "WTNB+",
                    "other_identifier": "SMALL BALL"
                }
            },
            {
                "title": "Kickball Sunday WTNB Winter",
                "expected": {
                    "sport": "Kickball",
                    "day": "Sunday",
                    "division": "wtnb",
                    "other_identifier": None
                }
            },
            {
                "title": "Random Product Title",  # No sport
                "expected": {
                "sport": None,
                "day": None,
                "division": None,
                    "other_identifier": "Random Product Title"
                }
            }
        ]
        
        for case in test_cases:
            product_data = {"id": 789, "title": case["title"]}
            result = self.service.parse_shopify_webhook_for_waitlist_form(product_data)
            
            # Check each field
            assert result["sport"] == case["expected"]["sport"], f"Sport mismatch for '{case['title']}'"
            assert result["day"] == case["expected"]["day"], f"Day mismatch for '{case['title']}'"
            assert result["division"] == case["expected"]["division"], f"Division mismatch for '{case['title']}'"
            assert result["other_identifier"] == case["expected"]["other_identifier"], f"Other ID mismatch for '{case['title']}'"
            assert result["product_url"] == "https://admin.shopify.com/store/09fe59-3/products/789"

    @patch('requests.post')
    def test_send_to_waitlist_form_gas(self, mock_post):
        """Test sending product data to Google Apps Script waitlist form"""
        # Should succeed when request returns 200
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {'GAS_WAITLIST_FORM_WEB_APP_URL': 'https://test-url.com'}):
            service = WebhooksService()
            product_data = {
                "productUrl": "https://admin.shopify.com/store/09fe59-3/products/123",
                "sport": "dodgeball",
                "day": "monday",
                "division": "open",
                "otherIdentifier": "Fall 2025"
            }
            
            result = service.send_to_waitlist_form_gas(product_data)
            
            assert result["success"] is True
            assert result["response"] == "Success"
            mock_post.assert_called_with(
                'https://test-url.com',
                json=product_data,
                timeout=30
            )
        
        # Should fail when request returns error status (>399)
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {'GAS_WAITLIST_FORM_WEB_APP_URL': 'https://test-url.com'}):
            service = WebhooksService()
            product_data = {"sport": "dodgeball"}
            
            result = service.send_to_waitlist_form_gas(product_data)
            
            assert result["success"] is False
            assert result["error"].startswith("HTTP 5")  # Should be >399
        
        # Should fail when URL is not configured
        result = self.service.send_to_waitlist_form_gas({"sport": "dodgeball"})
        
        assert result["success"] is False
        assert "not configured" in result["error"]


# =============================================================================
# Integration Tests
# =============================================================================
# These tests validate the full orchestration and data flow between components.
# They test that the webhook handler correctly coordinates multiple services
# and handles the complete end-to-end processing pipeline.

    @patch.object(WebhooksService, 'send_to_waitlist_form_gas')
    def test_handle_shopify_webhook(self, mock_send):
        """Test webhook handler integration - orchestration and end-to-end flow"""
        mock_send.return_value = {"success": True, "response": "GAS success"}
        
        # Should skip processing for non-product-update webhooks (topic filtering)
        headers = {"x-shopify-topic": "orders/create"}
        body = b'{"test": "data"}'
        
        result = self.service.handle_shopify_webhook(headers, body)
        
        assert result["success"] is True
        assert result["message"] == "Not a product update webhook"
        mock_send.assert_not_called()
        
        # Should exit early when product still has inventory (inventory check flow)
        headers = {"x-shopify-topic": "products/update"}
        body = json.dumps(self.sample_product_data).encode('utf-8')  # Has inventory = 21
        
        result = self.service.handle_shopify_webhook(headers, body)
        
        assert result["success"] is True
        assert result["message"] == "Product still has inventory"
        mock_send.assert_not_called()
        
        # Should process complete pipeline when product is sold out (end-to-end flow)
        sold_out_product = self.sample_product_data.copy()
        for variant in sold_out_product["variants"]:
            variant["inventory_quantity"] = 0
        
        headers = {"x-shopify-topic": "products/update"}
        body = json.dumps(sold_out_product).encode('utf-8')
        
        result = self.service.handle_shopify_webhook(headers, body)
        
        assert result["success"] is True
        assert result["message"] == "Product sold out, waitlist form updated"
        assert result["parsed_product"]["sport"] == "Dodgeball"  # Now Title case
        mock_send.assert_called_once()
        
        # Should handle invalid JSON gracefully (error handling integration)
        headers = {"x-shopify-topic": "products/update"}
        body = b"invalid-json"
        
        result = self.service.handle_shopify_webhook(headers, body)
        
        assert result["success"] is False
        assert "Invalid JSON" in result["error"]
    
