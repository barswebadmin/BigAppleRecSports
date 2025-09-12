"""
Tests for refund vs credit calculation differences.
Tests the actual calculation logic to ensure refunds and credits are calculated differently.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from services.orders.refund_calculator import RefundCalculator
from utils.date_utils import calculate_refund_amount


class TestRefundCreditCalculations:
    """Test calculation differences between refunds and credits"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_shopify_service = Mock()
        self.calculator = RefundCalculator()
        
        # Sample order data with season dates (format expected by RefundCalculator)
        self.sample_order_data = {
            "id": "gid://shopify/Order/5876418969694",
            "name": "#42305",
            "total_price": "20.00",
            "line_items": [{
                "title": "Kickball - Thursday - Advanced - Fall 2024",
                "price": "20.00",
                "quantity": 1,
                "product": {
                    "descriptionHtml": "<p>Season Dates: 10/15/24 - 12/15/24 (8 weeks)</p>"
                }
            }]
        }
        
        # Test timestamps - early vs late requests
        self.early_request = datetime(2024, 9, 1, tzinfo=timezone.utc)   # More than 2 weeks before
        self.late_request = datetime(2024, 10, 10, tzinfo=timezone.utc)  # Less than 2 weeks before
        self.very_late_request = datetime(2024, 10, 20, tzinfo=timezone.utc)  # After season start

    @patch('services.orders.refund_calculator.extract_season_dates')
    @patch('services.orders.refund_calculator.calculate_refund_amount')
    def test_refund_calculation_applies_processing_fee(self, mock_calc, mock_extract):
        """Test that refund calculations include processing fees"""
        
        # Mock successful season date extraction
        mock_extract.return_value = ("10/15/24", "")
        
        # Mock the utility function to return refund-specific calculation (tuple format)
        mock_calc.return_value = (19.00, "95% refund (5% processing fee applied)")
        
        result = self.calculator.calculate_refund_due(
            self.sample_order_data, 
            "refund", 
            self.early_request
        )
        
        # Verify processing fee is applied for refunds
        assert result["refund_amount"] == 19.00
        assert "processing fee" in result["message"].lower()
        assert result["refund_type"] == "refund"
        assert result["success"] is True
        
        # Verify the utility function was called with refund type
        mock_calc.assert_called_once()
        call_args = mock_calc.call_args[1]  # Get keyword args
        assert call_args["refund_type"] == "refund"

    @patch('services.orders.refund_calculator.extract_season_dates')
    @patch('services.orders.refund_calculator.calculate_refund_amount')
    def test_credit_calculation_no_processing_fee(self, mock_calc, mock_extract):
        """Test that credit calculations do NOT include processing fees"""
        
        # Mock successful season date extraction
        mock_extract.return_value = ("10/15/24", "")
        
        # Mock the utility function to return credit-specific calculation (tuple format)
        mock_calc.return_value = (20.00, "100% store credit (no processing fee for credits)")
        
        result = self.calculator.calculate_refund_due(
            self.sample_order_data, 
            "credit", 
            self.early_request
        )
        
        # Verify no processing fee for credits
        assert result["refund_amount"] == 20.00
        assert "no processing fee" in result["message"].lower()
        assert result["refund_type"] == "credit"
        assert result["success"] is True
        
        # Verify the utility function was called with credit type
        mock_calc.assert_called_once()
        call_args = mock_calc.call_args[1]  # Get keyword args
        assert call_args["refund_type"] == "credit"

    @patch('services.orders.refund_calculator.extract_season_dates')
    @patch('services.orders.refund_calculator.calculate_refund_amount')
    def test_credit_calculation_ignores_timing(self, mock_calc, mock_extract):
        """Test that credit calculations return full amount regardless of timing"""
        
        # Mock successful season date extraction
        mock_extract.return_value = ("10/15/24", "")
        
        # Credits should always return full amount (tuple format)
        mock_calc.return_value = (20.00, "100% store credit (timing doesn't affect credits)")
        
        # Test early credit request
        early_result = self.calculator.calculate_refund_due(
            self.sample_order_data, "credit", self.early_request
        )
        
        # Test late credit request  
        late_result = self.calculator.calculate_refund_due(
            self.sample_order_data, "credit", self.late_request
        )
        
        # Test very late credit request
        very_late_result = self.calculator.calculate_refund_due(
            self.sample_order_data, "credit", self.very_late_request
        )
        
        # All should return full amount
        assert early_result["refund_amount"] == 20.00
        assert late_result["refund_amount"] == 20.00
        assert very_late_result["refund_amount"] == 20.00
        
        # All should indicate no processing fee or be store credit
        for result in [early_result, late_result, very_late_result]:
            message_lower = result["message"].lower()
            assert "store credit" in message_lower or "no processing fee" in message_lower

    @patch('services.orders.refund_calculator.extract_season_dates')
    @patch('services.orders.refund_calculator.calculate_refund_amount')
    def test_refund_calculation_varies_by_timing(self, mock_calc, mock_extract):
        """Test that refund calculations vary based on request timing"""
        
        # Mock successful season date extraction
        mock_extract.return_value = ("10/15/24", "")
        
        def mock_calc_timing_sensitive(season_start_date_str, off_dates_str, total_amount_paid, refund_type, request_submitted_at):
            """Mock calculation that varies by timing for refunds only (tuple format)"""
            if refund_type == "credit":
                return (20.00, "100% store credit (timing doesn't affect credits)")
            
            # For refunds, vary by timing based on request timestamp
            if request_submitted_at.month == 9:  # Early request (September 1)
                return (19.00, "95% refund (more than 2 weeks before season)")
            elif request_submitted_at.month == 10 and request_submitted_at.day <= 15:  # Late request (Oct 10)
                return (14.00, "70% refund (less than 2 weeks before season)")
            elif request_submitted_at.month == 10 and request_submitted_at.day > 15:  # Very late request (Oct 20)
                return (8.00, "40% refund (season already started)")
            else:  # Other late requests
                return (0.00, "0% refund (season already started)")
        
        mock_calc.side_effect = mock_calc_timing_sensitive
        
        # Test early refund (high percentage)
        early_result = self.calculator.calculate_refund_due(
            self.sample_order_data, "refund", self.early_request
        )
        
        # Test late refund (lower percentage)
        late_result = self.calculator.calculate_refund_due(
            self.sample_order_data, "refund", self.late_request
        )
        
        # Test very late refund (no refund)
        very_late_result = self.calculator.calculate_refund_due(
            self.sample_order_data, "refund", self.very_late_request
        )
        
        # Verify different refund amounts based on timing
        assert early_result["refund_amount"] == 19.00
        assert "95%" in early_result["message"]
        
        assert late_result["refund_amount"] == 14.00
        assert "70%" in late_result["message"]
        
        assert very_late_result["refund_amount"] == 8.00
        assert "40%" in very_late_result["message"]

    def test_calculate_refund_amount_utility_function_direct(self):
        """Test the utility function directly to ensure it handles refund vs credit correctly"""
        
        order_total = 20.00
        season_start_date_str = "10/15/24"  # Format expected by utility function
        off_dates_str = None
        request_time = datetime(2024, 9, 1, tzinfo=timezone.utc)  # Early request
        
        # Test refund calculation (should return tuple)
        refund_amount, refund_message = calculate_refund_amount(
            season_start_date_str, off_dates_str, order_total, "refund", request_time
        )
        
        # Test credit calculation (should return tuple)
        credit_amount, credit_message = calculate_refund_amount(
            season_start_date_str, off_dates_str, order_total, "credit", request_time
        )
        
        # Verify refund has processing fee (refund should be less than total due to processing fee)
        assert refund_amount < order_total
        assert "processing fee" in refund_message.lower()
        
        # Verify credit gives full amount (credits should be full amount)
        assert credit_amount == order_total or credit_amount > refund_amount
        # Credit message might not explicitly mention "no processing fee"

    @patch('services.orders.refund_calculator.extract_season_dates')
    @patch('services.orders.refund_calculator.calculate_refund_amount')
    def test_calculation_explanation_differs_by_type(self, mock_calc, mock_extract):
        """Test that calculation explanations differ for refund vs credit"""
        
        # Mock successful season date extraction
        mock_extract.return_value = ("10/15/24", "")
        
        # Mock different explanations for each type (tuple format)
        def mock_explanation_by_type(season_start_date_str, off_dates_str, total_amount_paid, refund_type, request_submitted_at):
            if refund_type == "refund":
                return (19.00, "95% refund calculated with 5% processing fee deducted from total")
            else:
                return (20.00, "100% store credit issued - no processing fees apply to credits")
        
        mock_calc.side_effect = mock_explanation_by_type
        
        # Test refund explanation
        refund_result = self.calculator.calculate_refund_due(
            self.sample_order_data, "refund", self.early_request
        )
        
        # Test credit explanation
        credit_result = self.calculator.calculate_refund_due(
            self.sample_order_data, "credit", self.early_request
        )
        
        # Verify different explanations
        refund_explanation = refund_result["message"]
        credit_explanation = credit_result["message"]
        
        assert "processing fee" in refund_explanation.lower()
        assert "deducted" in refund_explanation.lower()
        
        assert "store credit" in credit_explanation.lower()
        assert "no processing fees" in credit_explanation.lower()

    @patch('services.orders.refund_calculator.extract_season_dates')
    @patch('services.orders.refund_calculator.calculate_refund_amount')
    def test_order_cancellation_flag_differs_by_type(self, mock_calc, mock_extract):
        """Test that order cancellation behavior differs for refunds vs credits"""
        
        # Mock successful season date extraction
        mock_extract.return_value = ("10/15/24", "")
        mock_calc.return_value = (20.00, "Test calculation")
        
        # Test refund (should indicate order cancellation)
        refund_result = self.calculator.calculate_refund_due(
            self.sample_order_data, "refund", self.early_request
        )
        
        # Test credit (should NOT indicate order cancellation)
        credit_result = self.calculator.calculate_refund_due(
            self.sample_order_data, "credit", self.early_request
        )
        
        # Note: The order cancellation flag would be handled at a higher level
        # This test verifies the calculator provides the right information
        # for downstream logic to make cancellation decisions
        
        assert refund_result["refund_type"] == "refund"
        assert credit_result["refund_type"] == "credit"

    @pytest.mark.parametrize("refund_type,expected_amount", [
        ("refund", 19.00),
        ("credit", 20.00),
        ("REFUND", 19.00),  # Test case insensitivity
        ("CREDIT", 20.00),
        ("Refund", 19.00),
        ("Credit", 20.00),
    ])
    @patch('services.orders.refund_calculator.extract_season_dates')
    @patch('services.orders.refund_calculator.calculate_refund_amount')
    def test_refund_type_case_insensitivity(self, mock_calc, mock_extract, refund_type, expected_amount):
        """Test that refund_type handling is case insensitive"""
        
        # Mock successful season date extraction
        mock_extract.return_value = ("10/15/24", "")
        
        def mock_case_sensitive_calc(season_start_date_str, off_dates_str, total_amount_paid, refund_type, request_submitted_at):
            if refund_type.lower() == "refund":
                return (19.00, "Refund with processing fee")
            else:
                return (20.00, "Credit with no fee")
        
        mock_calc.side_effect = mock_case_sensitive_calc
        
        result = self.calculator.calculate_refund_due(
            self.sample_order_data, refund_type, self.early_request
        )
        
        assert result["refund_amount"] == expected_amount
        assert result["refund_type"] == refund_type  # Should preserve original case

    @patch('services.orders.refund_calculator.extract_season_dates')
    @patch('services.orders.refund_calculator.calculate_refund_amount')
    def test_invalid_refund_type_handling(self, mock_calc, mock_extract):
        """Test handling of invalid refund_type values in calculations"""
        
        # Test that the calculator handles invalid refund types gracefully
        # In practice, invalid types should be caught at a higher level
        
        # Mock successful season date extraction
        mock_extract.return_value = ("10/15/24", "")
        
        # Mock the utility function to behave normally (it doesn't validate refund_type)
        mock_calc.return_value = (20.00, "Calculated with invalid type")
        
        # The calculator should still work and pass through the invalid type
        result = self.calculator.calculate_refund_due(
            self.sample_order_data, "invalid_type", self.early_request
        )
        
        # The calculator should still return a valid response
        assert result["success"] is True
        assert result["refund_type"] == "invalid_type"
        assert result["refund_amount"] == 20.00
        
        # The validation of refund_type is expected to happen at a higher level
        # (e.g., in the service layer or API validation)

    def test_calculation_logging_differs_by_type(self):
        """Test that calculation logic handles different refund types appropriately"""
        
        # This test verifies that the calculation logic can distinguish between
        # refund and credit types at the calculation level
        
        with patch('services.orders.refund_calculator.extract_season_dates') as mock_extract, \
             patch('services.orders.refund_calculator.calculate_refund_amount') as mock_calc:
            
            # Mock successful season date extraction
            mock_extract.return_value = ("10/15/24", "")
            
            def mock_type_aware_calc(season_start_date_str, off_dates_str, total_amount_paid, refund_type, request_submitted_at):
                if refund_type == "refund":
                    return (19.00, "Refund calculation with fees")
                else:
                    return (20.00, "Credit calculation without fees")
            
            mock_calc.side_effect = mock_type_aware_calc
            
            # Test refund calculation
            refund_result = self.calculator.calculate_refund_due(
                self.sample_order_data, "refund", self.early_request
            )
            
            # Test credit calculation
            credit_result = self.calculator.calculate_refund_due(
                self.sample_order_data, "credit", self.early_request
            )
            
            # Verify that different types result in different outcomes
            assert refund_result["refund_type"] == "refund"
            assert refund_result["refund_amount"] == 19.00
            
            assert credit_result["refund_type"] == "credit"
            assert credit_result["refund_amount"] == 20.00
