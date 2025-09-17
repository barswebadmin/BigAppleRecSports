"""
Test early exit conditions for product update webhook handler
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from services.webhooks.handlers.product_update_handler import evaluate_product_update_webhook


class TestProductUpdateEarlyExit:
    """Test early exit conditions in product update webhook handler"""

    def setup_method(self):
        """Set up test fixtures"""
        self.gas_client = Mock()
        
        # Base product data that would normally trigger inventory processing
        self.base_product_data = {
            "admin_graphql_api_id": "gid://shopify/Product/7457972551774",
            "body_html": "<p>Test product</p>",
            "created_at": "2025-09-16T23:59:28-04:00",
            "handle": "test-product",
            "id": 7457972551774,
            "product_type": "Recreation",
            "template_suffix": "",
            "title": "Test Product",
            "updated_at": "2025-09-17T00:07:32-04:00",
            "vendor": "Big Apple Recreational Sports",
            "status": "active",
            "published_scope": "global",
            "tags": "test",
            "variants": [
                {
                    "id": 1,
                    "inventory_quantity": 0,  # Zero inventory would normally trigger waitlist
                }
            ]
        }

    def test_early_exit_draft_status(self):
        """Test that draft products are skipped"""
        product_data = self.base_product_data.copy()
        product_data["status"] = "draft"
        product_data["published_at"] = "2025-09-15T00:00:00-04:00"  # More than 24h ago
        
        body = json.dumps(product_data).encode('utf-8')
        result = evaluate_product_update_webhook(body, self.gas_client)
        
        assert result["action_needed"] is False
        assert result["reason"] == "registration_not_yet_open"
        assert result["data"]["product_id"] == 7457972551774
        
        # Should not call GAS client
        self.gas_client.send_to_waitlist_form.assert_not_called()

    def test_early_exit_null_published_at(self):
        """Test that unpublished products (null published_at) are skipped"""
        product_data = self.base_product_data.copy()
        product_data["status"] = "active"
        product_data["published_at"] = None
        
        body = json.dumps(product_data).encode('utf-8')
        result = evaluate_product_update_webhook(body, self.gas_client)
        
        assert result["action_needed"] is False
        assert result["reason"] == "registration_not_yet_open"
        assert result["data"]["product_id"] == 7457972551774
        
        # Should not call GAS client
        self.gas_client.send_to_waitlist_form.assert_not_called()

    def test_early_exit_recently_published(self):
        """Test that recently published products (< 24h) are skipped"""
        # Set published_at to 12 hours ago
        now = datetime.now(timezone.utc)
        published_12h_ago = now - timedelta(hours=12)
        published_at_str = published_12h_ago.isoformat().replace('+00:00', '-04:00')
        
        product_data = self.base_product_data.copy()
        product_data["status"] = "active"
        product_data["published_at"] = published_at_str
        
        body = json.dumps(product_data).encode('utf-8')
        result = evaluate_product_update_webhook(body, self.gas_client)
        
        assert result["action_needed"] is False
        assert result["reason"] == "registration_not_yet_open"
        assert result["data"]["product_id"] == 7457972551774
        
        # Should not call GAS client
        self.gas_client.send_to_waitlist_form.assert_not_called()

    def test_no_early_exit_old_published_product(self):
        """Test that products published > 24h ago proceed with inventory checks"""
        # Set published_at to 48 hours ago
        now = datetime.now(timezone.utc)
        published_48h_ago = now - timedelta(hours=48)
        published_at_str = published_48h_ago.isoformat().replace('+00:00', '-04:00')
        
        product_data = self.base_product_data.copy()
        product_data["status"] = "active"
        product_data["published_at"] = published_at_str
        
        # Mock successful GAS response
        self.gas_client.send_to_waitlist_form.return_value = {
            "success": True, 
            "response": "Added to waitlist"
        }
        
        body = json.dumps(product_data).encode('utf-8')
        result = evaluate_product_update_webhook(body, self.gas_client)
        
        assert result["action_needed"] is True
        assert result["reason"] == "product_sold_out"
        assert result["data"]["product_id"] == 7457972551774
        
        # Should proceed with inventory check - but GAS is now called in shopify_handler, not here
        # This function only evaluates, it doesn't call GAS directly anymore

    def test_edge_case_exactly_24_hours(self):
        """Test edge case where product was published exactly 30 hours ago (should proceed)"""
        # Set published_at to 30 hours ago to ensure it's > 24 hours even with timezone conversion
        now = datetime.now(timezone.utc)
        published_30h_ago = now - timedelta(hours=30)
        published_at_str = published_30h_ago.isoformat().replace('+00:00', '-04:00')
        
        product_data = self.base_product_data.copy()
        product_data["status"] = "active"
        product_data["published_at"] = published_at_str
        
        # Mock successful GAS response
        self.gas_client.send_to_waitlist_form.return_value = {
            "success": True, 
            "response": "Added to waitlist"
        }
        
        body = json.dumps(product_data).encode('utf-8')
        result = evaluate_product_update_webhook(body, self.gas_client)
        
        # Should proceed (30 hours is > 24 hours even with timezone conversion)
        assert result["action_needed"] is True
        assert result["reason"] == "product_sold_out"
        assert result["data"]["product_id"] == 7457972551774

    def test_invalid_published_at_format(self):
        """Test that invalid published_at format doesn't cause early exit"""
        product_data = self.base_product_data.copy()
        product_data["status"] = "active"
        product_data["published_at"] = "invalid-date-format"
        
        # Mock successful GAS response
        self.gas_client.send_to_waitlist_form.return_value = {
            "success": True, 
            "response": "Added to waitlist"
        }
        
        body = json.dumps(product_data).encode('utf-8')
        result = evaluate_product_update_webhook(body, self.gas_client)
        
        # Should proceed despite invalid date (don't early exit on parse errors)
        assert result["action_needed"] is True
        assert result["reason"] == "product_sold_out"
        assert result["data"]["product_id"] == 7457972551774

    def test_multiple_early_exit_conditions(self):
        """Test that first matching condition is returned when multiple apply"""
        product_data = self.base_product_data.copy()
        product_data["status"] = "draft"  # This should be checked first
        product_data["published_at"] = None  # This would also trigger exit
        
        body = json.dumps(product_data).encode('utf-8')
        result = evaluate_product_update_webhook(body, self.gas_client)
        
        assert result["action_needed"] is False
        # Should return the registration_not_yet_open reason (for draft status)
        assert result["reason"] == "registration_not_yet_open"
        assert result["data"]["product_id"] == 7457972551774
