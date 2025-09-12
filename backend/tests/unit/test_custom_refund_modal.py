"""
Tests for custom refund modal submission handling in the Slack service.

These tests focus on the business logic of processing custom refund amounts
submitted through Slack modals, ensuring proper data validation and flow.
"""

import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
from services.slack.slack_service import SlackService


class TestCustomRefundModalSubmission:
    """Test custom refund modal submission processing"""

    def setup_method(self):
        """Set up test fixtures"""
        # Mock API client
        self.mock_api_client = Mock()
        self.mock_api_client.update_message.return_value = {"ok": True}
        
        # Create SlackService instance with mocked dependencies
        with patch("services.slack.slack_service.OrdersService"), \
             patch("services.slack.slack_service.SlackMessageBuilder"), \
             patch("services.slack.slack_service.SlackRefundsUtils") as mock_refunds_utils:
            
            self.slack_service = SlackService()
            self.slack_service.api_client = self.mock_api_client
            
            # Mock the refunds utils handle_process_refund method
            self.mock_refunds_utils = mock_refunds_utils.return_value
            self.mock_refunds_utils.handle_process_refund = AsyncMock(
                return_value={"success": True, "message": "Refund processed"}
            )

    @pytest.mark.asyncio
    async def test_handle_process_refund_with_custom_amount(self):
        """Test that custom refund amounts are properly passed to the refund processor"""
        
        # Test data
        request_data = {
            "orderId": "gid://shopify/Order/5877381955678",
            "rawOrderNumber": "#42366",
            "refundAmount": "25.50",  # Custom amount from modal
            "refundType": "credit",
            "orderCancelled": "false",
        }
        
        requestor_name = {"first": "John", "last": "Doe"}
        requestor_email = "test@example.com"
        
        # Call the method
        result = await self.slack_service.handle_process_refund(
            request_data=request_data,
            channel_id="C092RU7R6PL",
            requestor_name=requestor_name,
            requestor_email=requestor_email,
            thread_ts="1757674001.149799",
            slack_user_name="joe randazzo",
            current_message_full_text="Test message",
            slack_user_id="U123456",
            trigger_id="trigger123"
        )
        
        # Verify the refunds utils was called with correct parameters
        self.mock_refunds_utils.handle_process_refund.assert_called_once()
        call_args = self.mock_refunds_utils.handle_process_refund.call_args
        
        # Check that the custom amount was preserved (args are positional)
        passed_request_data = call_args[0][0]
        passed_channel_id = call_args[0][1]
        passed_requestor_name = call_args[0][2]
        passed_requestor_email = call_args[0][3]
        
        assert passed_request_data["refundAmount"] == "25.50"
        assert passed_request_data["refundType"] == "credit"
        assert passed_request_data["orderId"] == "gid://shopify/Order/5877381955678"
        
        # Verify other parameters
        assert passed_channel_id == "C092RU7R6PL"
        assert passed_requestor_name == requestor_name
        assert passed_requestor_email == requestor_email

    @pytest.mark.asyncio
    async def test_handle_process_refund_with_decimal_amounts(self):
        """Test various decimal amount formats from custom modal input"""
        
        test_amounts = ["1.99", "100", "0.50", "1234.56", "15.00"]
        
        for amount in test_amounts:
            # Reset the mock for each iteration
            self.mock_refunds_utils.handle_process_refund.reset_mock()
            
            request_data = {
                "orderId": "gid://shopify/Order/1234567890",
                "rawOrderNumber": "#12345",
                "refundAmount": amount,
                "refundType": "refund",
                "orderCancelled": "false",
            }
            
            # Call the method
            await self.slack_service.handle_process_refund(
                request_data=request_data,
                channel_id="C092RU7R6PL",
                requestor_name={"first": "Test", "last": "User"},
                requestor_email="test@example.com",
                thread_ts="1757674001.149799",
                slack_user_name="test user",
                current_message_full_text="Test message",
                slack_user_id="U123456"
            )
            
            # Verify the amount was passed correctly (args are positional)
            call_args = self.mock_refunds_utils.handle_process_refund.call_args
            passed_request_data = call_args[0][0]
            assert passed_request_data["refundAmount"] == amount

    @pytest.mark.asyncio 
    async def test_handle_process_refund_credit_vs_refund_types(self):
        """Test that both credit and refund types work with custom amounts"""
        
        test_cases = [
            ("credit", "25.50"),
            ("refund", "15.00"),
            ("CREDIT", "100.00"),  # Test case insensitivity
            ("REFUND", "0.99")
        ]
        
        for refund_type, amount in test_cases:
            # Reset the mock for each iteration
            self.mock_refunds_utils.handle_process_refund.reset_mock()
            
            request_data = {
                "orderId": "gid://shopify/Order/1234567890",
                "rawOrderNumber": "#12345",
                "refundAmount": amount,
                "refundType": refund_type,
                "orderCancelled": "false",
            }
            
            # Call the method
            await self.slack_service.handle_process_refund(
                request_data=request_data,
                channel_id="C092RU7R6PL",
                requestor_name={"first": "Test", "last": "User"},
                requestor_email="test@example.com",
                thread_ts="1757674001.149799",
                slack_user_name="test user",
                current_message_full_text="Test message",
                slack_user_id="U123456"
            )
            
            # Verify both amount and type were passed correctly (args are positional)
            call_args = self.mock_refunds_utils.handle_process_refund.call_args
            passed_request_data = call_args[0][0]
            assert passed_request_data["refundAmount"] == amount
            assert passed_request_data["refundType"] == refund_type

    @pytest.mark.asyncio
    async def test_handle_process_refund_preserves_metadata(self):
        """Test that all metadata from the modal is preserved during processing"""
        
        request_data = {
            "orderId": "gid://shopify/Order/5877381955678",
            "rawOrderNumber": "#42366", 
            "refundAmount": "75.25",
            "refundType": "credit",
            "orderCancelled": "false",
        }
        
        requestor_name = {"first": "Jane", "last": "Smith"}
        requestor_email = "jane.smith@example.com"
        channel_id = "C092RU7R6PL"
        thread_ts = "1757674001.149799"
        slack_user_name = "staff member"
        slack_user_id = "U987654"
        current_message_full_text = "Original message content with details"
        trigger_id = "trigger_id_123"
        
        # Call the method with all parameters
        await self.slack_service.handle_process_refund(
            request_data=request_data,
            channel_id=channel_id,
            requestor_name=requestor_name,
            requestor_email=requestor_email,
            thread_ts=thread_ts,
            slack_user_name=slack_user_name,
            current_message_full_text=current_message_full_text,
            slack_user_id=slack_user_id,
            trigger_id=trigger_id
        )
        
        # Verify all parameters were passed through correctly
        self.mock_refunds_utils.handle_process_refund.assert_called_once()
        call_args = self.mock_refunds_utils.handle_process_refund.call_args
        
        # Check all parameters (args are positional)
        passed_request_data = call_args[0][0]
        passed_channel_id = call_args[0][1]
        passed_requestor_name = call_args[0][2]
        passed_requestor_email = call_args[0][3]
        passed_thread_ts = call_args[0][4]
        passed_slack_user_name = call_args[0][5]
        passed_current_message_full_text = call_args[0][6]
        passed_slack_user_id = call_args[0][7]
        passed_trigger_id = call_args[0][8]
        
        assert passed_request_data == request_data
        assert passed_channel_id == channel_id
        assert passed_requestor_name == requestor_name
        assert passed_requestor_email == requestor_email
        assert passed_thread_ts == thread_ts
        assert passed_slack_user_name == slack_user_name
        assert passed_current_message_full_text == current_message_full_text
        assert passed_slack_user_id == slack_user_id
        assert passed_trigger_id == trigger_id

    @pytest.mark.asyncio
    async def test_handle_process_refund_returns_result(self):
        """Test that the result from refunds utils is returned correctly"""
        
        # Mock a specific return value
        expected_result = {
            "success": True,
            "message": "Refund of $25.50 processed successfully",
            "shopify_response": {"id": "refund_123"}
        }
        self.mock_refunds_utils.handle_process_refund.return_value = expected_result
        
        request_data = {
            "orderId": "gid://shopify/Order/5877381955678",
            "rawOrderNumber": "#42366",
            "refundAmount": "25.50",
            "refundType": "credit",
            "orderCancelled": "false",
        }
        
        # Call the method
        result = await self.slack_service.handle_process_refund(
            request_data=request_data,
            channel_id="C092RU7R6PL",
            requestor_name={"first": "John", "last": "Doe"},
            requestor_email="test@example.com",
            thread_ts="1757674001.149799",
            slack_user_name="joe randazzo",
            current_message_full_text="Test message",
            slack_user_id="U123456"
        )
        
        # Verify the result is returned correctly
        assert result == expected_result
