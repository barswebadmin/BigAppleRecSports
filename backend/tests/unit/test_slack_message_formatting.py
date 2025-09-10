"""
Test suite for Slack message formatting, including status positioning and user tagging.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from services.slack.message_builder import SlackMessageBuilder


class TestSlackMessageFormatting:
    """Test Slack message formatting features."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock sport groups for Slack mentions
        mock_sport_groups = {
            "pickleball": "<!subteam^S12345|@pickleball-leads>",
            "soccer": "<!subteam^S67890|@soccer-leads>", 
            "kickball": "<!subteam^S11111|@kickball-leads>"
        }
        self.message_builder = SlackMessageBuilder(sport_groups=mock_sport_groups)
        
        # Mock order data
        self.mock_order_data = {
            "order": {
                "orderId": "gid://shopify/Order/5875167625310",
                "id": "5875167625310",
                "name": "#42234",
                "totalAmountPaid": 100.00,
                "line_items": [{
                    "title": "Test Product - Pickleball Monday",
                    "product": {
                        "title": "Test Product - Pickleball Monday",
                        "id": "gid://shopify/Product/7350462185566"
                    }
                }]
            },
            "refund_calculation": {
                "success": True,
                "refund_amount": 95.00,
                "season_start_date": "10/15/24",
                "message": "*Estimated Refund Due:* $95.00\n (This request is calculated...)"
            },
            "original_data": {
                "original_timestamp": "09/10/25 at 3:21 AM",
                "season_start_date": "10/15/24",
                "order_created_at": "09/09/25 at 1:16 AM",
                "product_display": "<https://admin.shopify.com/store/09fe59-3/products/7350462185566|Test Product>",
                "order_number_display": "<https://admin.shopify.com/store/09fe59-3/orders/5875167625310|#42234>",
                "product_field_name": "Sport/Season/Day"
            }
        }
        
        # Mock requestor info
        self.mock_requestor_name = {"first": "John", "last": "Doe"}
        self.mock_requestor_email = "john.doe@example.com"

    def test_status_footer_position_order_canceled(self):
        """Test that 'Order Canceled' status appears at the bottom of the message."""
        
        result = self.message_builder.create_refund_decision_message(
            order_data=self.mock_order_data,
            requestor_name=self.mock_requestor_name,
            requestor_email=self.mock_requestor_email,
            refund_type="refund",
            sport_mention="@here",
            sheet_link="https://docs.google.com/spreadsheets/test",
            order_cancelled=True,
            slack_user_id="U0278M72535",
            original_timestamp="09/10/25 at 3:21 AM"
        )
        
        message_text = result["text"]
        
        # Verify the status appears at the end
        assert message_text.endswith("🚀 *Order Canceled*, processed by <@U0278M72535>")
        
        # Verify the status does NOT appear at the beginning
        assert not message_text.startswith("🚀 *Order Canceled*")
        
        # Verify proper user tagging format
        assert "<@U0278M72535>" in message_text
        assert "processed by U0278M72535" not in message_text  # Should not be raw ID

    def test_status_footer_position_order_not_canceled(self):
        """Test that 'Order Not Canceled' status appears at the bottom of the message."""
        
        result = self.message_builder.create_refund_decision_message(
            order_data=self.mock_order_data,
            requestor_name=self.mock_requestor_name,
            requestor_email=self.mock_requestor_email,
            refund_type="refund",
            sport_mention="@here",
            sheet_link="https://docs.google.com/spreadsheets/test",
            order_cancelled=False,
            slack_user_id="U0278M72535",
            original_timestamp="09/10/25 at 3:21 AM"
        )
        
        message_text = result["text"]
        
        # Verify the status appears at the end
        assert message_text.endswith("ℹ️ *Order Not Canceled*, processed by <@U0278M72535>")
        
        # Verify the status does NOT appear at the beginning
        assert not message_text.startswith("ℹ️ *Order Not Canceled*")
        
        # Verify proper user tagging format
        assert "<@U0278M72535>" in message_text
        assert "processed by U0278M72535" not in message_text  # Should not be raw ID
    def test_user_channel_id_vs_member_id(self):
        """Test that we're using member ID correctly for user mentions."""
        
        # According to the user:
        # - Channel ID: "D026TPC6S3H"  
        # - Member ID: "U0278M72535"
        # We should use Member ID for user mentions
        
        member_id = "U0278M72535"
        
        # Test with member ID (correct)
        result_member = self.message_builder.create_refund_decision_message(
            order_data=self.mock_order_data,
            requestor_name=self.mock_requestor_name,
            requestor_email=self.mock_requestor_email,
            refund_type="refund",
            sport_mention="@here",
            sheet_link="",
            order_cancelled=True,
            slack_user_id=member_id
        )
        
        message_text = result_member["text"]
        
        # Should contain properly formatted mention
        assert f"<@{member_id}>" in message_text
        # Should NOT contain raw user ID in the processed by text
        assert f"processed by {member_id}" not in message_text
        # Should be at the bottom
        assert message_text.endswith(f"🚀 *Order Canceled*, processed by <@{member_id}>")

    def test_slack_text_property_in_response(self):
        """Test that the slack_text property is correctly set in the response."""
        
        # Test canceled order
        result_canceled = self.message_builder.create_refund_decision_message(
            order_data=self.mock_order_data,
            requestor_name=self.mock_requestor_name,
            requestor_email=self.mock_requestor_email,
            refund_type="refund",
            sport_mention="@here",
            sheet_link="",
            order_cancelled=True,
            slack_user_id="U0278M72535"
        )
        
        assert result_canceled["slack_text"] == "Order Canceled"
        
        # Test not canceled order
        result_not_canceled = self.message_builder.create_refund_decision_message(
            order_data=self.mock_order_data,
            requestor_name=self.mock_requestor_name,
            requestor_email=self.mock_requestor_email,
            refund_type="refund",
            sport_mention="@here",
            sheet_link="",
            order_cancelled=False,
            slack_user_id="U0278M72535"
        )
        
        assert result_not_canceled["slack_text"] == "Order Not Canceled"
