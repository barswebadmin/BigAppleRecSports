#!/usr/bin/env python3
"""
Tests for Slack dynamic client creation and channel persistence logic.
Tests the core functionality for creating API clients with different tokens/channels.
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch

# Add the backend directory to Python path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from services.slack.slack_refunds_utils import SlackRefundsUtils
from services.slack.api_client import SlackApiClient, MockSlackApiClient
from services.orders.orders_service import OrdersService
from config import Settings


class TestSlackDynamicClient:
    """Test suite for Slack dynamic client creation"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_orders_service = Mock(spec=OrdersService)
        self.mock_settings = Mock(spec=Settings)
        self.mock_settings.environment = "development"

        self.slack_utils = SlackRefundsUtils(
            orders_service=self.mock_orders_service, settings=self.mock_settings
        )

    def test_create_dynamic_api_client_with_real_token(self):
        """Test _create_dynamic_api_client creates SlackApiClient for real tokens"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            client = self.slack_utils._create_dynamic_api_client(
                channel_id="C092RU7R6PL", bot_token="xoxb-real-token"
            )

            assert isinstance(client, SlackApiClient)
            assert client.channel_id == "C092RU7R6PL"
            assert client.bearer_token == "xoxb-real-token"

    def test_create_dynamic_api_client_with_mock_token(self):
        """Test _create_dynamic_api_client creates MockSlackApiClient for test tokens"""
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            client = self.slack_utils._create_dynamic_api_client(
                channel_id="C092RU7R6PL", bot_token="xoxb-test-mock-token"
            )

            assert isinstance(client, MockSlackApiClient)
            assert client.channel_id == "C092RU7R6PL"

    def test_create_dynamic_api_client_with_none_values(self):
        """Test _create_dynamic_api_client handles None values gracefully"""
        client = self.slack_utils._create_dynamic_api_client(
            channel_id=None, bot_token=None
        )

        # Should still create a client, using defaults
        assert client is not None

    def test_show_modal_to_user_stores_metadata(self):
        """Test that _show_modal_to_user properly stores metadata"""
        mock_client = Mock(spec=SlackApiClient)
        mock_client.open_modal.return_value = {"ok": True}

        original_metadata = {
            "first": "Test",
            "last": "User",
            "original_thread_ts": "123.456",
            "original_channel_id": "C092RU7R6PL",
        }

        # Test the _show_modal_to_user method
        self.slack_utils._show_modal_to_user(
            client=mock_client,
            user_id="U0278M72535",
            trigger_id="test_trigger",
            modal_blocks=[],
            callback_id="test_callback",
            title="Test Modal",
            original_metadata=original_metadata,
            bot_token="xoxb-test-token",
        )

        # Verify modal was opened
        mock_client.open_modal.assert_called_once()
        call_args = mock_client.open_modal.call_args[1]

        # Verify the modal structure
        assert "view" in call_args
        assert "private_metadata" in call_args

        # Parse and verify the metadata
        import json

        private_metadata = json.loads(call_args["private_metadata"])
        assert private_metadata["original_bot_token"] == "xoxb-test-token"
        assert private_metadata["original_channel_id"] == "C092RU7R6PL"
        assert private_metadata["original_thread_ts"] == "123.456"

    def test_show_modal_custom_submit_text(self):
        """Test that _show_modal_to_user handles custom submit button text"""
        mock_client = Mock(spec=SlackApiClient)
        mock_client.open_modal.return_value = {"ok": True}

        original_metadata = {
            "first": "Test",
            "last": "User",
            "original_thread_ts": "123.456",
            "original_channel_id": "C092RU7R6PL",
        }

        # Test with custom submit text
        self.slack_utils._show_modal_to_user(
            client=mock_client,
            user_id="U0278M72535",
            trigger_id="test_trigger",
            modal_blocks=[],
            callback_id="test_callback",
            title="Test Modal",
            original_metadata=original_metadata,
            submit_text="Custom Submit",
        )

        # Verify modal was opened with custom submit text
        mock_client.open_modal.assert_called_once()
        call_args = mock_client.open_modal.call_args[1]
        modal_view = call_args["view"]

        assert modal_view["submit"]["text"] == "Custom Submit"

    def test_show_modal_default_submit_text(self):
        """Test that _show_modal_to_user uses default submit text when not specified"""
        mock_client = Mock(spec=SlackApiClient)
        mock_client.open_modal.return_value = {"ok": True}

        original_metadata = {
            "first": "Test",
            "last": "User",
            "original_thread_ts": "123.456",
            "original_channel_id": "C092RU7R6PL",
        }

        # Test without custom submit text
        self.slack_utils._show_modal_to_user(
            client=mock_client,
            user_id="U0278M72535",
            trigger_id="test_trigger",
            modal_blocks=[],
            callback_id="test_callback",
            title="Test Modal",
            original_metadata=original_metadata,
        )

        # Verify modal was opened with default submit text
        mock_client.open_modal.assert_called_once()
        call_args = mock_client.open_modal.call_args[1]
        modal_view = call_args["view"]

        assert modal_view["submit"]["text"] == "Submit"


class TestSlackUtilsIntegration:
    """Integration tests for SlackRefundsUtils with mocked dependencies"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_orders_service = Mock(spec=OrdersService)
        self.mock_settings = Mock(spec=Settings)
        self.mock_settings.environment = "development"
        self.mock_settings.slack_refunds_bot_token = "xoxb-test-token"

        self.slack_utils = SlackRefundsUtils(
            orders_service=self.mock_orders_service, settings=self.mock_settings
        )

    def test_slack_utils_initialization(self):
        """Test that SlackRefundsUtils initializes correctly"""
        assert self.slack_utils.orders_service == self.mock_orders_service
        assert self.slack_utils.settings == self.mock_settings
        assert self.slack_utils.message_builder is not None

    def test_parse_button_value(self):
        """Test button value parsing functionality"""
        test_value = (
            "orderName=#12345|requestorName=Test User|requestorEmail=test@example.com"
        )

        result = self.slack_utils.parse_button_value(test_value)

        assert result["orderName"] == "#12345"
        assert result["requestorName"] == "Test User"
        assert result["requestorEmail"] == "test@example.com"

    def test_parse_button_value_with_empty_values(self):
        """Test button value parsing with empty values"""
        test_value = "orderName=#12345|requestorName=|requestorEmail=test@example.com"

        result = self.slack_utils.parse_button_value(test_value)

        assert result["orderName"] == "#12345"
        assert result["requestorName"] == ""
        assert result["requestorEmail"] == "test@example.com"

    def test_extract_sheet_link(self):
        """Test sheet link extraction from message text"""
        message_text = """
        Some message content
        🔗 *<https://docs.google.com/spreadsheets/d/123/edit#gid=456&range=A1:A1|View Request in Google Sheets>*
        More content
        """

        result = self.slack_utils.extract_sheet_link(message_text)

        assert (
            "https://docs.google.com/spreadsheets/d/123/edit#gid=456&range=A1:A1"
            in result
        )

    def test_extract_sheet_link_not_found(self):
        """Test sheet link extraction when no link is present"""
        message_text = "Some message without a sheet link"

        result = self.slack_utils.extract_sheet_link(message_text)

        assert result == ""


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
