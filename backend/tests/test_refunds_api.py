"""
Test suite for refunds API endpoint
Tests all three scenarios: success, email mismatch, and order not found
Uses proper mocking to avoid actual API calls to Shopify and Slack
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
import json

from main import app
from models.requests import RefundSlackNotificationRequest

client = TestClient(app)

class TestRefundsAPI:
    """Test suite for the /refunds/send-to-slack endpoint"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.base_payload = {
            "order_number": "12345",
            "requestor_name": {"first": "John", "last": "Doe"},
            "requestor_email": "john.doe@example.com",
            "refund_type": "refund",
            "notes": "Schedule conflict",
            "sheet_link": "https://docs.google.com/spreadsheets/d/test/edit#gid=0&range=A5"
        }
        
        self.mock_order_data = {
            "id": "gid://shopify/Order/123456789",
            "name": "#12345",
            "email": "john.doe@example.com",
            "customer": {
                "email": "john.doe@example.com",
                "firstName": "John",
                "lastName": "Doe"
            },
            "totalPriceV2": {"amount": "150.00", "currencyCode": "USD"},
            "lineItems": {
                "edges": [
                    {
                        "node": {
                            "title": "Fall 2024 Kickball - Tuesday",
                            "quantity": 1,
                            "originalTotalPrice": {"amount": "150.00", "currencyCode": "USD"}
                        }
                    }
                ]
            }
        }
    
    @patch('routers.refunds.orders_service', autospec=True)
    @patch('routers.refunds.slack_service', autospec=True)
    def test_successful_order_validation_and_slack_notification(self, mock_slack_service, mock_orders_service):
        """Test successful order validation with matching email"""
        
        # Mock successful order fetch
        mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": self.mock_order_data
        }
        
        # Mock no existing refunds
        mock_orders_service.check_existing_refunds.return_value = {
            "success": True,
            "existing_refunds": []
        }
        
        # Mock refund calculation
        mock_orders_service.calculate_refund_due.return_value = {
            "success": True,
            "refund_amount": 19.00,
            "message": "Refund calculated successfully"
        }
        
        # Mock customer lookup
        mock_orders_service.shopify_service.get_customer_by_email.return_value = {
            "success": True,
            "customer": {"id": "123", "firstName": "j", "lastName": "r"}
        }
        
        # Mock successful Slack notification
        mock_slack_service.send_refund_request_notification.return_value = {
            "success": True,
            "message": "Refund request sent to Slack successfully"
        }
        
        # Send request
        response = client.post("/refunds/send-to-slack", json=self.base_payload)
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert "Refund request sent to Slack successfully" in response_data["message"]
        
        # Verify orders service was called correctly
        mock_orders_service.fetch_order_details_by_email_or_order_name.assert_called_once_with(
            order_name="12345"
        )
        
        # Verify Slack service was called correctly
        mock_slack_service.send_refund_request_notification.assert_called_once()
        call_args = mock_slack_service.send_refund_request_notification.call_args
        
        # Check that order_data was passed
        assert "order_data" in call_args.kwargs
        assert call_args.kwargs["order_data"]["order"] == self.mock_order_data
        
        # Check requestor_info
        requestor_info = call_args.kwargs["requestor_info"]
        assert requestor_info["name"] == {"first": "John", "last": "Doe"}
        assert requestor_info["email"] == "john.doe@example.com"
        assert requestor_info["refund_type"] == "refund"
        assert requestor_info["notes"] == "Schedule conflict"
        
        # Check sheet_link
        assert call_args.kwargs["sheet_link"] == self.base_payload["sheet_link"]
    
    @patch('routers.refunds.orders_service', autospec=True)
    @patch('routers.refunds.slack_service', autospec=True)
    def test_order_not_found_returns_406(self, mock_slack_service, mock_orders_service):
        """Test 406 response when order is not found in Shopify"""
        
        # Mock order not found
        mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": False,
            "message": "Order #12345 not found in Shopify"
        }
        
        # Mock Slack notification for error case
        mock_slack_service.send_refund_request_notification.return_value = {
            "success": True,
            "message": "Error notification sent to Slack"
        }
        
        # Send request
        response = client.post("/refunds/send-to-slack", json=self.base_payload)
        
        # Verify 406 response
        assert response.status_code == 406
        response_data = response.json()
        assert "Order 12345 not found" in response_data["detail"]
        
        # Verify orders service was called
        mock_orders_service.fetch_order_details_by_email_or_order_name.assert_called_once_with(
            order_name="12345"
        )
        
        # Verify Slack service was called with error_type
        mock_slack_service.send_refund_request_notification.assert_called_once()
        call_args = mock_slack_service.send_refund_request_notification.call_args
        
        assert call_args.kwargs["error_type"] == "order_not_found"
        assert call_args.kwargs["raw_order_number"] == "12345"
        
        # Check requestor_info for error case
        requestor_info = call_args.kwargs["requestor_info"]
        assert requestor_info["name"] == {"first": "John", "last": "Doe"}
        assert requestor_info["email"] == "john.doe@example.com"
    
    @patch('routers.refunds.orders_service', autospec=True)
    @patch('routers.refunds.slack_service', autospec=True)
    def test_email_mismatch_returns_409(self, mock_slack_service, mock_orders_service):
        """Test 409 response when requestor email doesn't match order customer email"""
        
        # Mock order found but with different email
        order_data_different_email = self.mock_order_data.copy()
        order_data_different_email["customer"]["email"] = "different@example.com"
        order_data_different_email["email"] = "different@example.com"
        
        mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": order_data_different_email
        }
        
        # Mock Slack notification for email mismatch
        mock_slack_service.send_refund_request_notification.return_value = {
            "success": True,
            "message": "Email mismatch notification sent to Slack"
        }
        
        # Send request with mismatched email
        payload = self.base_payload.copy()
        payload["requestor_email"] = "wrong@example.com"
        
        response = client.post("/refunds/send-to-slack", json=payload)
        
        # Verify 409 response
        assert response.status_code == 409
        response_data = response.json()
        assert "does not match order customer email" in response_data["detail"]
        assert "wrong@example.com" in response_data["detail"]
        
        # Verify orders service was called
        mock_orders_service.fetch_order_details_by_email_or_order_name.assert_called_once_with(
            order_name="12345"
        )
        
        # Verify Slack service was called with email_mismatch error
        mock_slack_service.send_refund_request_notification.assert_called_once()
        call_args = mock_slack_service.send_refund_request_notification.call_args
        
        assert call_args.kwargs["error_type"] == "email_mismatch"
        assert call_args.kwargs["raw_order_number"] == "12345"
        assert call_args.kwargs["order_customer_email"] == "different@example.com"
        
        # Check order_data includes the found order
        assert "order_data" in call_args.kwargs
        assert call_args.kwargs["order_data"]["order"] == order_data_different_email
    
    def test_invalid_request_payload_returns_422(self):
        """Test validation errors for invalid request payloads"""
        
        # Test missing required field
        invalid_payload = self.base_payload.copy()
        del invalid_payload["order_number"]
        
        response = client.post("/refunds/send-to-slack", json=invalid_payload)
        assert response.status_code == 422
        
        # Test invalid email format
        invalid_payload = self.base_payload.copy()
        invalid_payload["requestor_email"] = "not-an-email"
        
        response = client.post("/refunds/send-to-slack", json=invalid_payload)
        # Note: pydantic doesn't validate email format by default, so this might pass
        # but we can add email validation if needed
    
    def test_requestor_name_variations(self):
        """Test different formats for requestor_name field"""
        
        test_cases = [
            {
                "input": {"first": "John", "last": "Doe"},
                "expected": {"first": "John", "last": "Doe"}
            },
            {
                "input": "John Doe",
                "expected": {"first": "John", "last": "Doe"}
            },
            {
                "input": "SingleName",
                "expected": {"first": "SingleName", "last": ""}
            }
        ]
        
        for test_case in test_cases:
            # Create request object to test validation
            payload = self.base_payload.copy()
            payload["requestor_name"] = test_case["input"]
            
            # Test that the pydantic model validates correctly
            request = RefundSlackNotificationRequest(**payload)
            assert request.requestor_name == test_case["expected"]
    
    @patch('routers.refunds.orders_service', autospec=True)
    @patch('routers.refunds.slack_service', autospec=True)  
    def test_order_number_normalization(self, mock_slack_service, mock_orders_service):
        """Test that order numbers are handled correctly (with/without # prefix)"""
        
        mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": self.mock_order_data
        }
        
        # Mock no existing refunds
        mock_orders_service.check_existing_refunds.return_value = {
            "success": True,
            "existing_refunds": []
        }
        
        # Mock refund calculation
        mock_orders_service.calculate_refund_due.return_value = {
            "success": True,
            "refund_amount": 19.00,
            "message": "Refund calculated successfully"
        }
        
        # Mock customer lookup
        mock_orders_service.shopify_service.get_customer_by_email.return_value = {
            "success": True,
            "customer": {"id": "123", "firstName": "j", "lastName": "r"}
        }
        
        mock_slack_service.send_refund_request_notification.return_value = {
            "success": True,
            "message": "Success"
        }
        
        # Test order number without # prefix
        payload = self.base_payload.copy()
        payload["order_number"] = "12345"
        
        response = client.post("/refunds/send-to-slack", json=payload)
        assert response.status_code == 200
        
        # Verify orders service received the order number as-is
        mock_orders_service.fetch_order_details_by_email_or_order_name.assert_called_with(
            order_name="12345"
        )
        
        # Test order number with # prefix
        mock_orders_service.reset_mock()
        payload["order_number"] = "#12345"
        
        response = client.post("/refunds/send-to-slack", json=payload)
        assert response.status_code == 200
        
        # Verify orders service received the order number with #
        mock_orders_service.fetch_order_details_by_email_or_order_name.assert_called_with(
            order_name="#12345"
        )
    
    @patch('routers.refunds.orders_service', autospec=True)
    @patch('routers.refunds.slack_service', autospec=True)
    def test_orders_service_exception_handling(self, mock_slack_service, mock_orders_service):
        """Test handling of exceptions from orders service"""
        
        # Mock orders service throwing an exception
        mock_orders_service.fetch_order_details_by_email_or_order_name.side_effect = Exception("Shopify API error")
        
        response = client.post("/refunds/send-to-slack", json=self.base_payload)
        
        # Should return 500 internal server error
        assert response.status_code == 500
    
    @patch('routers.refunds.orders_service', autospec=True)
    @patch('routers.refunds.slack_service', autospec=True)
    def test_slack_service_exception_handling(self, mock_slack_service, mock_orders_service):
        """Test handling of exceptions from Slack service"""
        
        # Mock successful order fetch
        mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": self.mock_order_data
        }
        
        # Mock no existing refunds (so we get to Slack call)
        mock_orders_service.check_existing_refunds.return_value = {
            "success": True,
            "existing_refunds": []
        }
        
        # Mock refund calculation
        mock_orders_service.calculate_refund_due.return_value = {
            "success": True,
            "refund_amount": 19.00,
            "message": "Refund calculated successfully"
        }
        
        # Mock customer lookup
        mock_orders_service.shopify_service.get_customer_by_email.return_value = {
            "success": True,
            "customer": {"id": "123", "firstName": "j", "lastName": "r"}
        }
        
        # Mock Slack service throwing an exception
        mock_slack_service.send_refund_request_notification.side_effect = Exception("Slack API error")
        
        response = client.post("/refunds/send-to-slack", json=self.base_payload)
        
        # Should return 500 internal server error
        assert response.status_code == 500
    
    def test_empty_notes_field(self):
        """Test that empty notes field is handled correctly"""
        
        payload = self.base_payload.copy()
        payload["notes"] = ""
        
        # Should validate successfully
        request = RefundSlackNotificationRequest(**payload)
        assert request.notes == ""
    
    def test_optional_sheet_link(self):
        """Test that sheet_link is optional"""
        
        payload = self.base_payload.copy()
        del payload["sheet_link"]
        
        # Should validate successfully
        request = RefundSlackNotificationRequest(**payload)
        assert request.sheet_link is None
        
        # Test with None value
        payload["sheet_link"] = None
        request = RefundSlackNotificationRequest(**payload)
        assert request.sheet_link is None


