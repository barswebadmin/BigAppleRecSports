#!/usr/bin/env python3
"""
Unit tests for Leadership Router API endpoints
"""

import pytest
import json
from typing import Dict, Any
from fastapi.testclient import TestClient
from main import app

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

@pytest.fixture
def client():
    """FastAPI test client fixture"""
    return TestClient(app)

def test_health_check(client):
    """Test the health check endpoint"""
    
    print("🧪 Testing Health Check...")
    
    response = client.get("/leadership/health")
    assert response.status_code == 200, f"Health check failed with status {response.status_code}"
    result = response.json()
    print(f"✅ Health check passed: {result}")
    assert result is not None, "Health check response should not be None"

def test_add_tags_endpoint(client):
    """Test the addTags endpoint"""
    
    # Test payload
    payload = {
        "csv_data": TEST_CSV_DATA,
        "spreadsheet_title": "2024 Leadership List",
        "year": 2024
    }
    
    print("🧪 Testing addTags Endpoint...")
    print(f"📤 Sending {len(TEST_CSV_DATA)} rows to endpoint")
    
    response = client.post("/leadership/addTags", json=payload)
    
    print(f"📊 Response Status: {response.status_code}")
    
    assert response.status_code == 200, f"AddTags endpoint failed with status {response.status_code}: {response.text}"
    result = response.json()
    print_api_results(result)
    assert result is not None, "AddTags response should not be None"

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

# Tests are now run via pytest, not directly as script 