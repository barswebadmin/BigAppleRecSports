"""
Tests for Order Create Webhook Handler

Tests order creation webhook processing, specifically email mismatch detection
and waitlist registration identification.
"""

import pytest
import json
from typing import Dict, Any
from new_structure_target.services.webhooks.handlers.order_create_handler import evaluate_order_create_webhook


class TestOrderCreateHandler:
    """Test cases for order create webhook handler"""

    def create_base_order_payload(self) -> Dict[str, Any]:
        """Create a base order payload for testing"""
        return {
            "admin_graphql_api_id": "gid://shopify/Order/5885712466014",
            "contact_email": "jdazz87@gmail.com",
            "created_at": "2025-09-16T23:00:31-04:00",
            "order_number": 43048,
            "customer": {
                "first_name": "Joe",
                "last_name": "Randazzo"
            },
            "line_items": [
                {
                    "properties": [
                        {
                            "name": "_Form Fields",
                            "value": " "
                        },
                        {
                            "name": "Best Contact Email Address:",
                            "value": "jprandazzo@icloud.com"
                        },
                        {
                            "name": "Just a test",
                            "value": "testtest"
                        }
                    ],
                    "title": "joe test product - dodgeball",
                    "variant_title": "Coming off Waitlist Reg",
                }
            ],
        }

    def test_email_mismatch_detected(self):
        """Test that email mismatch is correctly detected"""
        order_data = self.create_base_order_payload()
        # contact_email: "jdazz87@gmail.com"
        # form_email: "jprandazzo@icloud.com" 
        # These should be different -> mismatch = True
        
        body = json.dumps(order_data).encode('utf-8')
        result = evaluate_order_create_webhook(body)
        
        assert result["success"] is True
        assert result["is_email_mismatch"] is True
        assert result["contact_email"] == "jdazz87@gmail.com"
        assert result["form_email"] == "jprandazzo@icloud.com"
        assert "email mismatch detected" in result["message"].lower()

    def test_no_email_mismatch(self):
        """Test that matching emails are correctly identified"""
        order_data = self.create_base_order_payload()
        
        # Make emails match
        order_data["contact_email"] = "jprandazzo@icloud.com"
        # form_email is already "jprandazzo@icloud.com"
        
        body = json.dumps(order_data).encode('utf-8')
        result = evaluate_order_create_webhook(body)
        
        assert result["success"] is True
        assert result["is_email_mismatch"] is False
        assert result["contact_email"] == "jprandazzo@icloud.com"
        assert result["form_email"] == "jprandazzo@icloud.com"

    def test_waitlist_registration_detected(self):
        """Test that waitlist registration is correctly detected"""
        order_data = self.create_base_order_payload()
        # variant_title: "Coming off Waitlist Reg" contains "waitlist"
        
        body = json.dumps(order_data).encode('utf-8')
        result = evaluate_order_create_webhook(body)
        
        assert result["success"] is True
        assert result["is_waitlist_registration"] is True
        assert result["variant_title"] == "Coming off Waitlist Reg"
        assert "waitlist registration" in result["message"].lower()

    def test_no_waitlist_registration(self):
        """Test that non-waitlist registrations are correctly identified"""
        order_data = self.create_base_order_payload()
        
        # Change variant_title to not contain "waitlist"
        order_data["line_items"][0]["variant_title"] = "Regular Registration"
        
        body = json.dumps(order_data).encode('utf-8')
        result = evaluate_order_create_webhook(body)
        
        assert result["success"] is True
        assert result["is_waitlist_registration"] is False
        assert result["variant_title"] == "Regular Registration"

    def test_email_mismatch_and_waitlist_registration(self):
        """Test both email mismatch and waitlist registration detected together"""
        order_data = self.create_base_order_payload()
        # Default payload has both conditions true
        
        body = json.dumps(order_data).encode('utf-8')
        result = evaluate_order_create_webhook(body)
        
        assert result["success"] is True
        assert result["is_email_mismatch"] is True
        assert result["is_waitlist_registration"] is True
        assert "email mismatch" in result["message"].lower()
        assert "waitlist registration" in result["message"].lower()

    def test_neither_condition_true(self):
        """Test when neither email mismatch nor waitlist registration is detected"""
        order_data = self.create_base_order_payload()
        
        # Make emails match
        order_data["contact_email"] = "jprandazzo@icloud.com"
        # Remove waitlist from variant title
        order_data["line_items"][0]["variant_title"] = "Regular Registration"
        
        body = json.dumps(order_data).encode('utf-8')
        result = evaluate_order_create_webhook(body)
        
        assert result["success"] is True
        assert result["is_email_mismatch"] is False
        assert result["is_waitlist_registration"] is False
        assert "standard order" in result["message"].lower()

    def test_no_email_property_found(self):
        """Test behavior when no email property is found in line items"""
        order_data = self.create_base_order_payload()
        
        # Remove email property
        order_data["line_items"][0]["properties"] = [
            {
                "name": "_Form Fields",
                "value": " "
            },
            {
                "name": "Just a test",
                "value": "testtest"
            }
        ]
        
        body = json.dumps(order_data).encode('utf-8')
        result = evaluate_order_create_webhook(body)
        
        assert result["success"] is True
        assert result["is_email_mismatch"] is False  # No form email means no mismatch
        assert result["form_email"] is None
        assert result["contact_email"] == "jdazz87@gmail.com"

    def test_multiple_email_properties(self):
        """Test behavior when multiple email properties exist"""
        order_data = self.create_base_order_payload()
        
        # Add another email property
        order_data["line_items"][0]["properties"].append({
            "name": "Secondary Email Address",
            "value": "secondary@example.com"
        })
        
        body = json.dumps(order_data).encode('utf-8')
        result = evaluate_order_create_webhook(body)
        
        assert result["success"] is True
        # Should find the first email property
        assert result["form_email"] == "jprandazzo@icloud.com"

    def test_case_insensitive_email_detection(self):
        """Test that email detection is case insensitive"""
        order_data = self.create_base_order_payload()
        
        # Change property name to different case
        order_data["line_items"][0]["properties"][1]["name"] = "BEST CONTACT EMAIL ADDRESS:"
        
        body = json.dumps(order_data).encode('utf-8')
        result = evaluate_order_create_webhook(body)
        
        assert result["success"] is True
        assert result["form_email"] == "jprandazzo@icloud.com"

    def test_case_insensitive_waitlist_detection(self):
        """Test that waitlist detection is case insensitive"""
        order_data = self.create_base_order_payload()
        
        # Change variant title to different case
        order_data["line_items"][0]["variant_title"] = "Coming off WAITLIST Reg"
        
        body = json.dumps(order_data).encode('utf-8')
        result = evaluate_order_create_webhook(body)
        
        assert result["success"] is True
        assert result["is_waitlist_registration"] is True

    def test_invalid_json_payload(self):
        """Test handling of invalid JSON payload"""
        invalid_body = b"invalid json content"
        result = evaluate_order_create_webhook(invalid_body)
        
        assert result["success"] is False
        assert "Invalid JSON payload" in result["error"]

    def test_missing_line_items(self):
        """Test behavior when line_items are missing"""
        order_data = self.create_base_order_payload()
        del order_data["line_items"]
        
        body = json.dumps(order_data).encode('utf-8')
        result = evaluate_order_create_webhook(body)
        
        assert result["success"] is True
        assert result["is_email_mismatch"] is False
        assert result["is_waitlist_registration"] is False
        assert result["form_email"] is None
        assert result["variant_title"] is None

    def test_empty_line_items(self):
        """Test behavior when line_items array is empty"""
        order_data = self.create_base_order_payload()
        order_data["line_items"] = []
        
        body = json.dumps(order_data).encode('utf-8')
        result = evaluate_order_create_webhook(body)
        
        assert result["success"] is True
        assert result["is_email_mismatch"] is False
        assert result["is_waitlist_registration"] is False
        assert result["form_email"] is None
        assert result["variant_title"] is None

    def test_missing_properties_in_line_item(self):
        """Test behavior when properties are missing from line item"""
        order_data = self.create_base_order_payload()
        del order_data["line_items"][0]["properties"]
        
        body = json.dumps(order_data).encode('utf-8')
        result = evaluate_order_create_webhook(body)
        
        assert result["success"] is True
        assert result["is_email_mismatch"] is False
        assert result["form_email"] is None
        # Should still detect waitlist from variant_title
        assert result["is_waitlist_registration"] is True
