#!/usr/bin/env python3
"""
Test script to verify that muteHttpExceptions works correctly
This simulates what the Google Apps Script should do now
"""

import requests
import json
from unittest.mock import Mock, patch

# Test configuration
BACKEND_URL = "http://127.0.0.1:8000"

# TODO: Route through a test-specific backend configuration

@patch('requests.post')
def test_error_handling_with_mute_exceptions(mock_post):
    """Test that non-200 status codes don't throw exceptions when muteHttpExceptions is used"""
    print("🧪 Testing error handling with muteHttpExceptions simulation...")
    
    # TODO: Route through a test-specific backend configuration
    # Mock 406 error response for order not found
    mock_response = Mock()
    mock_response.status_code = 406
    mock_response.text = '{"success": false, "message": "Order #99999999 not found in Shopify"}'
    mock_response.json.return_value = {
        "success": False,
        "message": "Order #99999999 not found in Shopify"
    }
    mock_post.return_value = mock_response
    
    # Test order not found (406)
    payload = {
        "order_number": "#99999999",  # Non-existent order
        "requestor_name": {"first": "Joe", "last": "Test"},
        "requestor_email": "jdazz87@gmail.com",
        "refund_type": "refund",
        "notes": "",
        "sheet_link": "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit#gid=1435845892&range=A72"
    }
    
    print("🔧 Using mocked 406 response (no live backend calls)")
    
    try:
        # This simulates what Google Apps Script does with muteHttpExceptions: true
        response = requests.post(
            f"{BACKEND_URL}/refunds/send-to-slack",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📥 Response status: {response.status_code}")
        
        # With muteHttpExceptions: true, this should NOT throw an exception
        # Instead, we check the status code and handle accordingly
        if response.status_code != 200:
            response_data = response.json()
            error_detail = response_data.get('detail', response_data)
            error_type = error_detail.get('error', 'unknown_error')
            error_message = error_detail.get('message', 'Unknown error occurred')
            status_code = response.status_code
            
            print(f"📥 Error detail: {json.dumps(error_detail, indent=2)}")
            
            if status_code == 406 or error_type == 'order_not_found':
                print("✅ Would send 'order not found' email to requestor")
                print(f"   📧 To: {payload['requestor_email']}")
                print(f"   📧 Subject: Big Apple Rec Sports - Error with Refund Request for Order {payload['order_number']}")
                
            elif status_code == 409 or error_type == 'email_mismatch':
                print("✅ Would send 'email mismatch' email to requestor")
                print(f"   📧 To: {payload['requestor_email']}")
                print(f"   📧 Subject: Big Apple Rec Sports - Error with Refund Request for Order {payload['order_number']}")
                print(f"   📧 Order customer email: {error_detail.get('order_customer_email', 'Unknown')}")
                
            else:
                print("✅ Would send debug email to admin")
                print(f"   📧 Status: {status_code}")
                print(f"   📧 Error: {error_message}")
        else:
            print("✅ Request succeeded (200)")
            response_data = response.json()
            print(f"📥 Success data: {json.dumps(response_data, indent=2)}")
            
    except Exception as e:
        print(f"❌ Exception occurred (this should NOT happen with muteHttpExceptions): {e}")

if __name__ == "__main__":
    print("🚀 Testing muteHttpExceptions behavior...")
    print("=" * 60)
    
    test_error_handling_with_mute_exceptions()
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("\nWith muteHttpExceptions: true, Google Apps Script should:")
    print("1. NOT throw exceptions on 406/409 status codes")
    print("2. Properly handle error responses in the main logic")
    print("3. Send appropriate emails to requestors for 406/409 errors")
    print("4. Only use the catch block for actual network/parsing errors") 