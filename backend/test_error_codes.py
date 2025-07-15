#!/usr/bin/env python3
"""
Test script to verify the new error codes work correctly
"""

import requests
import json

# Test configuration
BACKEND_URL = "http://127.0.0.1:8000"

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

def test_email_mismatch_409():
    """Test that email mismatch returns 409 status code"""
    print("\n🧪 Testing email mismatch (should return 409)...")
    
    # This would need a real order number and mismatched email to test properly
    # For now, we'll just show the expected behavior
    payload = {
        "order_number": "#12345",  # Would need real order
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
        
        if response.status_code == 409:
            print("✅ Email mismatch test passed - returned 409!")
        elif response.status_code == 406:
            print("ℹ️ Got 406 (order not found) - expected if test order doesn't exist")
        else:
            print(f"❌ Email mismatch test failed - expected 409, got {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing email mismatch: {e}")

def test_successful_request():
    """Test a successful request (should return 200)"""
    print("\n🧪 Testing successful request (should return 200)...")
    
    # This would need a real order and matching email to test properly
    payload = {
        "order_number": "#12345",
        "requestor_name": {"first": "Valid", "last": "User"},
        "requestor_email": "valid.user@example.com",
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
        
        if response.status_code == 200:
            print("✅ Successful request test passed - returned 200!")
        else:
            print(f"ℹ️ Got {response.status_code} - expected if test order doesn't exist or email doesn't match")
            
    except Exception as e:
        print(f"❌ Error testing successful request: {e}")

if __name__ == "__main__":
    print("🚀 Starting error code tests...")
    print("=" * 50)
    
    test_order_not_found_406()
    test_email_mismatch_409()
    test_successful_request()
    
    print("\n" + "=" * 50)
    print("✅ Error code tests completed!")
    print("\nNOTE: To fully test email mismatch (409), you would need:")
    print("1. A real order number that exists in Shopify")
    print("2. An email that doesn't match the order's customer email")
    print("3. The backend API running with valid Shopify credentials") 