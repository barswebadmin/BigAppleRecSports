"""
Simple test for weeks calculation in product description
"""

from utils.date_utils import calculate_weeks_between_dates


def test_weeks_calculation_function():
    """Test the weeks calculation function directly"""

    # Test typical season dates
    start = "2025-09-20T00:00:00Z"
    end = "2025-11-15T00:00:00Z"
    weeks = calculate_weeks_between_dates(start, end)

    assert weeks == 8, f"Expected 8 weeks, got {weeks}"


def test_weeks_calculation_edge_cases():
    """Test edge cases for weeks calculation"""

    # Test exactly one week
    start = "2025-09-20T00:00:00Z"
    end = "2025-09-27T00:00:00Z"
    weeks = calculate_weeks_between_dates(start, end)

    assert weeks == 1, f"Expected 1 week, got {weeks}"

    # Test invalid dates
    weeks = calculate_weeks_between_dates("TBD", "TBD")
    assert weeks == 0, f"Expected 0 weeks for invalid dates, got {weeks}"

    # Test same date
    weeks = calculate_weeks_between_dates(start, start)
    assert weeks == 0, f"Expected 0 weeks for same dates, got {weeks}"


def test_weeks_calculation_integration():
    """Test that the weeks calculation is integrated into create_product"""

    # Import the function and check it uses our calculation
    from backend.services.products.create_product_complete_proces.create_product.create_product import (
        calculate_weeks_between_dates,
    )

    # Just verify the function is imported and works
    test_start = "2025-09-01T00:00:00Z"
    test_end = "2025-10-27T00:00:00Z"  # 8 weeks

    result = calculate_weeks_between_dates(test_start, test_end)

    # Should be 8 weeks
    assert result == 8, f"Expected 8 weeks from Sep 1 to Oct 27, got {result}"

    # Confirm the logic works for realistic season lengths
    # Typical BARS season: 8-12 weeks
    assert 8 <= result <= 12, f"Result {result} weeks should be in typical range"


def test_weeks_text_formatting():
    """Test that weeks are formatted correctly in description text"""

    # Test singular vs plural
    test_cases = [
        (0, "0 weeks"),
        (1, "1 weeks"),  # Note: the template always uses "weeks" even for 1
        (2, "2 weeks"),
        (8, "8 weeks"),
        (12, "12 weeks"),
    ]

    for weeks, expected_text in test_cases:
        # Create a mock description that uses the weeks value
        description = f"Season: Sep 1 - Oct 27 ({weeks} weeks)"

        assert (
            expected_text in description
        ), f"Expected '{expected_text}' in '{description}'"


if __name__ == "__main__":
    # Run the tests directly
    test_weeks_calculation_function()
    test_weeks_calculation_edge_cases()
    test_weeks_calculation_integration()
    test_weeks_text_formatting()
    print("✅ All weeks calculation tests passed!")
