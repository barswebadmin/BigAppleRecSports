"""
Unit tests for bars_common_utils shared utilities.

Tests the lambda layer functionality that's shared across functions.
"""

import pytest
import json
from datetime import datetime, time
from unittest.mock import patch, MagicMock
import sys
import os

# Import bars_common_utils modules
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__),
                    '../../lambda-layers/bars-common-utils/python')
)

from bars_common_utils.date_utils import (  # type: ignore
    parse_date, parse_time, parse_off_dates, calculate_discounted_schedule
)
from bars_common_utils.event_utils import (  # type: ignore
    parse_event_body, validate_required_fields, get_field_safe
)
from bars_common_utils.response_utils import (  # type: ignore
    format_response, format_error
)
from bars_common_utils.request_utils import wait_until_next_minute  # type: ignore
from bars_common_utils.scheduler_utils import (  # type: ignore
    create_schedule_target
)


class TestDateUtils:
    """Test date utility functions"""

    def test_parse_date_formats(self):
        """Test parsing different date formats"""
        test_cases = [
            ("1/15/25", datetime(2025, 1, 15)),
            ("12/31/24", datetime(2024, 12, 31)),
            ("1/1/2025", datetime(2025, 1, 1)),
            ("12/25/2024", datetime(2024, 12, 25))
        ]

        for date_str, expected in test_cases:
            result = parse_date(date_str)
            assert result == expected, f"Failed for {date_str}"

    def test_parse_date_invalid_format(self):
        """Test parse_date with invalid formats"""
        invalid_dates = ["invalid", "13/01/25", "1/32/25", ""]

        for invalid_date in invalid_dates:
            with pytest.raises(ValueError):
                parse_date(invalid_date)

    def test_parse_time_formats(self):
        """Test parsing time formats"""
        test_cases = [
            ("10:30 AM", time(10, 30)),
            ("2:15 PM", time(14, 15)),
            ("12:00 AM", time(0, 0)),
            ("12:00 PM", time(12, 0))
        ]

        for time_str, expected in test_cases:
            result = parse_time(time_str)
            assert result == expected, f"Failed for {time_str}"

    def test_parse_time_invalid_format(self):
        """Test parse_time with invalid formats"""
        invalid_times = ["invalid", "25:00 AM", "10:60 PM", ""]

        for invalid_time in invalid_times:
            with pytest.raises(ValueError):
                parse_time(invalid_time)

    def test_parse_off_dates(self):
        """Test parsing comma-separated off dates"""
        sport_time = time(19, 0)  # 7:00 PM

        # Test with valid dates
        result = parse_off_dates("1/15/25,2/12/25,3/5/25", sport_time)
        assert len(result) == 3
        assert all(isinstance(dt, datetime) for dt in result)
        assert result[0].time() == sport_time

        # Test with empty string
        result = parse_off_dates("", sport_time)
        assert result == []

        # Test with None
        result = parse_off_dates(None, sport_time)
        assert result == []

    def test_calculate_discounted_schedule(self):
        """Test discount schedule calculation"""
        season_start = datetime(2025, 1, 15, 19, 0)  # Jan 15, 2025 at 7 PM
        off_dates = [datetime(2025, 1, 22, 19, 0)]  # One off date
        base_price = 100.0

        result = calculate_discounted_schedule(season_start, off_dates,
                                               base_price)

        assert len(result) == 4  # Four weeks of discounts
        assert all('timestamp' in item and 'updated_price' in item
                   for item in result)

        # Prices should be discounted (less than base price)
        for item in result:
            assert item['updated_price'] < base_price
            assert item['updated_price'] > 0


