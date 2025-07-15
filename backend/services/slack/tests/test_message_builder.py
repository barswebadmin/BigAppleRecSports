"""
Unit tests for SlackMessageBuilder.
"""

import pytest
from ..message_builder import SlackMessageBuilder


class TestSlackMessageBuilder:
    """Test SlackMessageBuilder functionality."""
    
    @pytest.fixture
    def sport_groups(self):
        return {
            "kickball": "<!subteam^S08L2521XAM>",
            "bowling": "<!subteam^S08KJJ02738>", 
            "pickleball": "<!subteam^S08KTJ33Z9R>",
            "dodgeball": "<!subteam^S08KJJ5CL4W>"
        }
    
    @pytest.fixture
    def message_builder(self, sport_groups):
        return SlackMessageBuilder(sport_groups)
    
    def test_get_sport_group_mention_kickball(self, message_builder):
        """Test kickball sport group mention."""
        result = message_builder.get_sport_group_mention("Kickball League Registration")
        assert result == "<!subteam^S08L2521XAM>"
    
    def test_get_sport_group_mention_bowling(self, message_builder):
        """Test bowling sport group mention."""
        result = message_builder.get_sport_group_mention("Bowling Tournament")
        assert result == "<!subteam^S08KJJ02738>"
    
    def test_get_sport_group_mention_fallback(self, message_builder):
        """Test fallback when no sport is found."""
        result = message_builder.get_sport_group_mention("Random Product")
        assert result == "@here"
    
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
    
    def test_format_sheet_link(self, message_builder):
        """Test sheet link formatting."""
        link = "https://docs.google.com/spreadsheets/d/test/edit"
        result = message_builder.format_sheet_link(link)
        expected = "<https://docs.google.com/spreadsheets/d/test/edit|📊 View Request in Sheets>"
        assert result == expected
    
    def test_format_sheet_link_empty(self, message_builder):
        """Test sheet link formatting with empty link."""
        result = message_builder.format_sheet_link("")
        assert result == "No sheet link provided"
    
    def test_format_requestor_line_full_name(self, message_builder):
        """Test requestor line with full name."""
        requestor_name = {"first": "John", "last": "Doe"}
        result = message_builder.format_requestor_line(requestor_name, "john@example.com")
        expected = "*Requestor:* John Doe (john@example.com)"
        assert result == expected
    
    def test_format_requestor_line_email_only(self, message_builder):
        """Test requestor line with email only."""
        requestor_name = {"first": "", "last": ""}
        result = message_builder.format_requestor_line(requestor_name, "john@example.com")
        expected = "*Requestor:* john@example.com"
        assert result == expected
    
    def test_format_request_type_refund(self, message_builder):
        """Test request type formatting for refund."""
        result = message_builder.format_request_type("refund")
        assert result == "💵 Refund back to original form of payment"
    
    def test_format_request_type_credit(self, message_builder):
        """Test request type formatting for credit."""
        result = message_builder.format_request_type("credit")
        assert result == "🎟️ Store Credit to use toward a future order"
    
    def test_format_request_type_unknown(self, message_builder):
        """Test request type formatting for unknown type."""
        result = message_builder.format_request_type("unknown")
        assert result == "❓ Unknown" 