"""
Unit tests for RefundCalculator.
"""

import pytest
from unittest.mock import patch
from modules.orders.services.refund_calculator import RefundCalculator


class TestRefundCalculator:
    """Test RefundCalculator functionality."""

    @pytest.fixture
    def calculator(self):
        return RefundCalculator()

    @pytest.fixture
    def sample_order_data(self):
        return {
            "total_price": "25.00",
            "line_items": [
                {
                    "title": "Spring Kickball League",
                    "product": {
                        "descriptionHtml": "<p>Season runs from March 1 to May 31, 2024</p>"
                    },
                }
            ],
        }

    def test_calculate_refund_no_line_items(self, calculator):
        """Test refund calculation with no line items."""
        order_data = {"line_items": []}
        result = calculator.calculate_refund_due(order_data, "refund")

        assert result["success"] is False
        assert "No line items found" in result["message"]
        assert result["refund_amount"] == 0

    @patch("services.orders.refund_calculator.extract_season_dates")
    def test_calculate_refund_no_season_dates(
        self, mock_extract, calculator, sample_order_data
    ):
        """Test refund calculation when season dates cannot be extracted (fallback calculation)."""
        mock_extract.return_value = (None, None)

        result = calculator.calculate_refund_due(sample_order_data, "refund")

        # Changed behavior: now returns success=True with fallback calculation (90% of total)
        assert result["success"] is True
        assert "Could not parse season dates" in result["message"]
        assert result["refund_amount"] == 22.50  # 90% of $25.00
        assert result["product_title"] == "Spring Kickball League"
        assert result["missing_season_info"] is True

    @patch("services.orders.refund_calculator.calculate_refund_amount")
    @patch("services.orders.refund_calculator.extract_season_dates")
    def test_calculate_refund_success(
        self, mock_extract, mock_calculate, calculator, sample_order_data
    ):
        """Test successful refund calculation."""
        mock_extract.return_value = ("2024-03-01T00:00:00Z", "off-dates")
        mock_calculate.return_value = (15.0, "Refund calculated successfully")

        result = calculator.calculate_refund_due(sample_order_data, "refund")

        assert result["success"] is True
        assert result["refund_amount"] == 15.0
        assert result["order_total"] == 25.0
        assert result["season_start_date"] == "2024-03-01T00:00:00Z"
        assert result["off_dates"] == "off-dates"
        assert result["refund_type"] == "refund"
        assert result["product_title"] == "Spring Kickball League"
        assert result["message"] == "Refund calculated successfully"

    @patch("services.orders.refund_calculator.extract_season_dates")
    def test_calculate_refund_extraction_error(
        self, mock_extract, calculator, sample_order_data
    ):
        """Test refund calculation when date extraction raises an exception."""
        mock_extract.side_effect = ValueError("Invalid date format")

        result = calculator.calculate_refund_due(sample_order_data, "refund")

        assert result["success"] is False
        assert "Could not extract season dates" in result["message"]
        assert "Invalid date format" in result["message"]
        assert result["refund_amount"] == 0
        assert result["product_title"] == "Spring Kickball League"

    def test_calculate_refund_general_error(self, calculator):
        """Test refund calculation with malformed order data."""
        # Malformed order data that will cause an exception
        order_data = {"invalid": "data"}

        result = calculator.calculate_refund_due(order_data, "refund")

        assert result["success"] is False
        assert "No line items found" in result["message"]
        assert result["refund_amount"] == 0