class TestEventUtils:
    """Test event utility functions"""

    def test_parse_event_body_string(self):
        """Test parsing string event body"""
        event = {
            'body': '{"test": "data", "number": 123}'
        }

        result = parse_event_body(event)
        assert result == {"test": "data", "number": 123}

    def test_parse_event_body_dict(self):
        """Test parsing dict event body"""
        event = {
            'body': {"test": "data", "number": 123}
        }

        result = parse_event_body(event)
        assert result == {"test": "data", "number": 123}

    def test_parse_event_body_direct(self):
        """Test parsing direct event (no body wrapper)"""
        event = {"test": "data", "number": 123}

        result = parse_event_body(event)
        assert result == {"test": "data", "number": 123}

    def test_validate_required_fields_success(self):
        """Test successful field validation"""
        data = {"field1": "value1", "field2": "value2", "field3": "value3"}
        required = ["field1", "field2"]

        result = validate_required_fields(data, required)
        assert result == data  # Should return original data

    def test_validate_required_fields_missing(self):
        """Test validation with missing fields"""
        data = {"field1": "value1"}
        required = ["field1", "field2", "field3"]

        with pytest.raises(ValueError) as exc_info:
            validate_required_fields(data, required)

        assert "Missing required fields" in str(exc_info.value)
        assert "field2" in str(exc_info.value)
        assert "field3" in str(exc_info.value)

    def test_get_field_safe(self):
        """Test safe field retrieval"""
        data = {"existing": "value", "empty": "", "none": None}

        # Test existing field
        assert get_field_safe(data, "existing") == "value"

        # Test missing field with default
        assert get_field_safe(data, "missing", "default") == "default"

        # Test empty field with default
        assert get_field_safe(data, "empty", "default") == "default"

        # Test None field with default
        assert get_field_safe(data, "none", "default") == "default"


class TestResponseUtils:
    """Test response utility functions"""

    def test_format_response_success(self):
        """Test formatting successful response"""
        data = {"message": "Success", "data": [1, 2, 3]}

        result = format_response(200, data)

        assert result == {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': data
        }

    def test_format_response_with_custom_headers(self):
        """Test formatting response with custom headers"""
        data = {"message": "Success"}
        custom_headers = {"X-Custom": "value"}

        result = format_response(201, data, custom_headers)

        expected_headers = {
            'Content-Type': 'application/json',
            'X-Custom': 'value'
        }
        assert result['headers'] == expected_headers

    def test_format_error_simple(self):
        """Test formatting simple error response"""
        result = format_error(400, "Bad request")

        assert result == {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': {'error': 'Bad request'}
        }

    def test_format_error_with_details(self):
        """Test formatting error response with details"""
        details = {"field": "Invalid value", "code": "E001"}

        result = format_error(422, "Validation failed", details)

        expected_body = {
            'error': 'Validation failed',
            'details': details
        }
        assert result['body'] == expected_body


class TestRequestUtils:
    """Test request utility functions"""

    @patch('time.sleep')
    @patch('bars_common_utils.request_utils.datetime')
    def test_wait_until_next_minute(self, mock_datetime, mock_sleep):
        """Test waiting until next minute"""
        # Mock current time as 10:30:45 (45 seconds past the minute)
        mock_now = MagicMock()
        mock_now.second = 45
        mock_datetime.now.return_value = mock_now

        wait_until_next_minute()

        # Should sleep for 15 seconds to reach next minute
        mock_sleep.assert_called_once_with(15)

    @patch('time.sleep')
    @patch('bars_common_utils.request_utils.datetime')
    def test_wait_until_next_minute_already_at_start(self, mock_datetime,
                                                     mock_sleep):
        """Test when already at start of minute"""
        # Mock current time as 10:30:00 (0 seconds)
        mock_now = MagicMock()
        mock_now.second = 0
        mock_datetime.now.return_value = mock_now

        wait_until_next_minute()

        # Should not sleep if already at start of minute
        mock_sleep.assert_called_once_with(60)  # Wait full minute


class TestSchedulerUtils:
    """Test scheduler utility functions"""

    def test_create_schedule_target(self):
        """Test creating EventBridge schedule target"""
        function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
        role_arn = "arn:aws:iam::123456789012:role/test-role"
        input_data = {"test": "data"}
        description = "Test schedule"

        result = create_schedule_target(function_arn, role_arn, input_data,
                                        description)

        expected = {
            "Arn": function_arn,
            "RoleArn": role_arn,
            "Input": json.dumps(input_data),
            "Description": description
        }
        assert result == expected

    def test_create_schedule_target_minimal(self):
        """Test creating schedule target with minimal parameters"""
        function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
        role_arn = "arn:aws:iam::123456789012:role/test-role"
        input_data = {"test": "data"}

        result = create_schedule_target(function_arn, role_arn, input_data)

        assert result["Arn"] == function_arn
        assert result["RoleArn"] == role_arn
        assert result["Input"] == json.dumps(input_data)
        assert "Description" in result  # Should have default description 