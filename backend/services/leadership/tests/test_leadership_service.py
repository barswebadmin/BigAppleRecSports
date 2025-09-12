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
    
    # Assert display text was generated and contains expected content
    assert display_text is not None, "Display text should not be None"
    assert len(display_text) > 0, "Display text should not be empty"
    assert "success" in display_text.lower(), "Display text should indicate success"
    assert "leadership" in display_text.lower(), "Display text should mention leadership"
    assert "2024" in display_text, "Display text should contain the year"
    
    print("\n" + "="*50)
    print("GENERATED DISPLAY TEXT:")
    print("="*50)
    print(display_text)
    print("="*50)

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
    
    # Assert error display text is properly formatted
    assert error_display_text is not None, "Error display text should not be None"
    assert len(error_display_text) > 0, "Error display text should not be empty"
    assert "error" in error_display_text.lower() or "no valid" in error_display_text.lower(), "Error text should indicate an error or issue"

if __name__ == "__main__":
    print("🚀 Running Leadership Service Tests...")
    
    test_display_text_generation()
    test_error_display_text()
    
    print("\n🏁 Leadership Service tests completed!") 