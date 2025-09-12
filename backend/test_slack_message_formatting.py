"""
Test Slack message formatting to ensure behavior-driven development consistency
Based on actual Slack messages sent by the system to validate formatting and content
"""

try:
    import pytest
except ImportError:
    print("❌ pytest not found. Please install it with: python3 -m pip install pytest")
    print("   Or run: python3 run_slack_tests.py (which will auto-install pytest)")
    exit(1)

from unittest.mock import Mock, patch
from datetime import datetime
from services.slack import SlackService


class TestSlackMessageFormatting:
    """Test suite to validate Slack message formatting matches expected behavior"""

    @pytest.fixture
    def slack_service(self):
        """Create a SlackService instance for testing"""
        return SlackService()

    @pytest.fixture
    def mock_datetime(self):
        """Mock datetime for consistent testing"""
        # Mock datetime to return a specific date/time for testing
        mock_dt = Mock()
        mock_dt.now.return_value = datetime(
            2025, 7, 14, 23, 12, 0
        )  # 07/14/25 at 11:12 PM
        return mock_dt

    def test_fallback_season_info_message_format(self, slack_service):
        """Test fallback message when season info cannot be parsed"""
        # Arrange - data matching the first actual message
        order_data = {
            "order": {
                "id": "gid://shopify/Order/12345",  # Fixed: added 'id' field
                "orderId": "gid://shopify/Order/12345",
                "orderName": "#40192",
                "orderCreatedAt": "2025-06-25T08:39:00Z",
                "totalAmountPaid": 2.00,
                "product": {
                    "title": "joe test product",
                    "productId": "gid://shopify/Product/67890",
                },
            }
        }

        requestor_info = {
            "name": {"first": "joe", "last": "test"},
            "email": "jdazz87@gmail.com",
            "refund_type": "refund",
            "notes": "",
        }

        # Mock the Slack API call to capture the message
        with patch.object(slack_service.api_client, "send_message") as mock_send:
            mock_send.return_value = {"success": True, "ts": "1234567890.123"}

            # Act
            result = slack_service.send_refund_request_notification(
                order_data=order_data,
                refund_calculation={
                    "success": False,
                    "message": "Could not parse season dates",
                },
                requestor_info=requestor_info,
                sheet_link="https://docs.google.com/spreadsheets/test",
            )

            # Assert
            assert result["success"] is True
            mock_send.assert_called_once()

            # Verify the message structure
            call_args = mock_send.call_args
            message_text = call_args[1]["message_text"]

            # Validate key components of the fallback message
            assert "📌 *New Refund Request!*" in message_text
            assert "⚠️ *Order Found in Shopify but Missing Season Info" in message_text
            assert (
                "*Request Type*: 💵 Refund back to original form of payment"
                in message_text
            )
            assert "*Requested by:* joe test (jdazz87@gmail.com)" in message_text
            assert (
                "*Product Title*: <https://admin.shopify.com/store/09fe59-3/products/67890|joe test product>"
                in message_text
            )
            assert "*Total Paid:* $2.00" in message_text
            assert (
                "⚠️ *Could not parse 'Season Dates' from this order's description"
                in message_text
            )
            assert (
                "Please verify the product and either contact the requestor or process anyway"
                in message_text
            )
            assert "*Attn*: <@U0278M72535>" in message_text
            assert (
                "🔗 *<https://docs.google.com/spreadsheets/test|View Request in Google Sheets>*"
                in message_text
            )

    def test_email_mismatch_error_message_format(self, slack_service):
        """Test error message when email doesn't match order customer"""
        # Arrange - data matching the second actual message
        order_data = {
            "order": {
                "id": "gid://shopify/Order/54321",  # Fixed: was 'orderId'
                "orderId": "gid://shopify/Order/54321",
                "orderName": "#39611",
                "product": {
                    "title": "Big Apple Dodgeball - Wednesday - WTNB+ Division - Summer 2025",
                    "productId": "gid://shopify/Product/98765",
                },
            }
        }

        requestor_info = {
            "name": {"first": "joe", "last": "test"},
            "email": "jdazz87@gmail.com",
            "refund_type": "credit",
            "notes": "",
        }

        # Mock the Slack API call to capture the message
        with patch.object(slack_service.api_client, "send_message") as mock_send:
            mock_send.return_value = {"success": True, "ts": "1234567890.123"}

            # Act
            result = slack_service.send_refund_request_notification(
                order_data=order_data,
                requestor_info=requestor_info,
                error_type="email_mismatch",
                order_customer_email="lilaanchors@gmail.com",
                raw_order_number="39611",  # Added missing raw_order_number
                sheet_link="https://docs.google.com/spreadsheets/test",
            )

            # Assert
            assert result["success"] is True
            mock_send.assert_called_once()

            # Verify the message structure
            call_args = mock_send.call_args
            message_text = call_args[1]["message_text"]

            # Validate key components of the email mismatch error
            assert "⚠️ *Email Mismatch - Action Required*" in message_text
            assert (
                "*Request Type*: 🎟️ Store Credit to use toward a future order"
                in message_text
            )
            assert (
                "📧 *Requested by:* joe test (<mailto:jdazz87@gmail.com|jdazz87@gmail.com>)"
                in message_text
            )
            assert (
                "*Email Associated with Order:* <mailto:lilaanchors@gmail.com|lilaanchors@gmail.com>"
                in message_text
            )
            assert (
                "*Order Number:* <https://admin.shopify.com/store/09fe59-3/orders/54321|#39611>"
                in message_text
            )
            # Check that the message contains the email mismatch warning
            assert (
                "⚠️ *The email provided does not match the order's customer email.*"
                in message_text
            )
            # Email mismatch messages don't include team mentions
            assert (
                "🔗 *<https://docs.google.com/spreadsheets/test|View Request in Google Sheets>*"
                in message_text
            )

    def test_order_not_found_error_message_format(self, slack_service):
        """Test error message when order is not found in Shopify"""
        # Arrange - data matching the third actual message
        requestor_info = {
            "name": {"first": "joe", "last": "test"},
            "email": "jdazz87@gmail.com",
            "refund_type": "refund",
            "notes": "test notes",
        }

        # Mock the Slack API call to capture the message
        with patch.object(slack_service.api_client, "send_message") as mock_send:
            mock_send.return_value = {"success": True, "ts": "1234567890.123"}

            # Act
            result = slack_service.send_refund_request_notification(
                requestor_info=requestor_info,
                error_type="order_not_found",
                raw_order_number="invalidordernumber",
                sheet_link="https://docs.google.com/spreadsheets/test",
            )

            # Assert
            assert result["success"] is True
            mock_send.assert_called_once()

            # Verify the message structure
            call_args = mock_send.call_args
            message_text = call_args[1]["message_text"]

            # Validate key components of the order not found error
            assert (
                "❌ *Error with Refund Request - Order Not Found in Shopify*"
                in message_text
            )
            assert (
                "*Request Type*: 💵 Refund back to original form of payment"
                in message_text
            )
            assert "*Requested by:* joe test (jdazz87@gmail.com)" in message_text
            assert (
                "🔎 *Order Number Provided:* invalidordernumber - this order cannot be found in Shopify"
                in message_text
            )
            assert "*Notes provided by requestor*: test notes" in message_text
            assert (
                "📩 *The requestor has been emailed to please provide correct order info"
                in message_text
            )
            assert (
                "🔗 *<https://docs.google.com/spreadsheets/test|View Request in Google Sheets>*"
                in message_text
            )
            # Note: No sport mention for order not found since we don't have product info

    def test_successful_refund_request_message_format(self, slack_service):
        """Test successful refund request message with proper season calculation"""
        # Arrange - data matching the fourth actual message
        order_data = {
            "order": {
                "id": "gid://shopify/Order/54321",  # Fixed: added 'id' field
                "orderId": "gid://shopify/Order/54321",
                "orderName": "#39611",
                "orderCreatedAt": "2025-06-17T03:18:00Z",
                "totalAmountPaid": 115.00,
                "product": {
                    "title": "Big Apple Dodgeball - Wednesday - WTNB+ Division - Summer 2025",
                    "productId": "gid://shopify/Product/98765",
                },
            }
        }

        requestor_info = {
            "name": {"first": "Amy", "last": "Dougherty"},
            "email": "lilaanchors@gmail.com",
            "refund_type": "refund",
            "notes": "Duplicate registration",
        }

        refund_calculation = {
            "success": True,
            "refund_amount": 92.00,
            "message": "Estimated Refund Due: $92.00\n(This request is calculated to have been submitted after the start of week 2. 80% after 15% penalty + 5% processing fee)",  # Fixed: was 'refund_text'
            "season_start_date": "7/9/25",
        }

        # Mock the Slack API call to capture the message
        with patch.object(slack_service.api_client, "send_message") as mock_send:
            mock_send.return_value = {"success": True, "ts": "1234567890.123"}

            # Act
            result = slack_service.send_refund_request_notification(
                requestor_info=requestor_info,
                sheet_link="https://docs.google.com/spreadsheets/test",
                order_data=order_data,
                refund_calculation=refund_calculation,
            )

            # Assert
            assert result["success"] is True
            mock_send.assert_called_once()

            # Verify the message structure
            call_args = mock_send.call_args
            message_text = call_args[1]["message_text"]

            # Validate key components of the successful request
            assert "📌 *New Refund Request!*" in message_text
            assert (
                "*Request Type*: 💵 Refund back to original form of payment"
                in message_text
            )
            assert (
                "📧 *Requested by:* Amy Dougherty (lilaanchors@gmail.com)"
                in message_text
            )
            assert (
                "*Order Number*: <https://admin.shopify.com/store/09fe59-3/orders/54321|#39611>"
                in message_text
            )
            assert (
                "*Product Title:* <https://admin.shopify.com/store/09fe59-3/products/98765|Big Apple Dodgeball - Wednesday - WTNB+ Division - Summer 2025>"
                in message_text
            )
            assert "*Season Start Date*: 7/9/25" in message_text
            assert "*Total Paid:* $115.00" in message_text
            assert "Estimated Refund Due: $92.00" in message_text
            assert (
                "(This request is calculated to have been submitted after the start of week 2. 80% after 15% penalty + 5% processing fee)"
                in message_text
            )
            assert (
                "*Notes provided by requestor*: Duplicate registration" in message_text
            )
            assert "*Attn*: <@U0278M72535>" in message_text  # dodgeball team mention

    def test_sport_group_mentions(self, slack_service):
        """Test that sport group mentions are correctly applied"""
        # TODO: Method now always returns joe's user ID regardless of sport/environment
        test_cases = [
            ("Big Apple Kickball - Monday", "<@U0278M72535>"),
            ("Big Apple Bowling - Tuesday", "<@U0278M72535>"),
            ("Big Apple Pickleball - Wednesday", "<@U0278M72535>"),
            ("Big Apple Dodgeball - Thursday", "<@U0278M72535>"),
            ("Some Other Sport", "<@U0278M72535>"),  # no more @here fallback
        ]

        for product_title, expected_mention in test_cases:
            result = slack_service.get_sport_group_mention(product_title)
            assert result == expected_mention, f"Failed for {product_title}"

    def test_request_type_formatting(self, slack_service):
        """Test that request type text is correctly formatted"""
        assert (
            slack_service._get_request_type_text("refund")
            == "💵 Refund back to original form of payment"
        )
        assert (
            slack_service._get_request_type_text("credit")
            == "🎟️ Store Credit to use toward a future order"
        )

    def test_order_url_formatting(self, slack_service):
        """Test that order URLs are correctly formatted for Slack"""
        # Test with full GID
        order_id = "gid://shopify/Order/12345"
        order_name = "#40192"
        expected_url = "<https://admin.shopify.com/store/09fe59-3/orders/12345|#40192>"
        assert slack_service.get_order_url(order_id, order_name) == expected_url

        # Test with order name that doesn't have #
        order_name = "40192"
        expected_url = "<https://admin.shopify.com/store/09fe59-3/orders/12345|#40192>"
        assert slack_service.get_order_url(order_id, order_name) == expected_url

    def test_product_url_formatting(self, slack_service):
        """Test that product URLs are correctly formatted"""
        product_id = "gid://shopify/Product/67890"
        expected_url = "https://admin.shopify.com/store/09fe59-3/products/67890"
        assert slack_service.get_product_url(product_id) == expected_url

    def test_sheet_link_formatting(self, slack_service):
        """Test that sheet links are correctly formatted"""
        # With sheet link
        sheet_link = "https://docs.google.com/spreadsheets/test"
        expected = f"\n \n 🔗 *<{sheet_link}|View Request in Google Sheets>*\n\n"
        assert slack_service._get_sheet_link_line(sheet_link) == expected

        # Without sheet link
        assert slack_service._get_sheet_link_line(None) == ""

    def test_requestor_line_formatting(self, slack_service):
        """Test that requestor line is correctly formatted"""
        requestor_name = {"first": "Amy", "last": "Dougherty"}
        requestor_email = "lilaanchors@gmail.com"
        expected = "📧 *Requested by:* Amy Dougherty (lilaanchors@gmail.com)\n\n"
        assert (
            slack_service._get_requestor_line(requestor_name, requestor_email)
            == expected
        )

    def test_optional_notes_formatting(self, slack_service):
        """Test that optional notes are correctly formatted"""
        # With notes
        notes = "Duplicate registration"
        expected = "*Notes provided by requestor*: Duplicate registration\n\n"
        assert slack_service._get_optional_request_notes(notes) == expected

        # Without notes
        assert slack_service._get_optional_request_notes("") == ""
        assert slack_service._get_optional_request_notes(None) == ""

    def test_message_structure_consistency(self, slack_service):
        """Test that all message types follow consistent block structure"""
        # All messages should have dividers and proper block structure
        with patch.object(slack_service.api_client, "send_message") as mock_send:
            mock_send.return_value = {"success": True}

            # Test different message types
            test_cases = [
                # Success case
                {
                    "requestor_info": {
                        "name": {"first": "Test", "last": "User"},
                        "email": "test@example.com",
                        "refund_type": "refund",
                        "notes": "",
                    },
                    "sheet_link": "https://docs.google.com/spreadsheets/test",
                    "order_data": {
                        "order": {
                            "id": "123",  # Fixed: added 'id' field
                            "orderId": "123",
                            "orderName": "#123",
                            "orderCreatedAt": "2025-01-01T00:00:00Z",
                            "totalAmountPaid": 100,
                            "product": {"title": "Test Product", "productId": "456"},
                        }
                    },
                    "refund_calculation": {
                        "success": True,
                        "refund_amount": 80,
                        "message": "Test refund",  # Fixed: was 'refund_text'
                        "season_start_date": "1/1/25",
                    },
                },
                # Fallback case
                {
                    "requestor_info": {
                        "name": {"first": "Test", "last": "User"},
                        "email": "test@example.com",
                        "refund_type": "refund",
                        "notes": "",
                    },
                    "sheet_link": "https://docs.google.com/spreadsheets/test",
                    "order_data": {
                        "order": {
                            "id": "123",  # Fixed: added 'id' field
                            "orderId": "123",
                            "orderName": "#123",
                            "orderCreatedAt": "2025-01-01T00:00:00Z",
                            "totalAmountPaid": 100,
                            "product": {"title": "Test Product", "productId": "456"},
                        }
                    },
                    "refund_calculation": {"success": False},
                },
                # Error cases
                {
                    "requestor_info": {
                        "name": {"first": "Test", "last": "User"},
                        "email": "test@example.com",
                        "refund_type": "refund",
                        "notes": "",
                    },
                    "sheet_link": "https://docs.google.com/spreadsheets/test",
                    "error_type": "order_not_found",
                    "raw_order_number": "123",
                },
            ]

            for test_case in test_cases:
                slack_service.send_refund_request_notification(**test_case)

                # Verify that send_message was called with proper parameters
                call_args = mock_send.call_args
                assert call_args is not None, "send_message should have been called"

                # Check the parameters passed to send_message
                assert "message_text" in call_args[1], "message_text should be passed"
                assert (
                    "action_buttons" in call_args[1]
                ), "action_buttons should be passed"

                message_text = call_args[1]["message_text"]
                action_buttons = call_args[1]["action_buttons"]

                # Verify message content
                assert len(message_text) > 0, "Message text should not be empty"
                assert (
                    "Refund Request" in message_text or "Error" in message_text
                ), "Message should contain refund/error content"

                # Verify action buttons structure
                if action_buttons:
                    for button in action_buttons:
                        assert "type" in button, "Button should have type"
                        assert "text" in button, "Button should have text"
                        assert "action_id" in button, "Button should have action_id"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
