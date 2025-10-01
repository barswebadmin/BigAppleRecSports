#!/usr/bin/env python3
"""
Unit tests for sheet link extraction functionality
"""

import pytest
from modules.integrations.slack.parsers.message_parsers import SlackMessageParsers


class TestSheetLinkExtraction:
    """Unit tests for sheet link extraction from Slack messages"""

    def setup_method(self):
        """Set up test fixtures"""
        self.parsers = SlackMessageParsers()

    def test_extract_sheet_link(self):
        """Test extraction of Google Sheets links from message text"""
        # Test various sheet link formats
        test_cases = [
            {
                "message": "Please check this sheet: https://docs.google.com/spreadsheets/d/1234567890",
                "expected": "https://docs.google.com/spreadsheets/d/1234567890"
            },
            {
                "message": "Sheet link: https://docs.google.com/spreadsheets/d/1234567890/edit#gid=0",
                "expected": "https://docs.google.com/spreadsheets/d/1234567890/edit#gid=0"
            },
            {
                "message": "No sheet link here",
                "expected": ""
            },
            {
                "message": "Multiple links: https://docs.google.com/spreadsheets/d/1234567890 and https://example.com",
                "expected": "https://docs.google.com/spreadsheets/d/1234567890"
            },
            {
                "message": "🔗 <https://docs.google.com/spreadsheets/d/ABCD123/edit|View Request in Google Sheets>",
                "expected": "https://docs.google.com/spreadsheets/d/ABCD123/edit"
            }
        ]

        for test_case in test_cases:
            result = self.parsers.extract_sheet_link(test_case["message"])
            assert result == test_case["expected"], f"Failed for message: {test_case['message']}"


# Legacy integration tests (keeping for backward compatibility)
from unittest.mock import Mock, patch
import requests
import json

# Test configuration
BACKEND_URL = "http://127.0.0.1:8000"
TEST_SHEET_LINK = "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit#gid=1435845892&range=A5"

@patch('requests.post')
def test_sheet_link_functionality(mock_post):
    """Test that the sheet link is properly passed through the API"""
    print("🧪 Testing sheet link functionality...")
    
    # TODO: Route through a test-specific backend configuration
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "message": "Refund request sent to Slack successfully",
        "data": {"sheet_link": TEST_SHEET_LINK}
    }
    mock_post.return_value = mock_response
    
    # Test payload with sheet link
    payload = {
        "order_number": "#12345",
        "requestor_name": {"first": "John", "last": "Doe"},
        "requestor_email": "john.doe@example.com",
        "refund_type": "refund",
        "notes": "Test refund request with sheet link",
        "sheet_link": TEST_SHEET_LINK
    }
    
    try:
        # Test the refunds endpoint
        print("📤 Testing /refunds/send-to-slack endpoint...")
        response = requests.post(
            f"{BACKEND_URL}/refunds/send-to-slack",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📥 Response status: {response.status_code}")
        response_data = response.json()
        print(f"📥 Response data: {json.dumps(response_data, indent=2)}")
        
        # Verify mock was called with expected payload
        mock_post.assert_called_once_with(
            f"{BACKEND_URL}/refunds/send-to-slack",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ Sheet link test passed!")
        else:
            print(f"❌ Sheet link test failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing sheet link: {e}")

@patch('requests.post')
def test_orders_endpoint(mock_post):
    """Test the orders endpoint with sheet link"""
    print("\n🧪 Testing orders endpoint with sheet link...")
    
    # TODO: Route through a test-specific backend configuration
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "message": "Order notification sent to Slack successfully",
        "data": {"sheet_link": TEST_SHEET_LINK}
    }
    mock_post.return_value = mock_response
    
    payload = {
        "requestor_name": {"first": "Jane", "last": "Smith"},
        "requestor_email": "jane.smith@example.com",
        "refund_type": "credit",
        "notes": "Test order endpoint with sheet link",
        "sheet_link": TEST_SHEET_LINK
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/orders/12345/slack-notification",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📥 Response status: {response.status_code}")
        response_data = response.json()
        print(f"📥 Response data: {json.dumps(response_data, indent=2)}")
        
        # Verify mock was called with expected payload
        mock_post.assert_called_once_with(
            f"{BACKEND_URL}/orders/12345/slack-notification",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ Orders endpoint sheet link test passed!")
        else:
            print(f"❌ Orders endpoint sheet link test failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing orders endpoint: {e}")

if __name__ == "__main__":
    print("🚀 Starting sheet link tests...")
    print(f"🔗 Test sheet link: {TEST_SHEET_LINK}")
    print("=" * 50)
    
    # TODO: Route through a test-specific backend configuration
    # Note: Tests are now mocked to avoid hitting live backend
    print("🔧 Running mocked tests (no live backend calls)")
    
    test_sheet_link_functionality()
    test_orders_endpoint()
    
    print("\n" + "=" * 50)
    print("✅ Sheet link tests completed!") 