class TestRefundsAPIIntegration:
    """Integration tests that verify the full request flow"""
    
    @patch('routers.refunds.orders_service', autospec=True)
    @patch('routers.refunds.slack_service', autospec=True)
    def test_full_success_flow_logging(self, mock_slack_service, mock_orders_service):
        """Test that all expected logging occurs during successful flow"""
        
        mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": {
                "id": "gid://shopify/Order/123",
                "name": "#12345",
                "customer": {"email": "test@example.com"}
            }
        }
        
        # Mock no existing refunds
        mock_orders_service.check_existing_refunds.return_value = {
            "success": True,
            "existing_refunds": []
        }
        
        # Mock refund calculation
        mock_orders_service.calculate_refund_due.return_value = {
            "success": True,
            "refund_amount": 19.00,
            "message": "Refund calculated successfully"
        }
        
        # Mock customer lookup
        mock_orders_service.shopify_service.get_customer_by_email.return_value = {
            "success": True,
            "customer": {"id": "123", "firstName": "j", "lastName": "r"}
        }
        
        mock_slack_service.send_refund_request_notification.return_value = {
            "success": True,
            "message": "Success"
        }
        
        payload = {
            "order_number": "12345",
            "requestor_name": "Test User",
            "requestor_email": "test@example.com",
            "refund_type": "credit",
            "notes": "Test request"
        }
        
        with patch('routers.refunds.logger') as mock_logger:
            response = client.post("/refunds/send-to-slack", json=payload)
            
            assert response.status_code == 200
            
            # Verify key log messages were called
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            
            assert any("REFUND REQUEST START" in log for log in log_calls)
            assert any("Order Number: 12345" in log for log in log_calls)
            assert any("Requestor Email: test@example.com" in log for log in log_calls)
            assert any("Processing refund Slack notification for order 12345" in log for log in log_calls)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
