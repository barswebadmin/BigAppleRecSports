"""
Backward compatibility tests to ensure existing behavior is unchanged.
Verifies that the configurable routing changes don't break existing functionality.
"""

import pytest
from unittest.mock import patch
from services.slack.slack_service import SlackService


class TestBackwardCompatibility:
    """Test that existing behavior remains unchanged after configurable routing implementation"""

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
            mock_settings.environment = "production"  # Test production behavior
            mock_settings.slack_refunds_bot_token = "test_token"

            return SlackService()

    def test_default_behavior_unchanged(self, slack_service):
        """Test that default behavior works exactly as before when no parameters are provided"""

        # Test that None parameters result in production defaults
        channel_config, mention_strategy = (
            slack_service._resolve_channel_and_mention_strategy(None, None)
        )

        # Should use production defaults
        assert channel_config["name"] == "#registration-refunds"  # production default
        assert channel_config["channelId"] == "C08J1EN7SFR"
        assert mention_strategy == "sportAliases"  # production default

    def test_sport_group_mentions_unchanged(self, slack_service):
        """Test that sport group mentions work exactly as before"""

        # Test that sportAliases strategy works as before
        test_cases = [
            ("Big Apple Kickball - Monday", "<!subteam^S08L2521XAM>"),
            ("Big Apple Bowling - Tuesday", "<!subteam^S08KJJ02738>"),
            ("Big Apple Pickleball - Wednesday", "<!subteam^S08KTJ33Z9R>"),
            ("Big Apple Dodgeball - Thursday", "<!subteam^S08KJJ5CL4W>"),
            ("Random Unknown Product", "@here"),  # fallback behavior
        ]

        for product_title, expected_mention in test_cases:
            result = slack_service._resolve_mention(product_title, "sportAliases")
            assert result == expected_mention, f"Failed for product '{product_title}'"

    def test_backward_compatible_channel_resolution(self, slack_service):
        """Test that channel resolution maintains backward compatibility"""

        # Test that default production channel is used when no override
        channel_config, _ = slack_service._resolve_channel_and_mention_strategy(
            None, None
        )

        # Should match original hardcoded production values
        assert channel_config["channelId"] == "C08J1EN7SFR"
        assert channel_config["name"] == "#registration-refunds"

        # Test that invalid channels fall back to default
        channel_config, _ = slack_service._resolve_channel_and_mention_strategy(
            "nonexistent", None
        )
        assert (
            channel_config["channelId"] == "C08J1EN7SFR"
        )  # fallback to production default

    def test_method_signatures_extended_not_changed(self, slack_service):
        """Test that method signatures are extended, not changed"""

        # Verify that the resolve methods exist and accept the expected parameters
        assert hasattr(slack_service, "_resolve_channel_and_mention_strategy")
        assert hasattr(slack_service, "_resolve_mention")

        # Test that the methods work with both None and actual values
        try:
            channel_config, strategy = (
                slack_service._resolve_channel_and_mention_strategy(None, None)
            )
            assert channel_config is not None
            assert strategy is not None

            mention = slack_service._resolve_mention("Test Product", "sportAliases")
            assert mention is not None

        except Exception as e:
            pytest.fail(f"Method signature compatibility failed: {e}")

    def test_original_environment_logic_preserved(self, slack_service):
        """Test that original environment-based logic is preserved"""

        # Test production environment behavior (current fixture)
        assert slack_service.settings.environment == "production"

        channel_config, strategy = slack_service._resolve_channel_and_mention_strategy(
            None, None
        )
        assert channel_config["name"] == "#registration-refunds"  # production channel
        assert strategy == "sportAliases"  # production mention strategy

        # Test that the sport groups are still available for sportAliases
        kickball_mention = slack_service._resolve_mention(
            "Big Apple Kickball", "sportAliases"
        )
        assert kickball_mention == "<!subteam^S08L2521XAM>"  # original production value
