#!/usr/bin/env python3
"""
Test script to verify the sheet link functionality works correctly
"""

import requests
import json

# Test configuration
BACKEND_URL = "http://127.0.0.1:8000"
TEST_SHEET_LINK = "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit#gid=1435845892&range=A5"

def test_sheet_link_functionality():
    """Test that the sheet link is properly passed through the API"""
    print("🧪 Testing sheet link functionality...")
    
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
        
        if response.status_code == 200:
            print("✅ Sheet link test passed!")
        else:
            print(f"❌ Sheet link test failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing sheet link: {e}")

def test_orders_endpoint():
    """Test the orders endpoint with sheet link"""
    print("\n🧪 Testing orders endpoint with sheet link...")
    
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
    
    test_sheet_link_functionality()
    test_orders_endpoint()
    
    print("\n" + "=" * 50)
    print("✅ Sheet link tests completed!") 