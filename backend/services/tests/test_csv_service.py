#!/usr/bin/env python3
"""
Test script for CSV service functionality
"""

from csv_service import CSVService

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
    
    # Test email extraction
    emails = csv_service.extract_emails_from_objects(objects, "personal email")
    print(f"📧 Extracted {len(emails)} emails from 'personal email' column")
    
    # Display sample object
    if objects:
        print(f"📋 Sample object: {objects[0]}")
    
    # Display extracted emails
    if emails:
        print(f"📧 Extracted emails: {emails}")
    
    print("✅ CSV to objects conversion test completed")
    return objects, emails

def test_csv_info():
    """Test CSV info extraction"""
    print("🧪 Testing CSV Info Extraction...")
    
    csv_service = CSVService()
    csv_info = csv_service.get_csv_info(TEST_CSV_DATA)
    
    print(f"📊 CSV Info: {csv_info}")
    print("✅ CSV info test completed")
    return csv_info

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