"""Tests for parse_timestamp_string utility function."""

import pytest
from datetime import datetime

from parse_timestamp_string import parse_timestamp_string


class TestParseDateOnly:
    """Test parsing date-only timestamp strings."""

    @pytest.mark.parametrize("date_string,expected_date", [
        ("03/02/2026", datetime(2026, 3, 2, 0, 0, 0)),
        ("03/02/26", datetime(2026, 3, 2, 0, 0, 0)),
        ("3/2", datetime(2026, 3, 2, 0, 0, 0)),
        ("3-2-26", datetime(2026, 3, 2, 0, 0, 0)),
        ("03-02-26", datetime(2026, 3, 2, 0, 0, 0)),
        ("03-02-2026", datetime(2026, 3, 2, 0, 0, 0)),
        ("mar 3 2026", datetime(2026, 3, 3, 0, 0, 0)),
        ("march 3rd 2026", datetime(2026, 3, 3, 0, 0, 0)),
        ("march 3", datetime(2026, 3, 3, 0, 0, 0)),
    ])
    def test_parse_timestamp_string_date_only(self, date_string, expected_date):
        """Test parsing various date-only formats."""
        result = parse_timestamp_string(date_string)
        
        assert result["input_type"] == "date"
        assert result["value"] == expected_date
