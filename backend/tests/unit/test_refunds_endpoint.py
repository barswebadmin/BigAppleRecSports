#!/usr/bin/env python3
"""
Comprehensive tests for refunds endpoint and JSON schema validation.
Tests the exact JSON format that comes from the Google Apps Script frontend.
"""

import os
import sys
import pytest
import json
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from pydantic import ValidationError

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from main import app
from routers.refunds import RefundSlackNotificationRequest

client = TestClient(app)

class TestRefundsEndpointJSONValidation:
    """Test suite for refunds endpoint JSON schema validation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # The exact JSON format that comes from the Google Apps Script
        self.valid_refund_request = {
            "order_number": "42234",
            "requestor_name": {
                "first": "j",
                "last": "r"
            },
            "requestor_email": "jdazz87@gmail.com",
            "refund_type": "refund",
            "notes": "",
            "sheet_link": "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit#gid=1435845892&range=A93"
        }
        
        # Valid alternative with "credit" type
        self.valid_credit_request = {
            "order_number": "42234",
            "requestor_name": {
                "first": "jane",
                "last": "doe"
            },
            "requestor_email": "jane.doe@example.com",
            "refund_type": "credit",
            "notes": "Requested store credit instead of refund",
            "sheet_link": "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit#gid=1435845892&range=A94"
        }
    
    def test_pydantic_model_validation_valid_refund(self):
        """Test that RefundSlackNotificationRequest accepts valid refund JSON"""
        # Test the exact JSON from the frontend
        request = RefundSlackNotificationRequest(**self.valid_refund_request)
        
        assert request.order_number == "42234"
        assert request.requestor_name["first"] == "j"
        assert request.requestor_name["last"] == "r"
        assert request.requestor_email == "jdazz87@gmail.com"
        assert request.refund_type == "refund"
        assert request.notes == ""
        assert "11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw" in request.sheet_link
    
    def test_pydantic_model_validation_valid_credit(self):
        """Test that RefundSlackNotificationRequest accepts valid credit JSON"""
        request = RefundSlackNotificationRequest(**self.valid_credit_request)
        
        assert request.order_number == "42234"
        assert request.requestor_name["first"] == "jane"
        assert request.requestor_name["last"] == "doe"
        assert request.requestor_email == "jane.doe@example.com"
        assert request.refund_type == "credit"
        assert request.notes == "Requested store credit instead of refund"
    
    def test_pydantic_model_validation_missing_required_fields(self):
        """Test that RefundSlackNotificationRequest rejects missing required fields"""
        # Test missing order_number
        invalid_request = self.valid_refund_request.copy()
        del invalid_request["order_number"]
        
        with pytest.raises(ValidationError) as exc_info:
            RefundSlackNotificationRequest(**invalid_request)
        assert "order_number" in str(exc_info.value)
        
        # Test missing requestor_name
        invalid_request = self.valid_refund_request.copy()
        del invalid_request["requestor_name"]
        
        with pytest.raises(ValidationError) as exc_info:
            RefundSlackNotificationRequest(**invalid_request)
        assert "requestor_name" in str(exc_info.value)
        
        # Test missing requestor_email
        invalid_request = self.valid_refund_request.copy()
        del invalid_request["requestor_email"]
        
        with pytest.raises(ValidationError) as exc_info:
            RefundSlackNotificationRequest(**invalid_request)
        assert "requestor_email" in str(exc_info.value)
        
        # Test missing refund_type
        invalid_request = self.valid_refund_request.copy()
        del invalid_request["refund_type"]
        
        with pytest.raises(ValidationError) as exc_info:
            RefundSlackNotificationRequest(**invalid_request)
        assert "refund_type" in str(exc_info.value)
    
    def test_pydantic_model_validation_invalid_refund_type(self):
        """Test that RefundSlackNotificationRequest rejects invalid refund_type"""
        invalid_request = self.valid_refund_request.copy()
        invalid_request["refund_type"] = "invalid_type"
        
        with pytest.raises(ValidationError) as exc_info:
            RefundSlackNotificationRequest(**invalid_request)
        assert "refund_type" in str(exc_info.value)
    
    def test_pydantic_model_validation_invalid_email_format(self):
        """Test that RefundSlackNotificationRequest rejects invalid email format"""
        invalid_request = self.valid_refund_request.copy()
        invalid_request["requestor_email"] = "not-an-email"
        
        with pytest.raises(ValidationError) as exc_info:
            RefundSlackNotificationRequest(**invalid_request)
        assert "requestor_email" in str(exc_info.value)
    
    def test_pydantic_model_validation_incomplete_requestor_name(self):
        """Test that RefundSlackNotificationRequest handles incomplete requestor_name gracefully"""
        # Missing first name - should default to empty string
        request_missing_first = self.valid_refund_request.copy()
        request_missing_first["requestor_name"] = {"last": "r"}
        
        request = RefundSlackNotificationRequest(**request_missing_first)
        assert request.requestor_name["first"] == ""
        assert request.requestor_name["last"] == "r"
        
        # Missing last name - should default to empty string
        request_missing_last = self.valid_refund_request.copy()
        request_missing_last["requestor_name"] = {"first": "j"}
        
        request = RefundSlackNotificationRequest(**request_missing_last)
        assert request.requestor_name["first"] == "j"
        assert request.requestor_name["last"] == ""
    
    def test_pydantic_model_optional_fields(self):
        """Test that optional fields (notes, sheet_link) can be omitted"""
        # Test without notes
        request_without_notes = self.valid_refund_request.copy()
        del request_without_notes["notes"]
        
        request = RefundSlackNotificationRequest(**request_without_notes)
        assert request.notes is None
        
        # Test without sheet_link
        request_without_sheet_link = self.valid_refund_request.copy()
        del request_without_sheet_link["sheet_link"]
        
        request = RefundSlackNotificationRequest(**request_without_sheet_link)
        assert request.sheet_link is None
        
        # Test without both optional fields
        minimal_request = {
            "order_number": "42234",
            "requestor_name": {"first": "j", "last": "r"},
            "requestor_email": "jdazz87@gmail.com",
            "refund_type": "refund"
        }
        
        request = RefundSlackNotificationRequest(**minimal_request)
        assert request.notes is None
        assert request.sheet_link is None

class TestRefundsEndpointIntegration:
    """Test the /refunds/send-to-slack endpoint with mocked dependencies"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.valid_request_data = {
            "order_number": "42234",
            "requestor_name": {
                "first": "j",
                "last": "r"
            },
            "requestor_email": "jdazz87@gmail.com",
            "refund_type": "refund",
            "notes": "",
            "sheet_link": "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit#gid=1435845892&range=A93"
        }
        
        self.mock_order_data = {
            "id": "gid://shopify/Order/5875167625310",
            "name": "#42234",
            "customer": {
                "id": "gid://shopify/Customer/7103723110494",
                "email": "jdazz87@gmail.com"
            },
            "total_price": "2.0"
        }
    
    @patch('routers.refunds.slack_service')
    @patch('routers.refunds.orders_service')
    def test_refunds_endpoint_success_flow(self, mock_orders_service, mock_slack_service):
        """Test complete success flow: order found, email matches, Slack sent"""
        # Mock successful order fetch
        mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": self.mock_order_data
        }
        
        # Mock successful Slack notification
        mock_slack_service.send_refund_request_notification.return_value = {
            "success": True,
            "message": "Notification sent successfully"
        }
        
        response = client.post("/refunds/send-to-slack", json=self.valid_request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "successfully sent to Slack" in data["message"]
        
        # Verify order was fetched with correct order number
        mock_orders_service.fetch_order_details_by_email_or_order_name.assert_called_once_with(
            order_name="42234"
        )
        
        # Verify Slack notification was sent
        mock_slack_service.send_refund_request_notification.assert_called_once()
    
    @patch('routers.refunds.slack_service')
    @patch('routers.refunds.orders_service')
    def test_refunds_endpoint_order_not_found(self, mock_orders_service, mock_slack_service):
        """Test order not found scenario"""
        # Mock order not found
        mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": False,
            "message": "Order 42234 not found in Shopify"
        }
        
        # Mock successful Slack notification for error case
        mock_slack_service.send_refund_request_notification.return_value = {
            "success": True,
            "message": "Error notification sent"
        }
        
        response = client.post("/refunds/send-to-slack", json=self.valid_request_data)
        
        assert response.status_code == 200  # Should still return 200 since error was handled
        data = response.json()
        assert data["success"] is True  # Success because error was handled properly
        assert "Order not found" in data["message"]
        
        # Verify error notification was sent to Slack
        mock_slack_service.send_refund_request_notification.assert_called_once()
        call_args = mock_slack_service.send_refund_request_notification.call_args
        assert call_args.kwargs["error_type"] == "order_not_found"
    
    @patch('routers.refunds.slack_service')
    @patch('routers.refunds.orders_service')
    def test_refunds_endpoint_email_mismatch(self, mock_orders_service, mock_slack_service):
        """Test email mismatch scenario"""
        # Mock order found but with different email
        order_with_different_email = self.mock_order_data.copy()
        order_with_different_email["customer"]["email"] = "different@email.com"
        
        mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": order_with_different_email
        }
        
        # Mock successful Slack notification for error case
        mock_slack_service.send_refund_request_notification.return_value = {
            "success": True,
            "message": "Error notification sent"
        }
        
        response = client.post("/refunds/send-to-slack", json=self.valid_request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "email does not match" in data["message"]
        
        # Verify error notification was sent to Slack
        mock_slack_service.send_refund_request_notification.assert_called_once()
        call_args = mock_slack_service.send_refund_request_notification.call_args
        assert call_args.kwargs["error_type"] == "email_mismatch"
    
    def test_refunds_endpoint_invalid_json_schema(self):
        """Test endpoint rejects invalid JSON schema"""
        # Test missing required field
        invalid_data = self.valid_request_data.copy()
        del invalid_data["order_number"]
        
        response = client.post("/refunds/send-to-slack", json=invalid_data)
        
        assert response.status_code == 422  # Unprocessable Entity
        assert "order_number" in response.json()["detail"][0]["loc"]
    
    def test_refunds_endpoint_invalid_json_structure(self):
        """Test endpoint rejects malformed JSON"""
        response = client.post(
            "/refunds/send-to-slack", 
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

class TestRefundsEndpointRealWorldScenarios:
    """Test real-world scenarios based on actual usage"""
    
    def test_exact_frontend_json_format(self):
        """Test the exact JSON format that was failing in the original issue"""
        frontend_json = {
            "order_number": "42234",
            "requestor_name": {
                "first": "j",
                "last": "r"
            },
            "requestor_email": "jdazz87@gmail.com", 
            "refund_type": "refund",
            "notes": "",
            "sheet_link": "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit#gid=1435845892&range=A93"
        }
        
        # Should not raise validation error
        request = RefundSlackNotificationRequest(**frontend_json)
        assert request.order_number == "42234"
        assert request.requestor_email == "jdazz87@gmail.com"
        
    def test_frontend_json_with_longer_names(self):
        """Test with longer, more realistic names"""
        frontend_json = {
            "order_number": "12345",
            "requestor_name": {
                "first": "Jonathan",
                "last": "Randazzo"
            },
            "requestor_email": "jonathan.randazzo@example.com",
            "refund_type": "credit",
            "notes": "Customer prefers store credit for faster processing",
            "sheet_link": "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit#gid=1435845892&range=A150"
        }
        
        request = RefundSlackNotificationRequest(**frontend_json)
        assert request.requestor_name.first == "Jonathan"
        assert request.requestor_name.last == "Randazzo"
        assert request.refund_type == "credit"
    
    def test_edge_cases_empty_notes(self):
        """Test edge case with empty notes field"""
        frontend_json = {
            "order_number": "99999",
            "requestor_name": {
                "first": "Test",
                "last": "User"
            },
            "requestor_email": "test@test.com",
            "refund_type": "refund",
            "notes": "",  # Empty string
            "sheet_link": None  # Null value
        }
        
        request = RefundSlackNotificationRequest(**frontend_json)
        assert request.notes == ""
        assert request.sheet_link is None

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
