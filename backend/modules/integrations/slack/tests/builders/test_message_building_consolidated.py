"""
Consolidated tests for Slack message building and formatting.
Combines functionality from test_slack_message_formatting.py and test_updated_message_format.py.
"""

import pytest
from unittest.mock import Mock, patch
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

    def test_sport_group_mention_extraction(self):
        """Test that sport group mentions are correctly extracted from product titles."""
        # Test pickleball mention
        pickleball_mention = self.message_builder.get_sport_group_mention(
            "Test Product - Pickleball Monday"
        )
        assert pickleball_mention == "<!subteam^S12345|@pickleball-leads>"

        # Test soccer mention
        soccer_mention = self.message_builder.get_sport_group_mention(
            "Soccer League Registration"
        )
        assert soccer_mention == "<!subteam^S67890|@soccer-leads>"

        # Test kickball mention
        kickball_mention = self.message_builder.get_sport_group_mention(
            "Kickball Tournament Entry"
        )
        assert kickball_mention == "<!subteam^S11111|@kickball-leads>"

    def test_order_url_generation(self):
        """Test that order URLs are correctly generated."""
        order_url = self.message_builder.get_order_url("5875167625310", "#42234")
        expected_url = "<https://admin.shopify.com/store/09fe59-3/orders/5875167625310|#42234>"
        assert order_url == expected_url

    def test_product_url_generation(self):
        """Test that product URLs are correctly generated."""
        product_url = self.message_builder.get_product_url("7350462185566")
        expected_url = "https://admin.shopify.com/store/09fe59-3/products/7350462185566"
        assert product_url == expected_url

    def test_refund_decision_message_creation(self):
        """Test creation of refund decision messages with proper formatting."""
        requestor_name = {"first": "John", "last": "Doe"}
        requestor_email = "john.doe@example.com"
        refund_type = "refund"
        sport_mention = self.message_builder.get_sport_group_mention(
            "Test Product - Pickleball Monday"
        )
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
        assert "text" in message_data
        assert "action_buttons" in message_data
        assert "metadata" in message_data

        # Verify message content
        message_text = message_data["text"]
        assert "John Doe" in message_text
        assert "john.doe@example.com" in message_text
        assert "#42234" in message_text
        assert "$95.00" in message_text
        assert "Pickleball Monday" in message_text

        # Verify action buttons
        action_buttons = message_data["action_buttons"]
        assert len(action_buttons) > 0
        button_action_ids = [btn.get("action_id") for btn in action_buttons]
        assert "process_refund" in button_action_ids
        assert "custom_refund" in button_action_ids
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

        message_text = message_data["text"]
        
        # Verify key information is present
        assert "Request Type" in message_text
        assert "Requested by" in message_text
        assert "Order Number" in message_text
        assert "Product Title" in message_text
        assert "Total Paid" in message_text
        assert "Estimated Refund Due" in message_text

    def test_updated_message_format_after_processing(self):
        """Test the updated message format after refund processing."""
        # Sample current message text
        sample_current_message = """*Request Type*: 💵 Refund back to original form of payment

📧 *Requested by:* joe test1 (<mailto:jdazz87@gmail.com|jdazz87@gmail.com>)

*Request Submitted At*: 09/10/25 at 4:12 AM

*Order Number*: <https://admin.shopify.com/store/09fe59-3/orders/5876418969694|#42305>

*Order Created At:* 09/10/25 at 3:27 AM

*Product Title:* <https://admin.shopify.com/store/09fe59-3/products/7350462185566|joe test product>

*Season Start Date*: 10/8/25

*Total Paid:* $2.00

*Estimated Refund Due:* $1.90"""

        # Test building comprehensive no refund message
        no_refund_message = self.slack_refunds_utils.build_comprehensive_no_refund_message(
            order_data=self.mock_order_data,
            raw_order_number="#42305",
            order_cancelled=True,
            requestor_name={"first": "joe", "last": "test1"},
            requestor_email="jdazz87@gmail.com",
            processor_user="staff_user",
            thread_ts="1234567890.123456",
            current_message_full_text=sample_current_message,
        )

        # Verify message structure
        assert "text" in no_refund_message
        assert "action_buttons" in no_refund_message

        # Verify message content
        message_text = no_refund_message["text"]
        assert "No Refund Approved" in message_text
        assert "#42305" in message_text
        assert "joe test1" in message_text
        assert "jdazz87@gmail.com" in message_text
        assert "staff_user" in message_text

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

        action_buttons = message_data["action_buttons"]
        
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
        assert "custom_refund" in button_action_ids
        assert "no_refund" in button_action_ids

        # Verify button values contain expected data
        for button in action_buttons:
            button_value = button.get("value", "")
            assert "rawOrderNumber" in button_value
            assert "orderId" in button_value
            assert "refundAmount" in button_value

    def test_metadata_generation(self):
        """Test that metadata is correctly generated for messages."""
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

        metadata = message_data.get("metadata", {})
        
        # Verify metadata structure
        assert "event_type" in metadata
        assert "event_payload" in metadata
        
        event_payload = metadata["event_payload"]
        assert "order_number" in event_payload
        assert "requestor_email" in event_payload
        assert "refund_type" in event_payload
        assert "sheet_link" in event_payload


if __name__ == "__main__":
    pytest.main([__file__])
