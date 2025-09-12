#!/usr/bin/env python3
"""
Test script for CSV service functionality
"""

from ..csv_service import CSVService

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

def test_csv_to_objects():
    """Test the CSV to objects conversion"""
    print("🧪 Testing CSV to Objects Conversion...")
    
    csv_service = CSVService()
    
    # Test the conversion
    objects = csv_service.process_csv_input(TEST_CSV_DATA)
    print(f"📊 Converted {len(objects)} rows to objects")
    
    # Assert we got the expected number of objects (all data rows, filtering happens later)
    assert len(objects) == 6, f"Expected 6 objects (all data rows), got {len(objects)}"
    
    # Test email extraction
    emails = csv_service.extract_emails_from_objects(objects, "personal email")
    print(f"📧 Extracted {len(emails)} emails from 'personal email' column")
    
    # Assert we extracted the expected number of emails
    assert len(emails) == 4, f"Expected 4 valid emails, got {len(emails)}"
    
    # Display sample object
    if objects:
        print(f"📋 Sample object: {objects[0]}")
        # Assert the first object has expected structure
        assert "Personal Email" in objects[0], "Object should contain 'Personal Email' field"
    
    # Display extracted emails
    if emails:
        print(f"📧 Extracted emails: {emails}")
        # Assert all extracted emails are valid
        for email in emails:
            assert "@" in email, f"Invalid email format: {email}"
    
    print("✅ CSV to objects conversion test completed")

def test_csv_info():
    """Test CSV info extraction"""
    print("🧪 Testing CSV Info Extraction...")
    
    csv_service = CSVService()
    csv_info = csv_service.get_csv_info(TEST_CSV_DATA)
    
    print(f"📊 CSV Info: {csv_info}")
    
    # Assert CSV info contains expected fields
    assert "total_rows" in csv_info, "CSV info should contain total_rows"
    assert "data_rows_count" in csv_info, "CSV info should contain data_rows_count"
    assert "total_columns" in csv_info, "CSV info should contain total_columns"
    assert "email_columns" in csv_info, "CSV info should contain email_columns"
    
    # Assert expected values
    assert csv_info["total_rows"] == 7, f"Expected 7 total rows, got {csv_info['total_rows']}"
    assert csv_info["data_rows_count"] == 6, f"Expected 6 data rows, got {csv_info['data_rows_count']}"
    assert csv_info["total_columns"] == 5, f"Expected 5 columns, got {csv_info['total_columns']}"
    
    print("✅ CSV info test completed")

def test_year_extraction():
    """Test year extraction from titles"""
    print("🧪 Testing Year Extraction...")
    
    csv_service = CSVService()
    
    test_titles = [
        "2024 Leadership List",
        "Leadership 2025 Data", 
        "Random Title",
        "2023-Leadership-Final"
    ]
    
    for title in test_titles:
        year = csv_service.extract_year_from_title(title)
        print(f"📅 '{title}' -> {year}")
    
    print("✅ Year extraction test completed")

if __name__ == "__main__":
    print("🚀 Running CSV Service Tests...")
    
    test_csv_to_objects()
    print("\n" + "-"*50)
    
    test_csv_info()
    print("\n" + "-"*50)
    
    test_year_extraction()
    
    print("\n🏁 CSV Service tests completed!") 