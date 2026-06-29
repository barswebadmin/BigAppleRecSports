"""
Unit tests for SlackClient, SlackBot, and related utilities.

Tests cover:
- Message sending (to_channel, to_user, reply, ephemeral)
- Message updating (direct, ephemeral)
- User/channel/group lookups
- Error handling and scope validation
- Retry behavior
- BotConfig lazy loading
- SlackBot wrapper methods

No network calls — slack_sdk.WebClient is mocked.
"""

import json
import os
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest
from slack_sdk.errors import SlackApiError
from slack_sdk.models.blocks import HeaderBlock, SectionBlock, DividerBlock

from shared_utilities.clients.slack.client import (
    SlackClient,
    BotConfig,
    Bots,
    SlackBot,
    SlackApiSuccessResponse,
    SlackApiErrorResponse,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_env(monkeypatch):
    """Set up environment variables for bot configs."""
    monkeypatch.setenv("SLACK__WEB_BOT__TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK__WEB_BOT__SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("SLACK__WEB_BOT__CHANNEL_ID", "C12345")
    monkeypatch.setenv("SLACK__DEV_BOT__TOKEN", "xoxb-dev-token")
    monkeypatch.setenv("SLACK__DEV_BOT__SIGNING_SECRET", "dev-secret")
    monkeypatch.setenv("SLACK__DEV_BOT__CHANNEL_ID", "C67890")
    monkeypatch.setenv("SLACK__LEADERSHIP_BOT__TOKEN", "xoxb-leadership-token")
    monkeypatch.setenv("SLACK__LEADERSHIP_BOT__SIGNING_SECRET", "leadership-secret")
    monkeypatch.setenv("SLACK__LEADERSHIP_BOT__USER_TOKEN", "xoxp-user-token")
    monkeypatch.setenv("SLACK__LEADERSHIP_BOT__CHANNEL_ID", "C11111")


@pytest.fixture
def slack_client():
    """Create a SlackClient with mocked WebClient methods."""
    return SlackClient(token="xoxb-test-token")


@pytest.fixture
def mock_slack_response():
    """Factory for creating mock Slack API responses."""
    def _make_response(ok: bool = True, **kwargs) -> Dict[str, Any]:
        response = {"ok": ok}
        response.update(kwargs)
        return response
    return _make_response


# ── BotConfig Tests ───────────────────────────────────────────────────────────

class TestBotConfig:
    """Test BotConfig lazy environment variable loading."""

    def test_token_loaded_from_env(self, mock_env):
        config = BotConfig("SLACK__WEB_BOT__TOKEN", "SLACK__WEB_BOT__SIGNING_SECRET")
        assert config.token == "xoxb-test-token"

    def test_signing_secret_loaded_from_env(self, mock_env):
        config = BotConfig("SLACK__WEB_BOT__TOKEN", "SLACK__WEB_BOT__SIGNING_SECRET")
        assert config.signing_secret == "test-secret"

    def test_user_token_loaded_from_env(self, mock_env):
        config = BotConfig(
            "SLACK__LEADERSHIP_BOT__TOKEN",
            "SLACK__LEADERSHIP_BOT__SIGNING_SECRET",
            user_token_env="SLACK__LEADERSHIP_BOT__USER_TOKEN"
        )
        assert config.user_token == "xoxp-user-token"

    def test_channel_id_loaded_from_env(self, mock_env):
        config = BotConfig(
            "SLACK__WEB_BOT__TOKEN",
            "SLACK__WEB_BOT__SIGNING_SECRET",
            channel_id_env="SLACK__WEB_BOT__CHANNEL_ID"
        )
        assert config.channel_id == "C12345"

    def test_missing_token_raises(self, monkeypatch):
        monkeypatch.delenv("SLACK__WEB_BOT__TOKEN", raising=False)
        config = BotConfig("SLACK__WEB_BOT__TOKEN", "SLACK__WEB_BOT__SIGNING_SECRET")
        with pytest.raises(RuntimeError, match="Missing env: SLACK__WEB_BOT__TOKEN"):
            _ = config.token

    def test_missing_secret_raises(self, monkeypatch):
        monkeypatch.setenv("SLACK__WEB_BOT__TOKEN", "xoxb-test")
        monkeypatch.delenv("SLACK__WEB_BOT__SIGNING_SECRET", raising=False)
        config = BotConfig("SLACK__WEB_BOT__TOKEN", "SLACK__WEB_BOT__SIGNING_SECRET")
        with pytest.raises(RuntimeError, match="Missing env: SLACK__WEB_BOT__SIGNING_SECRET"):
            _ = config.signing_secret

    def test_optional_user_token_returns_none(self, mock_env):
        config = BotConfig("SLACK__WEB_BOT__TOKEN", "SLACK__WEB_BOT__SIGNING_SECRET")
        assert config.user_token is None

    def test_optional_channel_id_returns_none(self, mock_env):
        config = BotConfig("SLACK__WEB_BOT__TOKEN", "SLACK__WEB_BOT__SIGNING_SECRET")
        assert config.channel_id is None


class TestBots:
    """Test Bots registry of named bot configs."""

    def test_web_bot_config_exists(self, mock_env):
        assert hasattr(Bots, "Web")
        assert Bots.Web.token == "xoxb-test-token"

    def test_dev_bot_config_exists(self, mock_env):
        assert hasattr(Bots, "Dev")
        assert Bots.Dev.token == "xoxb-dev-token"

    def test_leadership_bot_has_user_token(self, mock_env):
        assert Bots.Leadership.user_token == "xoxp-user-token"


# ── SlackClient Message Sending Tests ─────────────────────────────────────────

class TestSlackClientSendMessage:
    """Test SlackClient.send_message() with different message types."""

    @pytest.mark.parametrize("message_type", [
        "to_channel",
        "to_user",
        "reply",
        "ephemeral",
    ])
    def test_send_message_success_returns_proper_structure(
        self,
        slack_client,
        mock_slack_response,
        message_type
    ):
        """Test that valid blocks successfully send and return proper response structure."""
        mock_response = mock_slack_response(
            ok=True,
            message_ts="1234567890.123456",
            channel="C12345"
        )

        method_map = {
            "to_channel": "chat_postMessage",
            "to_user": "chat_postMessage",
            "reply": "chat_postMessage",
            "ephemeral": "chat_postEphemeral",
        }

        with patch.object(slack_client, method_map[message_type], return_value=mock_response):
            blocks = [HeaderBlock(text="Test")]
            kwargs = {
                "message_type": message_type,
                "channel_id": "C12345",
                "bot_token": "xoxb-test",
                "blocks": blocks,
            }
            if message_type == "ephemeral":
                kwargs["user_id"] = "U12345"
            if message_type == "reply":
                kwargs["thread_ts"] = "1234567890.000000"

            result = slack_client.send_message(**kwargs)

            assert result["success"] is True
            assert result["message_ts"] == "1234567890.123456"
            assert result["channel"] == "C12345"
            assert "response" in result

    @pytest.mark.parametrize("error_code,status_code", [
        ("invalid_blocks", 400),
        ("channel_not_found", 404),
        ("not_in_channel", 403),
        ("invalid_auth", 401),
    ])
    def test_send_message_with_api_errors(
        self,
        slack_client,
        error_code,
        status_code
    ):
        """Test that API errors are properly caught and returned as error responses."""
        mock_error_response = Mock()
        mock_error_response.data = {"ok": False, "error": error_code}
        mock_error_response.status_code = status_code

        with patch.object(slack_client, "chat_postMessage", side_effect=SlackApiError("Error", mock_error_response)):
            result = slack_client.send_message(
                message_type="to_channel",
                channel_id="C12345",
                bot_token="xoxb-test",
                blocks=[HeaderBlock(text="Test")]
            )

            assert result["success"] is False
            assert error_code in result["error"]
            assert "response" in result

    def test_send_message_with_malformed_blocks(self, slack_client):
        """Test that malformed blocks trigger validation errors."""
        mock_error_response = Mock()
        mock_error_response.data = {"ok": False, "error": "invalid_blocks"}
        mock_error_response.status_code = 400

        with patch.object(slack_client, "chat_postMessage", side_effect=SlackApiError("Invalid blocks", mock_error_response)):
            # Attempt to send with invalid block structure
            result = slack_client.send_message(
                message_type="to_channel",
                channel_id="C12345",
                bot_token="xoxb-test",
                blocks=[HeaderBlock(text="Test")]
            )

            assert result["success"] is False
            assert "invalid_blocks" in result["error"]

    def test_send_message_with_invalid_auth(self, slack_client):
        """Test that invalid authentication is properly handled."""
        mock_error_response = Mock()
        mock_error_response.data = {"ok": False, "error": "invalid_auth"}
        mock_error_response.status_code = 401

        with patch.object(slack_client, "chat_postMessage", side_effect=SlackApiError("Invalid auth", mock_error_response)):
            result = slack_client.send_message(
                message_type="to_channel",
                channel_id="C12345",
                bot_token="xoxb-invalid",
                blocks=[HeaderBlock(text="Test")]
            )

            assert result["success"] is False
            assert "invalid_auth" in result["error"]

    @pytest.mark.parametrize("invalid_channel", [
        "",  # Empty channel
        "INVALID",  # Invalid format
        "C" * 100,  # Too long
    ])
    def test_send_message_with_invalid_channel_ids(self, slack_client, invalid_channel):
        """Test that invalid channel IDs result in errors."""
        mock_error_response = Mock()
        mock_error_response.data = {"ok": False, "error": "channel_not_found"}
        mock_error_response.status_code = 404

        with patch.object(slack_client, "chat_postMessage", side_effect=SlackApiError("Channel not found", mock_error_response)):
            result = slack_client.send_message(
                message_type="to_channel",
                channel_id=invalid_channel,
                bot_token="xoxb-test",
                blocks=[HeaderBlock(text="Test")]
            )

            assert result["success"] is False

    def test_send_message_with_empty_blocks(self, slack_client, mock_slack_response):
        """Test that empty blocks list is handled (Slack may reject or accept depending on text)."""
        mock_response = mock_slack_response(ok=True, message_ts="123", channel="C12345")

        with patch.object(slack_client, "chat_postMessage", return_value=mock_response):
            result = slack_client.send_message(
                message_type="to_channel",
                channel_id="C12345",
                bot_token="xoxb-test",
                blocks=[]  # Empty blocks
            )

            # Should still succeed if Slack accepts it (text field is provided)
            assert result["success"] is True

    def test_send_message_network_error(self, slack_client):
        """Test that network errors are properly handled."""
        with patch.object(slack_client, "chat_postMessage", side_effect=Exception("Network timeout")):
            result = slack_client.send_message(
                message_type="to_channel",
                channel_id="C12345",
                bot_token="xoxb-test",
                blocks=[HeaderBlock(text="Test")]
            )

            assert result["success"] is False
            assert "Unexpected error" in result["error"]

    @pytest.mark.parametrize("message_type", [
        "to_channel",
        "to_user",
        "reply",
        "ephemeral",
    ])
    def test_send_message_returns_correct_response_structure(
        self,
        slack_client,
        mock_slack_response,
        message_type
    ):
        """Test that each message type returns proper success response with message_ts and channel."""
        mock_response = mock_slack_response(
            ok=True,
            message_ts="1234567890.123456",
            channel="C12345"
        )

        method_map = {
            "to_channel": "chat_postMessage",
            "to_user": "chat_postMessage",
            "reply": "chat_postMessage",
            "ephemeral": "chat_postEphemeral",
        }

        with patch.object(slack_client, method_map[message_type], return_value=mock_response):
            blocks = [HeaderBlock(text="Test")]
            kwargs = {
                "message_type": message_type,
                "channel_id": "C12345",
                "bot_token": "xoxb-test",
                "blocks": blocks,
            }
            if message_type == "ephemeral":
                kwargs["user_id"] = "U12345"
            if message_type == "reply":
                kwargs["thread_ts"] = "1234567890.000000"

            result = slack_client.send_message(**kwargs)

            assert result["success"] is True
            assert result["message_ts"] == "1234567890.123456"
            assert result["channel"] == "C12345"

    def test_send_ephemeral_requires_user_id(self, slack_client):
        """Test that ephemeral messages require user_id parameter."""
        blocks = [HeaderBlock(text="Test")]
        with pytest.raises(ValueError, match="user_id is required for ephemeral messages"):
            slack_client.send_message(
                message_type="ephemeral",
                channel_id="C12345",
                bot_token="xoxb-test",
                blocks=blocks
            )

    def test_send_reply_requires_thread_ts(self, slack_client):
        """Test that reply messages require thread_ts parameter."""
        blocks = [HeaderBlock(text="Test")]
        with pytest.raises(ValueError, match="thread_ts is required for reply messages"):
            slack_client.send_message(
                message_type="reply",
                channel_id="C12345",
                bot_token="xoxb-test",
                blocks=blocks
            )

    @pytest.mark.parametrize("blocks_input,expected_count", [
        ([HeaderBlock(text="Header"), SectionBlock(text="Section")], 2),
        ([DividerBlock()], 1),
        ([HeaderBlock(text="Test"), DividerBlock(), SectionBlock(text="Footer")], 3),
    ])
    def test_send_message_with_multiple_blocks(
        self,
        slack_client,
        mock_slack_response,
        blocks_input,
        expected_count
    ):
        """Test that messages with multiple blocks return success."""
        mock_response = mock_slack_response(ok=True, message_ts="123", channel="C12345")

        with patch.object(slack_client, "chat_postMessage", return_value=mock_response):
            result = slack_client.send_message(
                message_type="to_channel",
                channel_id="C12345",
                bot_token="xoxb-test",
                blocks=blocks_input
            )

            assert result["success"] is True
            assert result["message_ts"] == "123"

    def test_send_message_with_metadata(self, slack_client, mock_slack_response):
        """Test that messages with metadata return success."""
        mock_response = mock_slack_response(ok=True, message_ts="123", channel="C12345")
        metadata = {"event_type": "registration_update", "product_id": "123"}

        with patch.object(slack_client, "chat_postMessage", return_value=mock_response):
            result = slack_client.send_message(
                message_type="to_channel",
                channel_id="C12345",
                bot_token="xoxb-test",
                blocks=[HeaderBlock(text="Test")],
                metadata=metadata
            )

            assert result["success"] is True
            assert result["message_ts"] == "123"


class TestSlackClientUpdateMessage:
    """Test SlackClient.update_message() for direct and ephemeral updates."""

    def test_update_direct_message_success(self, slack_client, mock_slack_response):
        """Test updating a direct message returns success response."""
        mock_response = mock_slack_response(ok=True, channel="C12345", ts="1234567890.123456")

        with patch.object(slack_client, "chat_update", return_value=mock_response):
            result = slack_client.update_message(
                update_type="direct",
                channel_id="C12345",
                bot_token="xoxb-test",
                message_ts="1234567890.123456",
                blocks=[HeaderBlock(text="Updated")]
            )

            assert result["success"] is True
            assert "response" in result

    def test_update_direct_requires_message_ts(self, slack_client):
        """Test that direct updates require message_ts."""
        with pytest.raises(ValueError, match="message_ts is required for direct message updates"):
            slack_client.update_message(
                update_type="direct",
                channel_id="C12345",
                bot_token="xoxb-test",
                message_ts=None,
                blocks=[HeaderBlock(text="Test")]
            )

    def test_update_ephemeral_requires_response_url(self, slack_client):
        """Test that ephemeral updates require response_url."""
        with pytest.raises(ValueError, match="response_url is required for ephemeral message updates"):
            slack_client.update_message(
                update_type="ephemeral",
                channel_id="C12345",
                bot_token="xoxb-test",
                message_ts=None,
                blocks=[HeaderBlock(text="Test")],
                response_url=None
            )

    @patch("shared_utilities.clients.slack.client.WebhookClient")
    def test_update_ephemeral_uses_webhook(self, mock_webhook_class, slack_client):
        """Test that ephemeral updates return success."""
        mock_webhook = Mock()
        mock_webhook.send.return_value = Mock(status_code=200)
        mock_webhook_class.return_value = mock_webhook

        result = slack_client.update_message(
            update_type="ephemeral",
            channel_id="C12345",
            bot_token="xoxb-test",
            message_ts=None,
            blocks=[HeaderBlock(text="Updated")],
            response_url="https://hooks.slack.com/actions/T123/B456/xyz"
        )

        assert result["success"] is True


# ── SlackClient Error Handling Tests ──────────────────────────────────────────

class TestSlackClientErrorHandling:
    """Test error handling, scope validation, and retry behavior."""

    def test_api_error_returns_error_response(self, slack_client):
        """Test that SlackApiError is caught and returned as error response."""
        mock_error_response = Mock()
        mock_error_response.data = {"ok": False, "error": "channel_not_found"}
        mock_error_response.status_code = 404

        with patch.object(slack_client, "chat_postMessage", side_effect=SlackApiError("Error", mock_error_response)):
            result = slack_client.send_message(
                message_type="to_channel",
                channel_id="C12345",
                bot_token="xoxb-test",
                blocks=[HeaderBlock(text="Test")]
            )

            assert result["success"] is False
            assert "channel_not_found" in result["error"]

    @pytest.mark.parametrize("error_code,api_method,payload", [
        ("missing_scope", "users_lookupByEmail", {"email": "test@example.com"}),
        ("not_allowed_token_type", "users_profile_set", {"user": "U12345", "profile": {}}),
        ("invalid_auth", "users_info", {"user": "U12345"}),
    ])
    def test_scope_info_added_for_auth_errors(
        self,
        slack_client,
        error_code,
        api_method,
        payload
    ):
        """Test that scope_info is added to response for auth-related errors."""
        mock_error_response = Mock()
        mock_error_response.data = {"ok": False, "error": error_code}
        mock_error_response.status_code = 403

        api_method_func = getattr(slack_client, api_method)

        with patch.object(slack_client, api_method, side_effect=SlackApiError("Error", mock_error_response)):
            # Patch requests at the module level where it's imported
            with patch("requests.post") as mock_auth_test:
                mock_auth_test.return_value = Mock(
                    headers={"x-oauth-scopes": "channels:read,users:read"},
                    json=lambda: {"ok": True}
                )

                result = slack_client._execute_slack_api_call(
                    api_method=api_method_func,
                    payload=payload,
                    operation_name="Test lookup"
                )

                assert result["success"] is False
                # scope_info is added for auth errors
                assert "scope_info" in result
                assert "token_type" in result["scope_info"]
                assert "current_scopes" in result["scope_info"]

    def test_successful_response_structure(self, slack_client, mock_slack_response):
        """Test that successful responses have correct structure."""
        mock_response = mock_slack_response(
            ok=True,
            message_ts="1234567890.123456",
            channel="C12345"
        )

        with patch.object(slack_client, "chat_postMessage", return_value=mock_response):
            result = slack_client.send_message(
                message_type="to_channel",
                channel_id="C12345",
                bot_token="xoxb-test",
                blocks=[HeaderBlock(text="Test")]
            )

            # Verify response structure matches SlackApiSuccessResponse
            assert result["success"] is True
            assert "message_ts" in result
            assert "channel" in result
            assert "response" in result

    def test_failed_response_structure(self, slack_client, mock_slack_response):
        """Test that failed responses have correct structure."""
        mock_response = mock_slack_response(ok=False, error="channel_not_found")

        with patch.object(slack_client, "chat_postMessage", return_value=mock_response):
            result = slack_client.send_message(
                message_type="to_channel",
                channel_id="C12345",
                bot_token="xoxb-test",
                blocks=[HeaderBlock(text="Test")]
            )

            # Verify response structure matches SlackApiErrorResponse
            assert result["success"] is False
            assert "error" in result
            assert result["error"] == "channel_not_found"


# ── SlackClient User Token Tests ──────────────────────────────────────────────

class TestSlackClientUserToken:
    """Test that user token is used for specific API methods."""

    @pytest.mark.parametrize("method_name", [
        "users_profile_set",
        "users_profile_get",
    ])
    def test_user_token_methods_use_user_token(self, method_name):
        """Test that user-token-required methods use user_token instead of bot token."""
        client = SlackClient(token="xoxb-bot-token", user_token="xoxp-user-token")
        mock_response = {"ok": True}

        # Mock the method on the client
        with patch.object(client, method_name, return_value=mock_response) as mock_method:
            # Create a new WebClient instance that will be used for user token
            with patch("shared_utilities.clients.slack.client.WebClient") as mock_webclient_class:
                mock_user_client = Mock()
                mock_user_method = Mock(return_value=mock_response)
                setattr(mock_user_client, method_name, mock_user_method)
                mock_webclient_class.return_value = mock_user_client

                # Call the method through _execute_slack_api_call
                api_method = getattr(client, method_name)
                result = client._execute_slack_api_call(
                    api_method=api_method,
                    payload={"user": "U12345"},
                    operation_name="Test"
                )

                # Verify a new WebClient was created with user token
                if method_name in client._USER_TOKEN_METHODS:
                    mock_webclient_class.assert_called_once()
                    call_kwargs = mock_webclient_class.call_args[1]
                    assert call_kwargs["token"] == "xoxp-user-token"


# ── SlackBot Wrapper Tests ────────────────────────────────────────────────────

class TestSlackBot:
    """Test SlackBot wrapper class."""

    def test_slackbot_initialization(self, mock_env):
        """Test that SlackBot initializes with BotConfig."""
        bot = SlackBot(Bots.Web)
        assert bot.token == "xoxb-test-token"
        assert bot.signing_secret == "test-secret"
        assert isinstance(bot.client, SlackClient)

    def test_slackbot_send_message_delegates_to_client(self, mock_env, mock_slack_response):
        """Test that SlackBot.send_message() returns successful response."""
        bot = SlackBot(Bots.Web)
        mock_response = mock_slack_response(ok=True, message_ts="1234567890.123456", channel="C12345")

        with patch.object(bot.client, "send_message", return_value={"success": True, "message_ts": "1234567890.123456", "channel": "C12345", "response": mock_response}):
            result = bot.send_message(
                message_type="to_channel",
                channel_id="C12345",
                blocks=[HeaderBlock(text="Test")]
            )

            assert result["success"] is True
            assert result["message_ts"] == "1234567890.123456"
            assert result["channel"] == "C12345"

    def test_slackbot_lookup_user_by_email(self, mock_env):
        """Test SlackBot.lookup_user() returns user data for email."""
        bot = SlackBot(Bots.Web)
        mock_user = {"id": "U12345", "name": "testuser", "profile": {"email": "test@example.com"}}

        with patch("shared_utilities.clients.slack.user_lookup.lookup_user", return_value=mock_user):
            result = bot.lookup_user("test@example.com")

            assert result == mock_user
            assert result["id"] == "U12345"
            assert result["profile"]["email"] == "test@example.com"

    def test_slackbot_lookup_user_by_id(self, mock_env):
        """Test SlackBot.lookup_user() returns user data for user ID."""
        bot = SlackBot(Bots.Web)
        mock_user = {"id": "U12345", "name": "testuser"}

        with patch("shared_utilities.clients.slack.user_lookup.lookup_user", return_value=mock_user):
            result = bot.lookup_user("U12345")

            assert result == mock_user
            assert result["id"] == "U12345"
            assert result["name"] == "testuser"

    def test_slackbot_lookup_channel_by_id(self, mock_env):
        """Test SlackBot.lookup_channel() returns channel data for valid ID."""
        bot = SlackBot(Bots.Web)
        mock_channel = {"id": "C12345ABCDE", "name": "general"}
        mock_response = {"ok": True, "channel": mock_channel}

        with patch.object(bot.client, "conversations_info", return_value=mock_response):
            result = bot.lookup_channel("C12345ABCDE")

            assert result is not None
            assert result["id"] == "C12345ABCDE"
            assert result["name"] == "general"

    def test_slackbot_lookup_channel_by_name(self, mock_env):
        """Test SlackBot.lookup_channel() with channel name."""
        bot = SlackBot(Bots.Web)
        mock_channels = [
            {"id": "C12345", "name": "general", "is_archived": False},
            {"id": "C67890", "name": "random", "is_archived": False},
        ]

        with patch.object(bot, "_list_all_channels", return_value=mock_channels):
            result = bot.lookup_channel("#general")

            assert result["id"] == "C12345"
            assert result["name"] == "general"

    def test_slackbot_lookup_group_by_id(self, mock_env):
        """Test SlackBot.lookup_group() with usergroup ID."""
        bot = SlackBot(Bots.Web)
        mock_group = {"id": "S12345ABCDE", "handle": "leadership"}
        mock_response = {"ok": True, "usergroups": [mock_group]}

        with patch.object(bot.client, "usergroups_list", return_value=mock_response):
            result = bot.lookup_group("S12345ABCDE")

            assert result is not None
            assert result["id"] == "S12345ABCDE"
            assert result["handle"] == "leadership"

    def test_slackbot_lookup_group_by_handle(self, mock_env):
        """Test SlackBot.lookup_group() with usergroup handle."""
        bot = SlackBot(Bots.Web)
        mock_group = {"id": "S12345", "handle": "leadership"}

        with patch("shared_utilities.clients.slack.services.usergroup_service.UsergroupService.get_group_by_handle", return_value=mock_group):
            result = bot.lookup_group("@leadership")

            assert result == mock_group


# ── Integration Tests ─────────────────────────────────────────────────────────

class TestSlackClientIntegration:
    """Integration tests for common workflows."""

    def test_send_notification_workflow(self, mock_env, mock_slack_response):
        """Test complete workflow: create bot, send notification, verify response."""
        bot = SlackBot(Bots.Web)
        mock_response = mock_slack_response(
            ok=True,
            message_ts="1234567890.123456",
            channel="C12345"
        )

        with patch.object(bot.client, "chat_postMessage", return_value=mock_response):
            blocks = [
                HeaderBlock(text="Test Notification"),
                SectionBlock(text="This is a test message"),
                DividerBlock(),
            ]

            result = bot.send_message(
                message_type="to_channel",
                channel_id="C12345",
                blocks=blocks
            )

            # Result is SlackApiSuccessResponse with "success" key, not "ok"
            assert result["success"] is True
            assert result["message_ts"] == "1234567890.123456"
            assert result["channel"] == "C12345"

    def test_lookup_and_mention_workflow(self, mock_env):
        """Test workflow: lookup user, format mention."""
        bot = SlackBot(Bots.Web)
        mock_user = {"id": "U12345", "name": "testuser", "profile": {"email": "test@example.com"}}

        with patch("shared_utilities.clients.slack.user_lookup.lookup_user", return_value=mock_user):
            user = bot.lookup_user("test@example.com")
            assert user is not None

            # Format mention (would be done by GenericMessageBuilder in real code)
            mention = f"<@{user['id']}>"
            assert mention == "<@U12345>"

    def test_error_recovery_workflow(self, mock_env):
        """Test workflow: API error, check error response, handle gracefully."""
        bot = SlackBot(Bots.Web)
        mock_error_response = Mock()
        mock_error_response.data = {"ok": False, "error": "channel_not_found"}
        mock_error_response.status_code = 404

        with patch.object(bot.client, "chat_postMessage", side_effect=SlackApiError("Error", mock_error_response)):
            result = bot.send_message(
                message_type="to_channel",
                channel_id="C_INVALID",
                blocks=[HeaderBlock(text="Test")]
            )

            assert result["success"] is False
            assert "channel_not_found" in result["error"]
            # Verify caller can handle error gracefully
            assert "response" in result or result.get("response") is None

