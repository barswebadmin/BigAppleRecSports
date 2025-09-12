"""
Comprehensive tests for Slack modal handlers - update and deny logic
"""

import pytest
import json
from unittest.mock import Mock, patch
from backend.services.slack.modal_handlers import SlackModalHandlers


class TestSlackModalHandlers:
    """Test suite for SlackModalHandlers"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_api_client = Mock()
        self.gas_webhook_url = "https://script.google.com/test-webhook"
        self.handler = SlackModalHandlers(self.mock_api_client, self.gas_webhook_url)

    @pytest.mark.asyncio
    async def test_show_deny_refund_request_modal_success(self):
        """Test successful modal display for deny request"""
        # Setup
        self.mock_api_client.send_modal.return_value = {
            "success": True,
            "view": {"id": "V123"},
        }

        request_data = {
            "rawOrderNumber": "#42234",
            "requestorEmail": "test@example.com",
            "first": "John",
            "last": "Doe",
            "refundType": "refund",
            "requestSubmittedAt": "09/10/25 at 2:00 AM",
        }

        # Execute
        result = await self.handler.show_deny_refund_request_modal(
            request_data=request_data,
            channel_id="C123",
            thread_ts="1234567890.123456",
            slack_user_name="staff_user",
            slack_user_id="U123",
            trigger_id="trigger123",
            current_message_full_text="Test message",
        )

        # Verify
        assert result["success"] is True
        assert result["message"] == "Modal displayed"

        # Check that send_modal was called with correct parameters
        self.mock_api_client.send_modal.assert_called_once()
        call_args = self.mock_api_client.send_modal.call_args

        # Verify trigger_id
        assert call_args[0][0] == "trigger123"

        # Verify modal structure
        modal_view = call_args[0][1]
        assert modal_view["type"] == "modal"
        assert modal_view["callback_id"] == "deny_refund_request_modal_submission"
        assert modal_view["title"]["text"] == "Deny Refund Request"

        # Verify private metadata contains all required fields
        private_metadata = json.loads(modal_view["private_metadata"])
        assert private_metadata["raw_order_number"] == "#42234"
        assert private_metadata["requestor_email"] == "test@example.com"
        assert private_metadata["first_name"] == "John"
        assert private_metadata["last_name"] == "Doe"
        assert private_metadata["original_thread_ts"] == "1234567890.123456"
        assert private_metadata["original_channel_id"] == "C123"
        assert private_metadata["slack_user_name"] == "staff_user"
        assert private_metadata["slack_user_id"] == "U123"

    @pytest.mark.asyncio
    async def test_show_deny_refund_request_modal_api_failure(self):
        """Test modal display when Slack API fails"""
        # Setup
        self.mock_api_client.send_modal.return_value = {
            "success": False,
            "error": "API Error",
        }

        request_data = {
            "rawOrderNumber": "#42234",
            "requestorEmail": "test@example.com",
            "first": "John",
            "last": "Doe",
            "refundType": "refund",
        }

        # Execute
        result = await self.handler.show_deny_refund_request_modal(
            request_data=request_data,
            channel_id="C123",
            thread_ts="1234567890.123456",
            slack_user_name="staff_user",
            slack_user_id="U123",
            trigger_id="trigger123",
            current_message_full_text="Test message",
        )

        # Verify
        assert result["success"] is False
        assert "Slack API error: API Error" in result["message"]

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_handle_deny_refund_request_modal_submission_success(self, mock_post):
        """Test successful modal submission processing"""
        # Setup
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = '{"success": true}'
        mock_post.return_value.raise_for_status = Mock()

        self.mock_api_client.update_message.return_value = {"success": True}

        payload = {
            "view": {
                "state": {
                    "values": {
                        "custom_message_input": {
                            "custom_message": {"value": "Custom denial message"}
                        },
                        "include_staff_info": {
                            "include_staff_info": {
                                "selected_options": [{"value": "include_staff"}]
                            }
                        },
                    }
                },
                "private_metadata": json.dumps(
                    {
                        "raw_order_number": "#42234",
                        "requestor_email": "test@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "original_thread_ts": "1234567890.123456",
                        "original_channel_id": "C123",
                        "slack_user_name": "staff_user",
                        "slack_user_id": "U123",
                    }
                ),
            }
        }

        # Execute
        result = await self.handler.handle_deny_refund_request_modal_submission(payload)

        # Verify
        assert result["response_action"] == "clear"

        # Verify GAS request was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == self.gas_webhook_url

        # Verify request payload
        request_data = call_args[1]["json"]
        assert request_data["action"] == "send_denial_email"
        assert request_data["order_number"] == "#42234"
        assert request_data["requestor_email"] == "test@example.com"
        assert request_data["first_name"] == "John"
        assert request_data["custom_message"] == "Custom denial message"
        assert request_data["include_staff_info"] is True
        assert request_data["slack_user_name"] == "staff_user"

        # Verify Slack message update was called
        self.mock_api_client.update_message.assert_called_once()
        update_call = self.mock_api_client.update_message.call_args
        assert update_call[1]["message_ts"] == "1234567890.123456"
        assert "🚫 *Refund Request Denied*" in update_call[1]["message_text"]
        assert "staff_user" in update_call[1]["message_text"]

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_handle_deny_refund_request_modal_submission_no_staff_info(
        self, mock_post
    ):
        """Test modal submission without including staff info"""
        # Setup
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = '{"success": true}'
        mock_post.return_value.raise_for_status = Mock()

        self.mock_api_client.update_message.return_value = {"success": True}

        payload = {
            "view": {
                "state": {
                    "values": {
                        "custom_message_input": {"custom_message": {"value": ""}},
                        "include_staff_info": {
                            "include_staff_info": {
                                "selected_options": []
                            }  # No staff info
                        },
                    }
                },
                "private_metadata": json.dumps(
                    {
                        "raw_order_number": "#42234",
                        "requestor_email": "test@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "original_thread_ts": "1234567890.123456",
                        "original_channel_id": "C123",
                        "slack_user_name": "staff_user",
                        "slack_user_id": "U123",
                    }
                ),
            }
        }

        # Execute
        result = await self.handler.handle_deny_refund_request_modal_submission(payload)

        # Verify
        assert result["response_action"] == "clear"

        # Verify GAS request parameters
        mock_post.assert_called_once()
        request_data = mock_post.call_args[1]["json"]
        assert request_data["include_staff_info"] is False
        assert request_data["custom_message"] == ""

        # Verify confirmation message mentions default message and web@bigapplerecsports.com
        update_call = self.mock_api_client.update_message.call_args
        confirmation_message = update_call[1]["message_text"]
        assert "Default denial message sent" in confirmation_message
        assert "web@bigapplerecsports.com" in confirmation_message

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_handle_deny_refund_request_modal_submission_gas_failure(
        self, mock_post
    ):
        """Test modal submission when GAS request fails"""
        # Setup - GAS request fails
        mock_post.side_effect = Exception("Network error")

        payload = {
            "view": {
                "state": {
                    "values": {
                        "custom_message_input": {
                            "custom_message": {"value": "Test message"}
                        },
                        "include_staff_info": {
                            "include_staff_info": {"selected_options": []}
                        },
                    }
                },
                "private_metadata": json.dumps(
                    {
                        "raw_order_number": "#42234",
                        "requestor_email": "test@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "original_thread_ts": "1234567890.123456",
                        "original_channel_id": "C123",
                        "slack_user_name": "staff_user",
                        "slack_user_id": "U123",
                    }
                ),
            }
        }

        # Execute
        result = await self.handler.handle_deny_refund_request_modal_submission(payload)

        # Verify - should still return clear to close modal
        assert result["response_action"] == "clear"

        # Verify error was logged
        mock_post.assert_called_once()

    def test_build_denial_confirmation_message_with_custom_message(self):
        """Test denial confirmation message building with custom message"""
        # Execute
        message = self.handler._build_denial_confirmation_message(
            order_number="#42234",
            requestor_email="test@example.com",
            first_name="John",
            last_name="Doe",
            slack_user_name="staff_user",
            custom_message_provided=True,
            include_staff_info=True,
        )

        # Verify
        assert "🚫 *Refund Request Denied*" in message
        assert "*Order Number:* #42234" in message
        assert "*Requestor:* John Doe (test@example.com)" in message
        assert "*Denied by:* staff_user" in message
        assert "Custom denial message sent" in message
        assert "Staff contact info included" in message

    def test_build_denial_confirmation_message_default(self):
        """Test denial confirmation message building with default settings"""
        # Execute
        message = self.handler._build_denial_confirmation_message(
            order_number="#42234",
            requestor_email="test@example.com",
            first_name="John",
            last_name="Doe",
            slack_user_name="staff_user",
            custom_message_provided=False,
            include_staff_info=False,
        )

        # Verify
        assert "Default denial message sent" in message
        assert "web@bigapplerecsports.com" in message
        assert "Staff contact info" not in message

    @pytest.mark.asyncio
    async def test_update_slack_message_success(self):
        """Test successful Slack message update"""
        # Setup
        self.mock_api_client.update_message.return_value = {"success": True}

        # Execute
        result = await self.handler._update_slack_message(
            channel_id="C123",
            message_ts="1234567890.123456",
            message_text="Updated message",
        )

        # Verify
        assert result["success"] is True
        self.mock_api_client.update_message.assert_called_once_with(
            message_ts="1234567890.123456",
            message_text="Updated message",
            action_buttons=[],
        )

    @pytest.mark.asyncio
    async def test_update_slack_message_failure(self):
        """Test Slack message update failure"""
        # Setup
        self.mock_api_client.update_message.side_effect = Exception("API Error")

        # Execute
        result = await self.handler._update_slack_message(
            channel_id="C123",
            message_ts="1234567890.123456",
            message_text="Updated message",
        )

        # Verify
        assert result["success"] is False
        assert "API Error" in result["error"]


class TestModalBlockBuilding:
    """Test suite for modal block building logic"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_api_client = Mock()
        self.gas_webhook_url = "https://script.google.com/test-webhook"
        self.handler = SlackModalHandlers(self.mock_api_client, self.gas_webhook_url)

    @patch("backend.services.slack.slack_refunds_utils.SlackRefundsUtils")
    def test_build_deny_request_modal_blocks_delegates_to_utils(self, mock_utils_class):
        """Test that modal block building delegates to SlackRefundsUtils"""
        # Setup
        mock_utils_instance = Mock()
        mock_utils_class.return_value = mock_utils_instance
        mock_utils_instance._build_deny_request_modal_blocks.return_value = [
            {"type": "section"}
        ]

        # Execute
        result = self.handler._build_deny_request_modal_blocks(
            raw_order_number="#42234",
            requestor_email="test@example.com",
            first_name="John",
            last_name="Doe",
            refund_type="refund",
        )

        # Verify
        assert result == [{"type": "section"}]

        # Verify constructor was called with correct args
        mock_utils_class.assert_called_once_with(None, None)

        # Verify method was called
        mock_utils_instance._build_deny_request_modal_blocks.assert_called_once_with(
            raw_order_number="#42234",
            requestor_email="test@example.com",
            first_name="John",
            last_name="Doe",
            refund_type="refund",
        )

    def test_show_modal_to_user_structure(self):
        """Test modal view structure creation"""
        # Setup
        self.mock_api_client.send_modal.return_value = {"success": True}

        modal_blocks = [
            {"type": "section", "text": {"type": "plain_text", "text": "Test"}}
        ]

        # Execute
        self.handler._show_modal_to_user(
            trigger_id="trigger123",
            modal_title="Test Modal",
            modal_blocks=modal_blocks,
            callback_id="test_callback",
            private_metadata='{"test": "data"}',
        )

        # Verify
        call_args = self.mock_api_client.send_modal.call_args
        modal_view = call_args[0][1]

        assert modal_view["type"] == "modal"
        assert modal_view["callback_id"] == "test_callback"
        assert modal_view["title"]["text"] == "Test Modal"
        assert modal_view["submit"]["text"] == "Send Denial"
        assert modal_view["close"]["text"] == "Cancel"
        assert modal_view["blocks"] == modal_blocks
        assert modal_view["private_metadata"] == '{"test": "data"}'


if __name__ == "__main__":
    pytest.main([__file__])
