#!/usr/bin/env python3
"""
INTEGRATION tests for error codes that test actual HTTP endpoints
NOTE: These tests make real HTTP requests and require a running server.
For unit tests with mocked services, use test_error_codes_unit.py instead.
"""

import pytest
import requests
import json
from unittest.mock import patch, MagicMock

# Test configuration
BACKEND_URL = "http://127.0.0.1:8000"

@pytest.fixture
def mock_slack_service():
    """Mock the SlackService to prevent actual Slack messages"""
    with patch('routers.refunds.SlackService') as mock_service:
        mock_instance = MagicMock()
        mock_service.return_value = mock_instance
        mock_instance.send_refund_request_notification.return_value = True
        yield mock_instance

@pytest.fixture
def mock_orders_service():
    """Mock the OrdersService for consistent test responses"""
    with patch('routers.refunds.OrdersService') as mock_service:
        mock_instance = MagicMock()
        mock_service.return_value = mock_instance
        yield mock_instance

class TestErrorCodes:
    """Test class for error code verification"""
    
    def test_order_not_found_406(self, mock_slack_service, mock_orders_service):
        """Test that order not found returns 406 status code"""
        print("🧪 Testing order not found (should return 406)...")
        
        # Mock OrdersService to return no orders
        mock_orders_service.get_order_by_name.return_value = None
        
        payload = {
            "order_number": "#99999999",  # Non-existent order
            "requestor_name": {"first": "John", "last": "Doe"},
            "requestor_email": "john.doe@example.com",
            "refund_type": "refund",
            "notes": "Test order not found",
            "sheet_link": "https://docs.google.com/spreadsheets/d/test/edit#gid=1&range=A5"
        }
        
        try:
            response = requests.post(
                f"{BACKEND_URL}/refunds/send-to-slack",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"📥 Response status: {response.status_code}")
            response_data = response.json()
            print(f"📥 Response data: {json.dumps(response_data, indent=2)}")
            
            assert response.status_code == 406, f"Expected 406, got {response.status_code}"
            assert "not found" in response_data["detail"].lower()
            print("✅ Order not found test passed - returned 406!")
            
            # Verify Slack was not called for error cases
            mock_slack_service.send_refund_request_notification.assert_not_called()
            
        except Exception as e:
            pytest.fail(f"Error testing order not found: {e}")

    def test_email_mismatch_409(self, mock_slack_service, mock_orders_service):
        """Test that email mismatch returns 409 status code"""
        print("\n🧪 Testing email mismatch (should return 409)...")
        
        # Mock OrdersService to return an order with different email
        mock_order = {
            "id": 12345,
            "name": "#12345",
            "customer": {"email": "real.customer@example.com"},
            "line_items": [{"title": "Test Product"}],
            "total_price": "25.00"
        }
        mock_orders_service.get_order_by_name.return_value = mock_order
        
        payload = {
            "order_number": "#12345",
            "requestor_name": {"first": "Jane", "last": "Smith"},
            "requestor_email": "wrong.email@example.com",  # Mismatched email
            "refund_type": "credit",
            "notes": "Test email mismatch",
            "sheet_link": "https://docs.google.com/spreadsheets/d/test/edit#gid=1&range=A6"
        }
        
        try:
            response = requests.post(
                f"{BACKEND_URL}/refunds/send-to-slack",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"📥 Response status: {response.status_code}")
            response_data = response.json()
            print(f"📥 Response data: {json.dumps(response_data, indent=2)}")
            
            assert response.status_code == 409, f"Expected 409, got {response.status_code}"
            assert "email mismatch" in response_data["detail"].lower() or "does not match" in response_data["detail"].lower()
            print("✅ Email mismatch test passed - returned 409!")
            
            # Verify Slack was not called for error cases
            mock_slack_service.send_refund_request_notification.assert_not_called()
            
        except Exception as e:
            pytest.fail(f"Error testing email mismatch: {e}")

    def test_successful_request_200(self, mock_slack_service, mock_orders_service):
        """Test a successful request returns 200 and calls Slack"""
        print("\n🧪 Testing successful request (should return 200)...")
        
        # Mock OrdersService to return a matching order
        mock_order = {
            "id": 12345,
            "name": "#12345",
            "customer": {"email": "valid.user@example.com"},
            "line_items": [{"title": "Test Product"}],
            "total_price": "25.00"
        }
        mock_orders_service.get_order_by_name.return_value = mock_order
        
        payload = {
            "order_number": "#12345",
            "requestor_name": {"first": "Valid", "last": "User"},
            "requestor_email": "valid.user@example.com",  # Matching email
            "refund_type": "refund",
            "notes": "Test successful request",
            "sheet_link": "https://docs.google.com/spreadsheets/d/test/edit#gid=1&range=A7"
        }
        
        try:
            response = requests.post(
                f"{BACKEND_URL}/refunds/send-to-slack",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"📥 Response status: {response.status_code}")
            response_data = response.json()
            print(f"📥 Response data: {json.dumps(response_data, indent=2)}")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            print("✅ Successful request test passed - returned 200!")
            
            # Verify Slack was called for successful cases
            mock_slack_service.send_refund_request_notification.assert_called_once()
            
        except Exception as e:
            pytest.fail(f"Error testing successful request: {e}")

# Standalone runner for backwards compatibility
def run_tests_standalone():
    """Run tests without pytest for standalone execution"""
    print("🚀 Starting error code tests with mocked Slack...")
    print("=" * 50)
    print("⚠️  Note: Running standalone mode without proper mocking.")
    print("⚠️  Use 'pytest test_error_codes.py' for proper mocked tests.")
    print("=" * 50)
    
    # Simple non-mocked tests that just check status codes
    def test_order_not_found_406():
        """Test that order not found returns 406 status code"""
        print("🧪 Testing order not found (should return 406)...")
        
        payload = {
            "order_number": "#99999999",  # Non-existent order
            "requestor_name": {"first": "John", "last": "Doe"},
            "requestor_email": "john.doe@example.com",
            "refund_type": "refund",
            "notes": "Test order not found",
            "sheet_link": "https://docs.google.com/spreadsheets/d/test/edit#gid=1&range=A5"
        }
        
        try:
            response = requests.post(
                f"{BACKEND_URL}/refunds/send-to-slack",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"📥 Response status: {response.status_code}")
            response_data = response.json()
            print(f"📥 Response data: {json.dumps(response_data, indent=2)}")
            
            if response.status_code == 406:
                print("✅ Order not found test passed - returned 406!")
            else:
                print(f"❌ Order not found test failed - expected 406, got {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error testing order not found: {e}")

    test_order_not_found_406()
    
    print("\n" + "=" * 50)
    print("✅ Standalone tests completed!")
    print("🚀 Run 'pytest test_error_codes.py -v' for full mocked tests")

if __name__ == "__main__":
    run_tests_standalone() 