"""
Test suite for refund calculation timestamp logic.
Ensures refund calculations use the request submission timestamp, not processing timestamp.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from modules.orders.services.refund_calculator import RefundCalculator
from shared.date_utils import calculate_refund_amount


class TestRefundTimestampLogic:
    """Test that refund calculations use the correct timestamp."""

    def setup_method(self):
        """Set up test fixtures."""
        self.refund_calculator = RefundCalculator()

        # Mock order data with a season date range that matches the extract_season_dates logic
        self.mock_order_data = {
            "total_price": "100.00",
            "line_items": [
                {
                    "title": "Test Product",
                    "product": {
                        "title": "Test Product",
                        "descriptionHtml": "<p>Season Dates: 10/15/24 - 12/15/24 (8 weeks)</p>",
                    },
                }
            ],
        }

    def test_refund_calculation_uses_submission_timestamp_not_current_time(self):
        """Test that refund calculation uses the provided submission timestamp."""

        # Season starts October 15, 2024
        season_start = datetime(2024, 10, 15, 7, 0, 0, tzinfo=timezone.utc)

        # Request submitted 3 weeks before season start (should get 95% refund)
        submission_time = season_start - timedelta(weeks=3)

        # Current time is 1 week before season start (would get 90% refund if used incorrectly)
        current_time = season_start - timedelta(weeks=1)

        with patch("shared.date_utils.datetime") as mock_datetime:
            # Mock datetime.now() to return current_time
            mock_datetime.now.return_value = current_time
            mock_datetime.fromtimestamp.side_effect = datetime.fromtimestamp
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Calculate refund using the submission timestamp
            result = self.refund_calculator.calculate_refund_due(
                order_data=self.mock_order_data,
                refund_type="refund",
                request_submitted_at=submission_time,
            )

            # Should use submission_time (3 weeks before) giving 95%, not current_time (1 week before) giving 90%
            assert result["success"] is True
            expected_refund = 100.00 * 0.95  # 95% for more than 2 weeks before
            assert abs(result["refund_amount"] - expected_refund) < 0.01
            assert "more than 2 weeks before week 1 started" in result["message"]

    def test_refund_calculation_defaults_to_current_time_when_no_timestamp_provided(
        self,
    ):
        """Test that when no timestamp is provided, it defaults to current time."""

        # Season starts October 15, 2024
        season_start = datetime(2024, 10, 15, 7, 0, 0, tzinfo=timezone.utc)

        # Current time is 1 week before season start (should get 90% refund)
        current_time = season_start - timedelta(weeks=1)

        with patch("shared.date_utils.datetime") as mock_datetime:
            # Mock datetime.now() to return current_time
            mock_datetime.now.return_value = current_time
            mock_datetime.fromtimestamp.side_effect = datetime.fromtimestamp
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            # Calculate refund without providing submission timestamp
            result = self.refund_calculator.calculate_refund_due(
                order_data=self.mock_order_data, refund_type="refund"
            )

            # Should use current_time (1 week before) giving 90%
            assert result["success"] is True
            expected_refund = 100.00 * 0.90  # 90% for before week 1 started
            assert abs(result["refund_amount"] - expected_refund) < 0.01
            assert "before week 1 started" in result["message"]

    def test_different_refund_tiers_based_on_submission_time(self):
        """Test that different submission times result in different refund amounts."""

        # Season starts October 15, 2024
        season_start = datetime(2024, 10, 15, 7, 0, 0, tzinfo=timezone.utc)

        test_cases = [
            {
                "name": "More than 2 weeks before",
                "submission_time": season_start - timedelta(weeks=3),
                "expected_percentage": 0.95,
                "expected_description": "more than 2 weeks before week 1 started",
            },
            {
                "name": "Less than 2 weeks but before week 1",
                "submission_time": season_start - timedelta(days=10),
                "expected_percentage": 0.90,
                "expected_description": "before week 1 started",
            },
            {
                "name": "After week 1 started",
                "submission_time": season_start + timedelta(days=3),
                "expected_percentage": 0.80,
                "expected_description": "after the start of week 1",
            },
            {
                "name": "After week 2 started",
                "submission_time": season_start + timedelta(weeks=1, days=3),
                "expected_percentage": 0.70,
                "expected_description": "after the start of week 2",
            },
        ]

        for case in test_cases:
            with patch("shared.date_utils.datetime") as mock_datetime:
                mock_datetime.fromtimestamp.side_effect = datetime.fromtimestamp
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                    *args, **kwargs
                )

                result = self.refund_calculator.calculate_refund_due(
                    order_data=self.mock_order_data,
                    refund_type="refund",
                    request_submitted_at=case["submission_time"],
                )

                expected_refund = 100.00 * case["expected_percentage"]

                assert result["success"] is True, f"Failed for case: {case['name']}"
                assert (
                    abs(result["refund_amount"] - expected_refund) < 0.01
                ), f"Wrong refund amount for {case['name']}: expected {expected_refund}, got {result['refund_amount']}"
                assert (
                    case["expected_description"] in result["message"]
                ), f"Wrong description for {case['name']}: {result['message']}"

    def test_calculate_refund_amount_function_directly(self):
        """Test the calculate_refund_amount function directly with different timestamps."""

        season_start_str = "10/15/24"
        total_amount = 100.0
        refund_type = "refund"

        # Test submission 3 weeks before season start
        submission_time = datetime(
            2024, 9, 24, 10, 0, 0, tzinfo=timezone.utc
        )  # 3 weeks before

        refund_amount, message = calculate_refund_amount(
            season_start_date_str=season_start_str,
            off_dates_str=None,
            total_amount_paid=total_amount,
            refund_type=refund_type,
            request_submitted_at=submission_time,
        )

        # Should get 95% refund (more than 2 weeks before)
        expected_refund = 100.0 * 0.95
        assert abs(refund_amount - expected_refund) < 0.01
        assert "more than 2 weeks before week 1 started" in message
        assert "95% after 0% penalty + 5% processing fee" in message

    def test_timezone_handling_in_refund_calculation(self):
        """Test that timezone-aware and naive timestamps are handled correctly."""

        season_start_str = "10/15/24"
        total_amount = 100.0
        refund_type = "refund"

        # Test with timezone-aware timestamp
        submission_time_aware = datetime(2024, 9, 24, 10, 0, 0, tzinfo=timezone.utc)

        refund_amount_aware, message_aware = calculate_refund_amount(
            season_start_date_str=season_start_str,
            off_dates_str=None,
            total_amount_paid=total_amount,
            refund_type=refund_type,
            request_submitted_at=submission_time_aware,
        )

        # Test with naive timestamp (should be treated as UTC)
        submission_time_naive = datetime(2024, 9, 24, 10, 0, 0)  # No timezone

        refund_amount_naive, message_naive = calculate_refund_amount(
            season_start_date_str=season_start_str,
            off_dates_str=None,
            total_amount_paid=total_amount,
            refund_type=refund_type,
            request_submitted_at=submission_time_naive,
        )

        # Both should produce the same result
        assert abs(refund_amount_aware - refund_amount_naive) < 0.01
        assert message_aware == message_naive

    def test_refund_vs_credit_percentages_with_timestamps(self):
        """Test that refund vs credit types give different percentages for same timestamp."""

        season_start_str = "10/15/24"
        total_amount = 100.0
        submission_time = datetime(
            2024, 9, 24, 10, 0, 0, tzinfo=timezone.utc
        )  # 3 weeks before

        # Test refund (95% for early submission)
        refund_amount, refund_message = calculate_refund_amount(
            season_start_date_str=season_start_str,
            off_dates_str=None,
            total_amount_paid=total_amount,
            refund_type="refund",
            request_submitted_at=submission_time,
        )

        # Test credit (100% for early submission)
        credit_amount, credit_message = calculate_refund_amount(
            season_start_date_str=season_start_str,
            off_dates_str=None,
            total_amount_paid=total_amount,
            refund_type="credit",
            request_submitted_at=submission_time,
        )

        # Credit should be higher than refund for same timing
        assert credit_amount > refund_amount
        assert abs(refund_amount - 95.0) < 0.01  # 95% for refund
        assert abs(credit_amount - 100.0) < 0.01  # 100% for credit

        # Messages should reflect the different types
        assert "processing fee" in refund_message
        assert "processing fee" not in credit_message

    @patch("shared.date_utils.logger")
    def test_logging_shows_correct_timestamps(self, mock_logger):
        """Test that the logging shows both season start and submission timestamps."""

        season_start_str = "10/15/24"
        submission_time = datetime(2024, 9, 24, 10, 0, 0, tzinfo=timezone.utc)

        calculate_refund_amount(
            season_start_date_str=season_start_str,
            off_dates_str=None,
            total_amount_paid=100.0,
            refund_type="refund",
            request_submitted_at=submission_time,
        )

        # Check that both timestamps are logged
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]

        season_start_logged = any(
            "Season Start Date (UTC @ 7am):" in call for call in log_calls
        )
        submission_logged = any(
            "Request Submitted At (UTC):" in call for call in log_calls
        )

        assert season_start_logged, "Season start date should be logged"
        assert submission_logged, "Request submission timestamp should be logged"

        # Check that the submission timestamp in the log matches what we provided
        submission_log = next(
            call for call in log_calls if "Request Submitted At (UTC):" in call
        )
        assert "2024-09-24T10:00:00+00:00" in submission_log
