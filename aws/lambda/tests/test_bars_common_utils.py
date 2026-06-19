"""Unit tests for shared_utilities (formerly bars_common_utils)."""

from datetime import datetime, time
from unittest.mock import patch

import pytest

from shared_utilities.date_utils.parse_date import parse_date
from shared_utilities.date_utils.parse_time import parse_time
from shared_utilities.date_utils.parse_off_dates import parse_off_dates
from shared_utilities.calculate_discounted_schedule import calculate_discounted_schedule
from shared_utilities.wait_until_next_minute import wait_until_next_minute


class TestDateUtils:
    def test_parse_date_formats(self):
        test_cases = [
            ("1/15/25", datetime(2025, 1, 15)),
            ("12/31/24", datetime(2024, 12, 31)),
            ("1/1/2025", datetime(2025, 1, 1)),
            ("12/25/2024", datetime(2024, 12, 25)),
        ]
        for date_str, expected in test_cases:
            assert parse_date(date_str) == expected, f"Failed for {date_str}"

    def test_parse_date_invalid_format(self):
        for invalid in ["invalid", "13/01/25", "1/32/25", ""]:
            with pytest.raises(ValueError):
                parse_date(invalid)

    def test_parse_time_formats(self):
        test_cases = [
            ("10:30 AM", time(10, 30)),
            ("2:15 PM", time(14, 15)),
            ("12:00 AM", time(0, 0)),
            ("12:00 PM", time(12, 0)),
        ]
        for time_str, expected in test_cases:
            assert parse_time(time_str) == expected, f"Failed for {time_str}"

    def test_parse_time_invalid_format(self):
        for invalid in ["invalid", "25:00 AM", "10:60 PM", ""]:
            with pytest.raises(ValueError):
                parse_time(invalid)

    def test_parse_off_dates(self):
        sport_time = time(19, 0)
        result = parse_off_dates("1/15/25,2/12/25,3/5/25", sport_time)
        assert len(result) == 3
        assert all(isinstance(dt, datetime) for dt in result)
        assert result[0].time() == sport_time
        assert parse_off_dates("", sport_time) == []
        assert parse_off_dates(None, sport_time) == []

    def test_calculate_discounted_schedule(self):
        season_start = datetime(2025, 1, 15, 19, 0)
        off_dates = [datetime(2025, 1, 22, 19, 0)]
        result = calculate_discounted_schedule(season_start, off_dates, 100.0)
        assert len(result) == 4
        assert all('timestamp' in item and 'updated_price' in item for item in result)
        for item in result:
            assert 0 < item['updated_price'] < 100.0


class TestWaitUntilNextMinute:
    @patch('time.sleep')
    @patch('shared_utilities.wait_until_next_minute.datetime')
    def test_waits_remaining_seconds(self, mock_datetime, mock_sleep):
        mock_datetime.utcnow.return_value = datetime(2023, 1, 1, 10, 30, 45)
        wait_until_next_minute()
        mock_sleep.assert_called_once_with(15.0)

    @patch('time.sleep')
    @patch('shared_utilities.wait_until_next_minute.datetime')
    def test_waits_full_minute_at_zero(self, mock_datetime, mock_sleep):
        mock_datetime.utcnow.return_value = datetime(2023, 1, 1, 10, 30, 0)
        wait_until_next_minute()
        mock_sleep.assert_called_once_with(60.0)
