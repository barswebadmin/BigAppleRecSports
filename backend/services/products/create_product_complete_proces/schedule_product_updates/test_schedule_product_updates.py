"""
Test AWS datetime formatting for schedule_product_updates
"""

from datetime import datetime, timezone
from .schedule_product_updates import format_datetime_for_aws


class TestAWSDateTimeFormatting:
    """Test suite for AWS datetime formatting"""

    def test_datetime_with_timezone(self):
        """Test datetime object with timezone"""
        dt = datetime(2025, 9, 17, 23, 0, 0, tzinfo=timezone.utc)
        result = format_datetime_for_aws(dt)
        assert result == "2025-09-17T23:00:00"

    def test_iso_string_with_timezone(self):
        """Test ISO string with +00:00 timezone"""
        input_str = "2025-09-17T23:00:00+00:00"
        result = format_datetime_for_aws(input_str)
        assert result == "2025-09-17T23:00:00"

    def test_iso_string_with_z_timezone(self):
        """Test ISO string with Z timezone"""
        input_str = "2025-09-16T23:00:00Z"
        result = format_datetime_for_aws(input_str)
        assert result == "2025-09-16T23:00:00"

    def test_iso_string_with_microseconds(self):
        """Test ISO string with microseconds and timezone"""
        input_str = "2025-09-18T23:00:00.123456+00:00"
        result = format_datetime_for_aws(input_str)
        assert result == "2025-09-18T23:00:00"

    def test_datetime_with_microseconds_no_timezone(self):
        """Test datetime with microseconds but no timezone"""
        dt = datetime(2025, 9, 15, 12, 30, 45, 123456)
        result = format_datetime_for_aws(dt)
        assert result == "2025-09-15T12:30:45"

    def test_already_correct_format(self):
        """Test string already in correct format"""
        input_str = "2025-09-15T12:30:45"
        result = format_datetime_for_aws(input_str)
        assert result == "2025-09-15T12:30:45"

    def test_problematic_cases_from_logs(self):
        """Test the specific cases that were failing in AWS"""
        problematic_cases = [
            "2025-09-17T23:00:00+00:00",
            "2025-09-18T23:00:00+00:00",
            "2025-09-16T23:00:00+00:00",
        ]

        for case in problematic_cases:
            result = format_datetime_for_aws(case)
            expected = case.split("+")[0]  # Remove timezone part
            assert (
                result == expected
            ), f"Failed for {case}: got {result}, expected {expected}"

    def test_none_and_empty_values(self):
        """Test edge cases with None and empty values"""
        assert format_datetime_for_aws(None) == "None"
        assert format_datetime_for_aws("") == ""

    def test_invalid_string(self):
        """Test invalid datetime string"""
        invalid_str = "not-a-datetime"
        result = format_datetime_for_aws(invalid_str)
        assert result == "not-a-datetime"  # Should return as-is if parsing fails
