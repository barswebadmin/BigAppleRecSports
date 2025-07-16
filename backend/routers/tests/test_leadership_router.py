#!/usr/bin/env python3
"""
Integration tests for Leadership Router API endpoints
"""

import requests
import json
from typing import Dict, Any

# Test data mimicking what Google Sheets would send (with 'Personal Email' column)
TEST_CSV_DATA = [
    ["Personal Email", "First Name", "Last Name", "League", "Team"],
    ["john.doe@gmail.com", "John", "Doe", "Basketball", "Team A"],
    ["jane.smith@yahoo.com", "Jane", "Smith", "Soccer", "Team B"],
    ["invalid-email", "Invalid", "Entry", "Basketball", "Team C"],  # This should be filtered out
    ["", "Empty", "Email", "Soccer", "Team D"],  # This should be filtered out
    ["mike.jones@outlook.com", "Mike", "Jones", "Basketball", "Team E"],
    ["sarah.wilson@gmail.com", "Sarah", "Wilson", "Soccer", "Team F"],
]

def test_health_check():
    """Test the health check endpoint"""
    
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/leadership/health"
    
    print("🧪 Testing Health Check...")
    
    try:
        response = requests.get(endpoint, timeout=10)
        assert response.status_code == 200, f"Health check failed with status {response.status_code}"
        result = response.json()
        print(f"✅ Health check passed: {result}")
        assert result is not None, "Health check response should not be None"
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check request failed: {e}")
        assert False, f"Health check request failed: {e}"

def test_add_tags_endpoint():
    """Test the addTags endpoint"""
    
    # Configuration
    base_url = "http://localhost:8000"  # Local backend
    # base_url = "https://barsbackend.onrender.com"  # Production backend
    
    endpoint = f"{base_url}/leadership/addTags"
    
    # Test payload
    payload = {
        "csv_data": TEST_CSV_DATA,
        "spreadsheet_title": "2024 Leadership List",
        "year": 2024
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print("🧪 Testing addTags Endpoint...")
    print(f"📤 Sending {len(TEST_CSV_DATA)} rows to {endpoint}")
    
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        
        assert response.status_code == 200, f"AddTags endpoint failed with status {response.status_code}: {response.text}"
        result = response.json()
        print_api_results(result)
        assert result is not None, "AddTags response should not be None"
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        assert False, f"AddTags request failed: {e}"

def print_api_results(result: Dict[str, Any]):
    """Pretty print the API results"""
    
    print("\n" + "="*50)
    print("📊 ADD TAGS API RESULTS")
    print("="*50)
    
    # Basic info
    print(f"✅ Success: {result.get('success', False)}")
    if not result.get('success'):
        print(f"❌ Error: {result.get('message', 'Unknown error')}")
        return
    
    # Key metrics
    print(f"📊 Objects Created: {result.get('objects_created', 0)}")
    print(f"📧 Emails Extracted: {result.get('emails_extracted', 0)}")
    print(f"✅ Valid Customers: {len(result.get('valid_customers', []))}")
    print(f"❌ Invalid Emails: {len(result.get('invalid_emails', []))}")
    print(f"📅 Year: {result.get('year', 'Unknown')} ({result.get('year_source', 'unknown')})")
    
    # Test display text
    if result.get('display_text'):
        print(f"\n📝 Display Text Generated: {len(result['display_text'])} characters")
        print("Display Text Preview:")
        preview_lines = result['display_text'].split('\n')[:8]
        for line in preview_lines:
            print(f"   {line}")
        if len(result['display_text'].split('\n')) > 8:
            print("   ... (truncated)")
    
    print("="*50)

if __name__ == "__main__":
    print("🚀 Running Leadership Router Integration Tests...")
    
    # Test health check first
    health_ok = test_health_check()
    
    if health_ok:
        print("\n" + "-"*50)
        # Test main endpoint
        test_add_tags_endpoint()
    else:
        print("❌ Skipping API tests - health check failed")
    
    print("\n🏁 Integration tests completed!") 