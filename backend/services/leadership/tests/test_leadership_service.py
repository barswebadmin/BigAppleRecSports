#!/usr/bin/env python3
"""
Test script for Leadership service functionality
"""

from ..leadership_service import LeadershipService

def test_display_text_generation():
    """Test the display text generation with mock data"""
    
    print("🧪 Testing Display Text Generation...")
    
    leadership_service = LeadershipService()
    
    # Mock successful result
    mock_result = {
        "success": True,
        "csv_info": {
            "total_rows": 6,
            "data_rows_count": 5,
            "total_columns": 5,
            "email_columns": [{"name": "Personal Email"}]
        },
        "objects_created": 5,
        "emails_extracted": 4,
        "valid_customers": [
            {"email": "john@example.com", "id": "123", "existing_tags": ["customer"]},
            {"email": "jane@example.com", "id": "456", "existing_tags": []}
        ],
        "invalid_emails": ["invalid-email", ""],
        "year": 2024,
        "year_source": "title",
        "discount_results": [
            {"title": "LeadershipWinter2024100off1", "success": True},
            {"title": "LeadershipSpring2024100off1", "success": True},
            {"title": "LeadershipSummer2024100off1", "success": False, "error": "Test error"}
        ],
        "processing_time": "3.2"
    }
    
    # Generate display text
    display_text = leadership_service.generate_display_text(mock_result)
    
    print("✅ Display text generated successfully!")
    print(f"📝 Length: {len(display_text)} characters")
    print(f"📝 Lines: {len(display_text.split(chr(10)))} lines")
    
    print("\n" + "="*50)
    print("GENERATED DISPLAY TEXT:")
    print("="*50)
    print(display_text)
    print("="*50)
    
    return display_text

def test_error_display_text():
    """Test error case display text generation"""
    print("\n🧪 Testing Error Case...")
    
    leadership_service = LeadershipService()
    
    error_result = {
        "success": False,
        "message": "No valid email addresses found in 'personal email' column"
    }
    
    error_display_text = leadership_service.generate_display_text(error_result)
    print("✅ Error display text generated!")
    print(f"📝 Error text: {error_display_text}")
    
    return error_display_text

if __name__ == "__main__":
    print("🚀 Running Leadership Service Tests...")
    
    test_display_text_generation()
    test_error_display_text()
    
    print("\n🏁 Leadership Service tests completed!") 