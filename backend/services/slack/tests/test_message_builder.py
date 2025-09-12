"""
Unit tests for SlackMessageBuilder.
"""

import pytest
from services.slack.message_builder import SlackMessageBuilder


class TestSlackMessageBuilder:
    """Test SlackMessageBuilder functionality."""

    @pytest.fixture
    def sport_groups(self):
        return {
            "kickball": "<!subteam^S08L2521XAM>",
            "bowling": "<!subteam^S08KJJ02738>",
            "pickleball": "<!subteam^S08KTJ33Z9R>",
            "dodgeball": "<!subteam^S08KJJ5CL4W>",
        }

    @pytest.fixture
    def message_builder(self, sport_groups):
        return SlackMessageBuilder(sport_groups)

    def test_get_sport_group_mention_kickball(self, message_builder):
        """Test kickball sport group mention."""
        # TODO: Method now always returns joe's user ID regardless of sport
        result = message_builder.get_sport_group_mention("Kickball League Registration")
        assert result == "<@U0278M72535>"

    def test_get_sport_group_mention_bowling(self, message_builder):
        """Test bowling sport group mention."""
        # TODO: Method now always returns joe's user ID regardless of sport
        result = message_builder.get_sport_group_mention("Bowling Tournament")
        assert result == "<@U0278M72535>"

    def test_get_sport_group_mention_fallback(self, message_builder):
        """Test fallback when no sport is found."""
        # TODO: Method now always returns joe's user ID, no more @here fallback
        result = message_builder.get_sport_group_mention("Random Product")
        assert result == "<@U0278M72535>"

    # TODO: Test for original @here fallback behavior - currently disabled
    # When get_sport_group_mention() is restored to use sport_groups logic,
    # uncomment this test to verify @here fallback works for unknown sports
    def test_get_sport_group_mention_at_here_fallback_original_behavior(
        self, message_builder
    ):
        """Test that @here fallback works when no sport is found in product title."""
        # TODO: This test is commented out because get_sport_group_mention()
        # currently always returns joe's user ID. Uncomment when original logic is restored.
        pass
        # result = message_builder.get_sport_group_mention("Random Unknown Product")
        # assert result == "@here"

    def test_get_order_url(self, message_builder):
        """Test order URL formatting."""
        result = message_builder.get_order_url("gid://shopify/Order/12345", "#12345")
        expected = "<https://admin.shopify.com/store/09fe59-3/orders/12345|#12345>"
        assert result == expected

    def test_get_order_url_without_hash(self, message_builder):
        """Test order URL formatting without hash prefix."""
        result = message_builder.get_order_url("12345", "12345")
        expected = "<https://admin.shopify.com/store/09fe59-3/orders/12345|#12345>"
        assert result == expected

    def test_get_product_url(self, message_builder):
        """Test product URL formatting."""
        result = message_builder.get_product_url("gid://shopify/Product/12345")
        expected = "https://admin.shopify.com/store/09fe59-3/products/12345"
        assert result == expected

    def test_get_sheet_link_line_with_link(self, message_builder):
        """Test sheet link formatting with valid link."""
        link = "https://docs.google.com/spreadsheets/d/test/edit"
        result = message_builder._get_sheet_link_line(link)
        expected = "\n \n 🔗 *<https://docs.google.com/spreadsheets/d/test/edit|View Request in Google Sheets>*\n\n"
        assert result == expected

    def test_get_sheet_link_line_empty(self, message_builder):
        """Test sheet link formatting with empty link."""
        result = message_builder._get_sheet_link_line("")
        assert result == ""

    def test_get_requestor_line_full_name(self, message_builder):
        """Test requestor line with full name."""
        requestor_name = {"first": "John", "last": "Doe"}
        result = message_builder._get_requestor_line(requestor_name, "john@example.com")
        expected = "📧 *Requested by:* John Doe (john@example.com)\n\n"
        assert result == expected

    def test_get_requestor_line_email_only(self, message_builder):
        """Test requestor line with email only."""
        requestor_name = {"first": "", "last": ""}
        result = message_builder._get_requestor_line(requestor_name, "john@example.com")
        expected = "📧 *Requested by:* john@example.com\n\n"
        assert result == expected

    def test_get_request_type_text_refund(self, message_builder):
        """Test request type formatting for refund."""
        result = message_builder._get_request_type_text("refund")
        assert result == "💵 Refund back to original form of payment"

    def test_get_request_type_text_credit(self, message_builder):
        """Test request type formatting for credit."""
        result = message_builder._get_request_type_text("credit")
        assert result == "🎟️ Store Credit to use toward a future order"

    def test_get_request_type_text_unknown(self, message_builder):
        """Test request type formatting for unknown type."""
        result = message_builder._get_request_type_text("unknown")
        assert result == "❓ Unknown"
