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
from services.orders.orders_service import OrdersService
from config import Config


class TestSlackDynamicClient:
    """Test suite for Slack dynamic client creation"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_orders_service = Mock(spec=OrdersService)
        self.mock_config = Mock(spec=Config)
        self.mock_config.environment = "development"

        self.slack_utils = SlackRefundsUtils(
            orders_service=self.mock_orders_service, settings=self.mock_config
        )

    def test_create_dynamic_api_client_with_real_token(self):
        """Test _create_dynamic_api_client creates a client for real tokens"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            client = self.slack_utils._create_dynamic_api_client(
                channel_id="C092RU7R6PL", bot_token="xoxb-real-token"
            )

            # Just verify a client was created
            assert client is not None
            assert hasattr(client, "channel_id")

    def test_create_dynamic_api_client_with_mock_token(self):
        """Test _create_dynamic_api_client creates a client for test tokens"""
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            client = self.slack_utils._create_dynamic_api_client(
                channel_id="C092RU7R6PL", bot_token="xoxb-test-mock-token"
            )

            # Just verify a client was created
            assert client is not None
            assert hasattr(client, "channel_id")

    def test_create_dynamic_api_client_with_none_values(self):
        """Test _create_dynamic_api_client handles None values gracefully"""
        client = self.slack_utils._create_dynamic_api_client(
            channel_id=None, bot_token=None
        )

        # Should still create a client, using defaults
        assert client is not None

    def test_show_modal_functionality_exists(self):
        """Test that _show_modal_to_user method exists and is callable"""
        # Just verify the method exists and can be called
        assert hasattr(self.slack_utils, "_show_modal_to_user")
        assert callable(getattr(self.slack_utils, "_show_modal_to_user"))


class TestSlackUtilsIntegration:
    """Integration tests for SlackRefundsUtils with mocked dependencies"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_orders_service = Mock(spec=OrdersService)
        self.mock_config = Mock(spec=Config)
        self.mock_config.environment = "development"
        self.mock_config.slack_refunds_bot_token = "xoxb-test-token"

        self.slack_utils = SlackRefundsUtils(
            orders_service=self.mock_orders_service, settings=self.mock_config
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

        # The method returns a fallback URL when no link is found
        assert "docs.google.com/spreadsheets" in result


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
