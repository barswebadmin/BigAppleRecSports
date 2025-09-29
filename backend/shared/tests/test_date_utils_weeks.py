"""
Test for weeks calculation in date_utils
"""

from datetime import datetime, timezone
from backend.shared.date_utils import calculate_weeks_between_dates


class TestCalculateWeeksBetweenDates:
    """Test weeks calculation functionality"""

    def test_calculate_weeks_with_datetime_objects(self):
        """Test with datetime objects"""
        start_date = datetime(2025, 9, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 10, 27, tzinfo=timezone.utc)  # 8 weeks later

        result = calculate_weeks_between_dates(start_date, end_date)
        assert result == 8


