"""
Test for weeks calculation in date_utils
"""

from datetime import datetime, timezone
from utils.date_utils import calculate_weeks_between_dates


class TestCalculateWeeksBetweenDates:
    """Test weeks calculation functionality"""

    def test_calculate_weeks_with_datetime_objects(self):
        """Test with datetime objects"""
        start_date = datetime(2025, 9, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 10, 27, tzinfo=timezone.utc)  # 8 weeks later

        result = calculate_weeks_between_dates(start_date, end_date)
        assert result == 8

    def test_calculate_weeks_with_string_dates(self):
        """Test with ISO string dates"""
        start_date = "2025-09-01T00:00:00Z"
        end_date = "2025-10-27T00:00:00Z"  # 8 weeks later

        result = calculate_weeks_between_dates(start_date, end_date)
        assert result == 8

    def test_calculate_weeks_mixed_types(self):
        """Test with mixed datetime and string"""
        start_date = datetime(2025, 9, 1, tzinfo=timezone.utc)
        end_date = "2025-09-15T00:00:00Z"  # 2 weeks later

        result = calculate_weeks_between_dates(start_date, end_date)
        assert result == 2

    def test_calculate_weeks_exact_weeks(self):
        """Test with exact week boundaries"""
        start_date = "2025-09-01T00:00:00Z"  # Monday
        end_date = "2025-09-08T00:00:00Z"  # Next Monday (1 week)

        result = calculate_weeks_between_dates(start_date, end_date)
        assert result == 1

    def test_calculate_weeks_partial_week_rounds(self):
        """Test that partial weeks are rounded"""
        start_date = "2025-09-01T00:00:00Z"
        end_date = "2025-09-11T00:00:00Z"  # 10 days = 1.43 weeks

        result = calculate_weeks_between_dates(start_date, end_date)
        assert result == 1  # Should round to 1

    def test_calculate_weeks_longer_season(self):
        """Test with a typical sports season length"""
        start_date = "2025-09-01T00:00:00Z"
        end_date = "2025-12-01T00:00:00Z"  # ~13 weeks

        result = calculate_weeks_between_dates(start_date, end_date)
        assert result == 13

    def test_calculate_weeks_same_date(self):
        """Test with same start and end date"""
        start_date = "2025-09-01T00:00:00Z"
        end_date = "2025-09-01T00:00:00Z"

        result = calculate_weeks_between_dates(start_date, end_date)
        assert result == 0

    def test_calculate_weeks_end_before_start(self):
        """Test when end date is before start date"""
        start_date = "2025-09-15T00:00:00Z"
        end_date = "2025-09-01T00:00:00Z"

        result = calculate_weeks_between_dates(start_date, end_date)
        assert result == 0

    def test_calculate_weeks_invalid_date_strings(self):
        """Test with invalid date strings"""
        start_date = "invalid-date"
        end_date = "2025-09-15T00:00:00Z"

        result = calculate_weeks_between_dates(start_date, end_date)
        assert result == 0

    def test_calculate_weeks_none_dates(self):
        """Test with None dates"""
        result = calculate_weeks_between_dates(None, None)
        assert result == 0

    def test_calculate_weeks_empty_strings(self):
        """Test with empty string dates"""
        result = calculate_weeks_between_dates("", "")
        assert result == 0

    def test_calculate_weeks_tbd_string(self):
        """Test with TBD string (common in our system)"""
        start_date = "2025-09-01T00:00:00Z"
        end_date = "TBD"

        result = calculate_weeks_between_dates(start_date, end_date)
        assert result == 0

    def test_calculate_weeks_realistic_season_scenario(self):
        """Test with realistic season dates from BARS"""
        # Fall 2025 season: September to November
        start_date = "2025-09-16T00:00:00Z"  # Sep 16, 2025
        end_date = "2025-11-18T00:00:00Z"  # Nov 18, 2025 (9 weeks)

        result = calculate_weeks_between_dates(start_date, end_date)
        assert result == 9
