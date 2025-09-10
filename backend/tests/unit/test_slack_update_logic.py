"""
Comprehensive tests for Slack update logic - edit request details functionality
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from backend.services.slack.slack_refunds_utils import SlackRefundsUtils


class TestSlackUpdateLogic:
    """Test suite for edit request details functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_api_client = Mock()
        self.mock_message_builder = Mock()
        self.mock_orders_service = Mock()
        self.mock_settings = Mock()
        
        self.utils = SlackRefundsUtils(
            orders_service=self.mock_orders_service,
            settings=self.mock_settings
        )
        # Manually set the injected dependencies for testing
        self.utils.api_client = self.mock_api_client  
        self.utils.message_builder = self.mock_message_builder
    
    @pytest.mark.asyncio
    async def test_handle_edit_request_details_success(self):
        """Test successful edit request details modal display"""
        # Setup
        self.mock_api_client.send_modal.return_value = {"success": True}
        
        request_data = {
            "rawOrderNumber": "#42234",
            "requestorEmail": "old@example.com",
            "first": "John",
            "last": "Doe"
        }
        
        # Execute
        result = await self.utils.handle_edit_request_details(
            request_data=request_data,
            channel_id="C123",
            thread_ts="1234567890.123456",
            slack_user_name="staff_user",
            slack_user_id="U123",
            trigger_id="trigger123",
            current_message_full_text="Test message"
        )
        
        # Verify
        assert result["success"] is True
        
        # Verify modal was called with correct parameters
        self.mock_api_client.send_modal.assert_called_once()
        call_args = self.mock_api_client.send_modal.call_args
        
        # Check trigger_id
        assert call_args[0][0] == "trigger123"
        
        # Check modal structure
        modal_view = call_args[0][1]
        assert modal_view["callback_id"] == "edit_request_details_submission"
        assert modal_view["title"]["text"] == "Edit Request Details"
        
        # Check private metadata includes original message context
        private_metadata = json.loads(modal_view["private_metadata"])
        assert private_metadata["original_thread_ts"] == "1234567890.123456"
        assert private_metadata["original_channel_id"] == "C123"
        
        # Check modal blocks for order number and email fields
        blocks = modal_view["blocks"]
        order_field = next((b for b in blocks if b.get("block_id") == "order_number_input"), None)
        assert order_field is not None
        assert order_field["element"]["initial_value"] == "42234"  # Without #
        
        email_field = next((b for b in blocks if b.get("block_id") == "requestor_email_input"), None)
        assert email_field is not None
        assert email_field["element"]["initial_value"] == "old@example.com"
    
    @pytest.mark.asyncio
    async def test_handle_edit_request_details_modal_failure(self):
        """Test edit request details when modal display fails"""
        # Setup
        self.mock_api_client.send_modal.return_value = {"success": False, "error": "Modal error"}
        
        request_data = {
            "rawOrderNumber": "#42234",
            "requestorEmail": "test@example.com"
        }
        
        # Execute
        result = await self.utils.handle_edit_request_details(
            request_data=request_data,
            channel_id="C123",
            thread_ts="1234567890.123456",
            slack_user_name="staff_user",
            slack_user_id="U123",
            trigger_id="trigger123",
            current_message_full_text="Test message"
        )
        
        # Verify
        assert result["success"] is False
        assert "Modal error" in result["message"]
    
    @pytest.mark.asyncio
    async def test_handle_edit_request_details_submission_success_validation(self):
        """Test successful submission with valid order and email"""
        # Setup - mock successful order validation
        self.mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": {
                "id": "5875167625310",
                "name": "#42235",
                "customer": {"email": "correct@example.com"}
            }
        }
        
        # Mock refund calculation
        self.mock_orders_service.calculate_refund_due.return_value = {
            "success": True, 
            "refund_amount": 95.00
        }
        
        # Mock successful Slack message update
        self.mock_message_builder.build_success_message.return_value = {
            "text": "Updated success message",
            "action_buttons": [{"type": "button", "text": "Cancel Order"}]
        }
        
        # Mock the update slack method
        self.utils.update_slack_on_shopify_success = Mock(return_value={"success": True})
        
        payload = {
            "view": {
                "state": {
                    "values": {
                        "order_number_input": {
                            "order_number": {"value": "42235"}
                        },
                        "requestor_email_input": {
                            "requestor_email": {"value": "correct@example.com"}
                        }
                    }
                },
                "private_metadata": json.dumps({
                    "raw_order_number": "#42234",
                    "requestor_email": "old@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "refund_type": "refund",
                    "original_thread_ts": "1234567890.123456",
                    "original_channel_id": "C123"
                })
            }
        }
        
        # Execute
        result = await self.utils.handle_edit_request_details_submission(payload)
        
        # Verify
        assert result["response_action"] == "clear"
        
        # Verify order lookup was called with new values
        self.mock_orders_service.fetch_order_details_by_email_or_order_name.assert_called_once_with(
            order_name="42235"
        )
        
        # Verify success message was built
        self.mock_message_builder.build_success_message.assert_called_once()
        
        # Verify message update was called (through update_slack_on_shopify_success)
        # This is an internal method call, so we verify the overall flow worked
    
    @pytest.mark.asyncio 
    async def test_handle_edit_request_details_submission_order_not_found(self):
        """Test submission when updated order number is not found"""
        # Setup - mock order not found
        self.mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": False,
            "message": "Order not found"
        }
        
        # Mock error message building
        self.mock_message_builder.build_error_message.return_value = {
            "text": "Order not found error message",
            "action_buttons": []
        }
        
        payload = {
            "view": {
                "state": {
                    "values": {
                        "order_number_input": {
                            "order_number": {"value": "99999"}
                        },
                        "requestor_email_input": {
                            "requestor_email": {"value": "test@example.com"}
                        }
                    }
                },
                "private_metadata": json.dumps({
                    "original_thread_ts": "1234567890.123456",
                    "original_channel_id": "C123"
                })
            }
        }
        
        # Execute
        result = await self.utils.handle_edit_request_details_submission(payload)
        
        # Verify
        assert result["response_action"] == "clear"
        
        # Verify error message was built
        self.mock_message_builder.build_error_message.assert_called_once()
        error_call = self.mock_message_builder.build_error_message.call_args
        assert error_call[1]["error_type"] == "order_not_found"
        assert error_call[1]["raw_order_number"] == "99999"
    
    @pytest.mark.asyncio
    async def test_handle_edit_request_details_submission_email_mismatch_persists(self):
        """Test submission when email mismatch still exists after update"""
        # Setup - mock order found but email still doesn't match
        self.mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": {
                "order": {
                    "id": "5875167625310", 
                    "name": "#42235",
                    "customer": {"email": "different@example.com"}
                }
            }
        }
        
        # Mock email mismatch message building
        self.mock_message_builder.build_error_message.return_value = {
            "text": "Email mismatch error message",
            "action_buttons": [{"type": "button", "text": "Edit Details"}]
        }
        
        payload = {
            "view": {
                "state": {
                    "values": {
                        "order_number_input": {
                            "order_number": {"value": "42235"}
                        },
                        "requestor_email_input": {
                            "requestor_email": {"value": "wrong@example.com"}
                        }
                    }
                },
                "private_metadata": json.dumps({
                    "first_name": "John",
                    "last_name": "Doe", 
                    "refund_type": "refund",
                    "original_thread_ts": "1234567890.123456",
                    "original_channel_id": "C123"
                })
            }
        }
        
        # Execute
        result = await self.utils.handle_edit_request_details_submission(payload)
        
        # Verify
        assert result["response_action"] == "clear"
        
        # Verify email mismatch error was built
        self.mock_message_builder.build_error_message.assert_called_once()
        error_call = self.mock_message_builder.build_error_message.call_args
        assert error_call[1]["error_type"] == "email_mismatch"
        assert error_call[1]["order_customer_email"] == "different@example.com"
    
    @pytest.mark.asyncio
    async def test_integration_flow_verification(self):
        """Test that the integration flow works as expected in real scenarios"""
        # This test verifies the overall flow without testing individual helper methods
        # that don't exist. Instead, we test the observable behavior.
        
        # Setup successful validation scenario  
        self.mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": {
                "id": "5875167625310",
                "name": "#42235",
                "customer": {"email": "correct@example.com"}
            }
        }
        
        self.mock_orders_service.calculate_refund_due.return_value = {
            "success": True, 
            "refund_amount": 95.00
        }
        
        self.mock_message_builder.build_success_message.return_value = {
            "text": "Success message",
            "action_buttons": []
        }
        
        self.utils.update_slack_on_shopify_success = Mock(return_value={"success": True})
        
        payload = {
            "view": {
                "state": {
                    "values": {
                        "order_number_input": {
                            "order_number": {"value": "42235"}
                        },
                        "requestor_email_input": {
                            "requestor_email": {"value": "correct@example.com"}
                        }
                    }
                },
                "private_metadata": json.dumps({
                    "first_name": "John",
                    "last_name": "Doe",
                    "refund_type": "refund",
                    "original_thread_ts": "1234567890.123456",
                    "original_channel_id": "C123"
                })
            }
        }
        
        # Execute
        result = await self.utils.handle_edit_request_details_submission(payload)
        
        # Verify success path
        assert result["response_action"] == "clear"
        
        # Verify order lookup was called
        self.mock_orders_service.fetch_order_details_by_email_or_order_name.assert_called_once_with(
            order_name="42235"
        )


if __name__ == "__main__":
    pytest.main([__file__])
