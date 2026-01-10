"""
Consolidated tests for Slack message building and formatting.
Combines functionality from test_slack_message_formatting.py and test_updated_message_format.py.
"""

import pytest
from unittest.mock import Mock
from modules.integrations.slack.builders.message_builder import SlackMessageBuilder
from modules.integrations.slack.slack_refunds_utils import SlackRefundsUtils


class TestMessageBuildingConsolidated:
    """Consolidated test suite for Slack message building and formatting."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock sport groups for Slack mentions
        self.mock_sport_groups = {
            "pickleball": "<!subteam^S12345|@pickleball-leads>",
            "soccer": "<!subteam^S67890|@soccer-leads>",
            "kickball": "<!subteam^S11111|@kickball-leads>",
            "dodgeball": "<!subteam^S08KJJ5CL4W>",
        }
        self.message_builder = SlackMessageBuilder(sport_groups=self.mock_sport_groups)

        # Mock order data
        self.mock_order_data = {
            "order": {
                "orderId": "gid://shopify/Order/5875167625310",
                "id": "5875167625310",
                "name": "#42234",
                "totalAmountPaid": 100.00,
                "line_items": [
                    {
                        "title": "Test Product - Pickleball Monday",
                        "product": {
                            "title": "Test Product - Pickleball Monday",
                            "id": "gid://shopify/Product/7350462185566",
                        },
                    }
                ],
            },
            "refund_calculation": {
                "success": True,
                "refund_amount": 95.00,
                "season_start_date": "10/15/24",
                "message": "*Estimated Refund Due:* $95.00\n (This request is calculated...)",
            },
            "original_data": {
                "original_timestamp": "09/10/25 at 3:21 AM",
                "season_start_date": "10/15/24",
                "order_created_at": "09/09/25 at 1:16 AM",
                "product_display": "<https://admin.shopify.com/store/09fe59-3/products/7350462185566|Test Product>",
                "order_number_display": "<https://admin.shopify.com/store/09fe59-3/orders/5875167625310|#42234>",
                "product_field_name": "Product Title",
            },
        }

        # Mock refunds utils
        self.mock_orders_service = Mock()
        self.mock_settings = Mock()
        self.slack_refunds_utils = SlackRefundsUtils(
            self.mock_orders_service, self.mock_settings
        )
        self.slack_refunds_utils.message_builder = self.message_builder

    def test_refund_decision_message_creation(self):
        """Test creation of refund decision messages with proper formatting."""
        requestor_name = {"first": "John", "last": "Doe"}
        requestor_email = "john.doe@example.com"
        refund_type = "refund"
        sport_mention = "<!subteam^S12345|@pickleball-leads>"
        sheet_link = "https://docs.google.com/spreadsheets/d/test"
        order_cancelled = True
        slack_user_id = "U1234567890"
        original_timestamp = "09/10/25 at 3:21 AM"

        message_data = self.message_builder.create_refund_decision_message(
            order_data=self.mock_order_data,
            requestor_name=requestor_name,
            requestor_email=requestor_email,
            refund_type=refund_type,
            sport_mention=sport_mention,
            sheet_link=sheet_link,
            order_cancelled=order_cancelled,
            slack_user_id=slack_user_id,
            original_timestamp=original_timestamp,
        )

        # Verify message structure
        assert "blocks" in message_data
        blocks = message_data["blocks"]
        assert len(blocks) > 0

        # First block should be a section with the message content
        section_block = blocks[0]
        assert section_block["type"] == "section"
        message_text = section_block["text"]["text"]

        # Verify message content
        assert "John Doe" in message_text
        assert "john.doe@example.com" in message_text
        assert "#42234" in message_text
        assert "$95.00" in message_text
        assert "Test Product" in message_text

        # Last block should be actions with buttons
        actions_block = blocks[-1]
        assert actions_block["type"] == "actions"
        action_buttons = actions_block["elements"]
        assert len(action_buttons) > 0
        button_action_ids = [btn.get("action_id") for btn in action_buttons]
        assert "process_refund" in button_action_ids
        assert "custom_refund_amount" in button_action_ids
        assert "no_refund" in button_action_ids

    def test_message_formatting_with_status_positioning(self):
        """Test that messages are formatted with proper status positioning."""
        # Test message with status at top
        message_data = self.message_builder.create_refund_decision_message(
            order_data=self.mock_order_data,
            requestor_name={"first": "John", "last": "Doe"},
            requestor_email="john.doe@example.com",
            refund_type="refund",
            sport_mention="<!subteam^S12345|@pickleball-leads>",
            sheet_link="https://docs.google.com/spreadsheets/d/test",
            order_cancelled=True,
            slack_user_id="U1234567890",
            original_timestamp="09/10/25 at 3:21 AM",
        )

        blocks = message_data["blocks"]
        message_text = blocks[0]["text"]["text"]
        
        # Verify key information is present
        assert "Request Type" in message_text
        assert "Requested by" in message_text
        assert "Order Number" in message_text
        assert "Product Title" in message_text
        assert "Total Paid" in message_text
        assert "Estimated Refund Due" in message_text

    def test_action_button_generation(self):
        """Test that action buttons are correctly generated with proper values."""
        requestor_name = {"first": "John", "last": "Doe"}
        requestor_email = "john.doe@example.com"
        refund_type = "refund"
        sport_mention = "<!subteam^S12345|@pickleball-leads>"
        sheet_link = "https://docs.google.com/spreadsheets/d/test"
        order_cancelled = True
        slack_user_id = "U1234567890"
        original_timestamp = "09/10/25 at 3:21 AM"

        message_data = self.message_builder.create_refund_decision_message(
            order_data=self.mock_order_data,
            requestor_name=requestor_name,
            requestor_email=requestor_email,
            refund_type=refund_type,
            sport_mention=sport_mention,
            sheet_link=sheet_link,
            order_cancelled=order_cancelled,
            slack_user_id=slack_user_id,
            original_timestamp=original_timestamp,
        )

        blocks = message_data["blocks"]
        actions_block = blocks[-1]
        assert actions_block["type"] == "actions"
        action_buttons = actions_block["elements"]
        
        # Verify button structure
        for button in action_buttons:
            assert "type" in button
            assert "text" in button
            assert "action_id" in button
            assert "value" in button
            assert button["type"] == "button"

        # Verify specific buttons exist
        button_action_ids = [btn.get("action_id") for btn in action_buttons]
        assert "process_refund" in button_action_ids
        assert "custom_refund_amount" in button_action_ids
        assert "no_refund" in button_action_ids

        # Verify button values contain expected data
        process_button = next((b for b in action_buttons if b["action_id"] == "process_refund"), None)
        assert process_button is not None
        assert "refundAmount" in process_button["value"]
        assert "orderId" in process_button["value"]



if __name__ == "__main__":
    pytest.main([__file__])
