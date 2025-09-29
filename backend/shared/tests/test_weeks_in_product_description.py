"""
Simple test for weeks calculation in product description
"""

from backend.shared.date_utils import calculate_weeks_between_dates


def test_weeks_calculation_function():
    """Test the weeks calculation function directly"""

    # Test typical season dates
    start = "2025-09-20T00:00:00Z"
    end = "2025-11-15T00:00:00Z"
    weeks = calculate_weeks_between_dates(start, end)

    assert weeks == 8, f"Expected 8 weeks, got {weeks}"


