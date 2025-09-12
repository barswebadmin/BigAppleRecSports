"""
Unit tests for configurable Slack channel and mention strategy routing.
Tests the new query parameters: slackChannelName and mentionStrategy.
Focuses on verifying that parameters are correctly passed to the service layer.
"""

import pytest
from unittest.mock import patch
from services.slack.slack_service import SlackService


class TestConfigurableSlackRouting:
    """Test the configurable Slack routing functionality"""

    @pytest.fixture
    def slack_service(self):
        with patch("services.slack.slack_service.settings") as mock_settings:
            mock_settings.slack_channels = {
                "refund-requests": {
                    "channelId": "C08J1EN7SFR",
                    "name": "#registration-refunds",
                },
                "joe-test": {"channelId": "C092RU7R6PL", "name": "#joe-test"},
            }
            mock_settings.slack_subgroups = {
                "kickball": "<!subteam^S08L2521XAM>",
                "bowling": "<!subteam^S08KJJ02738>",
                "pickleball": "<!subteam^S08KTJ33Z9R>",
                "dodgeball": "<!subteam^S08KJJ5CL4W>",
            }
            mock_settings.slack_users = {"joe": "<@U0278M72535>", "here": "@here"}
            mock_settings.environment = "test"
            mock_settings.slack_refunds_bot_token = "test_token"

            return SlackService()

    def test_channel_resolution_logic(self, slack_service):
        """Test channel resolution logic with different parameters"""

        # Test default fallback (None parameter)
        channel_config, mention_strategy = (
            slack_service._resolve_channel_and_mention_strategy(None, None)
        )
        assert channel_config["name"] == "#joe-test"  # test environment default
        assert mention_strategy == "user|joe"  # test environment default

        # Test custom channel (parameter provided and found in config)
        channel_config, mention_strategy = (
            slack_service._resolve_channel_and_mention_strategy("refund-requests", None)
        )
        assert channel_config["name"] == "#registration-refunds"
        assert channel_config["channelId"] == "C08J1EN7SFR"

        # Test invalid channel (parameter provided but not in config - should use hardcoded fallback, NOT env default)
        channel_config, mention_strategy = (
            slack_service._resolve_channel_and_mention_strategy("invalid-channel", None)
        )
        assert channel_config["name"] == "#joe-test"  # hardcoded fallback for test env
        assert (
            channel_config["channelId"] == "C092RU7R6PL"
        )  # hardcoded fallback for test env

        # Test empty string channel (parameter provided as empty - should use hardcoded fallback)
        channel_config, mention_strategy = (
            slack_service._resolve_channel_and_mention_strategy("", None)
        )
        assert channel_config["name"] == "#joe-test"  # hardcoded fallback for test env

    def test_mention_resolution_logic(self, slack_service):
        """Test mention resolution logic with different strategies"""

        # Test user mention strategy
        mention = slack_service._resolve_mention("Big Apple Kickball", "user|joe")
        assert mention == "<@U0278M72535>"

        # Test user|here strategy
        mention = slack_service._resolve_mention("Big Apple Kickball", "user|here")
        assert mention == "@here"

        # Test sport aliases strategy with kickball
        mention = slack_service._resolve_mention("Big Apple Kickball", "sportAliases")
        assert mention == "<!subteam^S08L2521XAM>"

        # Test sport aliases strategy with unknown sport
        mention = slack_service._resolve_mention("Random Product", "sportAliases")
        assert mention == "@here"  # fallback

        # Test empty string strategy (explicit empty from query param)
        mention = slack_service._resolve_mention("Product", "")
        assert mention == "<@U0278M72535>"  # fallback to joe for empty strategy

        # Test invalid user fallback
        mention = slack_service._resolve_mention("Product", "user|unknown")
        assert mention == "<@U0278M72535>"  # fallback to joe

        # Test invalid strategy fallback
        mention = slack_service._resolve_mention("Product", "invalid_strategy")
        assert mention == "<@U0278M72535>"  # fallback to joe

    def test_using_custom_config_detection(self, slack_service):
        """Test the logic that determines when to use custom configuration"""

        # Test the custom config detection logic directly

        # None parameters should NOT trigger custom config
        using_custom = (None is not None and None.strip() if None else False) or (
            None is not None and None.strip() if None else False
        )
        assert using_custom is False

        # Empty string parameters should NOT trigger custom config
        using_custom = ("" != None and "".strip()) or ("" != None and "".strip())
        assert not using_custom  # Empty string is falsy

        # Whitespace parameters should NOT trigger custom config
        using_custom = (" " != None and " ".strip()) or ("  " != None and "  ".strip())
        assert not using_custom  # Whitespace strips to empty string (falsy)

        # Valid parameters SHOULD trigger custom config
        using_custom = ("joe-test" != None and "joe-test".strip()) or (
            "user|joe" != None and "user|joe".strip()
        )
        assert using_custom  # Non-empty strings are truthy

        # Test actual resolution when custom config is detected
        channel_config, strategy = slack_service._resolve_channel_and_mention_strategy(
            "joe-test", "user|joe"
        )
        assert channel_config["name"] == "#joe-test"
        assert strategy == "user|joe"

    def test_environment_based_defaults(self, slack_service):
        """Test that environment-based defaults work correctly"""

        # Test environment defaults (test env)
        channel_config, strategy = slack_service._resolve_channel_and_mention_strategy(
            None, None
        )
        assert channel_config["name"] == "#joe-test"  # test env default channel
        assert strategy == "user|joe"  # test env default mention

        # Test production environment defaults
        with patch("services.slack.slack_service.settings") as mock_settings:
            mock_settings.environment = "production"
            mock_settings.slack_channels = slack_service.settings.slack_channels
            mock_settings.slack_users = slack_service.settings.slack_users

            # Create new service with production settings
            prod_service = SlackService()
            channel_config, strategy = (
                prod_service._resolve_channel_and_mention_strategy(None, None)
            )
            assert strategy == "sportAliases"  # production default mention

    def test_all_supported_mention_formats(self, slack_service):
        """Test all supported mention formats work correctly"""

        test_cases = [
            ("user|joe", "Big Apple Kickball", "<@U0278M72535>"),
            ("user|here", "Big Apple Bowling", "@here"),
            ("sportAliases", "Big Apple Kickball", "<!subteam^S08L2521XAM>"),
            ("sportAliases", "Big Apple Bowling", "<!subteam^S08KJJ02738>"),
            ("sportAliases", "Big Apple Pickleball", "<!subteam^S08KTJ33Z9R>"),
            ("sportAliases", "Big Apple Dodgeball", "<!subteam^S08KJJ5CL4W>"),
            ("sportAliases", "Unknown Product", "@here"),  # fallback
            ("invalid", "Any Product", "<@U0278M72535>"),  # fallback to joe
        ]

        for strategy, product_title, expected_mention in test_cases:
            result = slack_service._resolve_mention(product_title, strategy)
            assert (
                result == expected_mention
            ), f"Failed for strategy '{strategy}' with product '{product_title}'"

    def test_query_param_priority_over_environment(self, slack_service):
        """Test that query parameters take priority over environment defaults"""

        # Test that when a channel param is provided, it doesn't fall back to environment
        # Even if the channel is not found in config, it should use hardcoded fallback, not env default

        # Case 1: Valid channel param overrides environment
        channel_config, strategy = slack_service._resolve_channel_and_mention_strategy(
            "refund-requests", "sportAliases"
        )
        assert (
            channel_config["name"] == "#registration-refunds"
        )  # Uses the param, not test env default
        assert strategy == "sportAliases"  # Uses the param, not test env default

        # Case 2: Invalid channel param still doesn't fall back to environment default
        channel_config, strategy = slack_service._resolve_channel_and_mention_strategy(
            "nonexistent", "user|here"
        )
        assert (
            channel_config["name"] == "#joe-test"
        )  # Uses hardcoded fallback for test env
        assert strategy == "user|here"  # Uses the param, not test env default

        # Case 3: Empty string params should be honored as explicit choices
        channel_config, strategy = slack_service._resolve_channel_and_mention_strategy(
            "", ""
        )
        assert (
            channel_config["name"] == "#joe-test"
        )  # Hardcoded fallback (not env default)
        assert strategy == ""  # Explicit empty string, not test env default

        # Case 4: None params should use environment defaults
        channel_config, strategy = slack_service._resolve_channel_and_mention_strategy(
            None, None
        )
        assert channel_config["name"] == "#joe-test"  # Test environment default
        assert strategy == "user|joe"  # Test environment default

    def test_mention_strategy_priority(self, slack_service):
        """Test that mention strategy parameters take priority"""

        # When mention strategy is provided, use it regardless of environment
        mention = slack_service._resolve_mention("Big Apple Kickball", "user|joe")
        assert mention == "<@U0278M72535>"  # Uses param, not sport alias for kickball

        # When mention strategy is empty string, treat as explicit choice
        mention = slack_service._resolve_mention("Big Apple Kickball", "")
        assert mention == "<@U0278M72535>"  # Explicit empty strategy fallback

        # Only when mention strategy is None should we use environment defaults
        # (This would be tested in the resolution method where None triggers environment logic)
