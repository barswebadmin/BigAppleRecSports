"""
Test progressive status replacement logic to ensure proper user attribution and no duplicate lines.

This test suite verifies that status indicators are replaced in-place rather than added,
and that each step maintains proper user attribution.
"""

import pytest
from unittest.mock import Mock
from services.slack.message_builder import SlackMessageBuilder
from services.slack.slack_refunds_utils import SlackRefundsUtils


class TestProgressiveStatusReplacement:
    """Test progressive status replacement functionality"""

    @pytest.fixture
    def mock_orders_service(self):
        """Mock orders service"""
        mock = Mock()
        mock.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": {
                "id": "gid://shopify/Order/12345",
                "line_items": [
                    {
                        "title": "Test Product - Monday - Summer 2025",
                        "product": {
                            "id": "gid://shopify/Product/67890",
                            "descriptionHtml": "Season starts on 10/8/25",
                        },
                    }
                ],
                "customer": {"email": "test@example.com"},
            },
        }
        return mock

    @pytest.fixture
    def mock_settings(self):
        """Mock settings"""
        mock = Mock()
        mock.is_debug_mode = False
        return mock

    @pytest.fixture
    def message_builder(self):
        """Create message builder instance"""
        return SlackMessageBuilder({"test": "@test"})

    @pytest.fixture
    def slack_utils(self, mock_orders_service, mock_settings):
        """Create slack utils instance with mocked dependencies"""
        return SlackRefundsUtils(mock_orders_service, mock_settings)

    def test_order_cancellation_replacement_not_canceled(self, message_builder):
        """Test that order cancellation creates proper status with user attribution"""
        # Mock order data
        order_data = {
            "order": {
                "id": "gid://shopify/Order/12345",
                "line_items": [{"title": "Test Product"}],
                "customer": {"email": "test@example.com"},
            },
            "refund_calculation": {"amount": 50.0, "type": "refund"},
        }

        requestor_name = {"first": "John", "last": "Doe"}
        slack_user_id = "U12345"

        result = message_builder.create_refund_decision_message(
            order_data=order_data,
            requestor_name=requestor_name,
            requestor_email="test@example.com",
            refund_type="refund",
            sport_mention="@test",
            order_cancelled=False,
            slack_user_id=slack_user_id,
        )

        message_text = result["text"]

        # Verify order status is present with user attribution
        assert "✅ *Order Not Canceled*, processed by <@U12345>" in message_text

        # Verify other steps remain pending
        assert "📋 Refund processing pending" in message_text
        assert "📋 Inventory restocking pending" in message_text

        # Verify no duplicate status lines
        status_lines = [
            line for line in message_text.split("\n") if "Order Not Canceled" in line
        ]
        assert (
            len(status_lines) == 1
        ), f"Found duplicate order status lines: {status_lines}"

    def test_order_cancellation_replacement_canceled(self, message_builder):
        """Test that order cancellation creates proper status for canceled orders"""
        order_data = {
            "order": {
                "id": "gid://shopify/Order/12345",
                "line_items": [{"title": "Test Product"}],
                "customer": {"email": "test@example.com"},
            },
            "refund_calculation": {"amount": 50.0, "type": "refund"},
        }

        requestor_name = {"first": "John", "last": "Doe"}
        slack_user_id = "U12345"

        result = message_builder.create_refund_decision_message(
            order_data=order_data,
            requestor_name=requestor_name,
            requestor_email="test@example.com",
            refund_type="refund",
            sport_mention="@test",
            order_cancelled=True,
            slack_user_id=slack_user_id,
        )

        message_text = result["text"]

        # Verify order status is present with user attribution
        assert "✅ *Order Canceled*, processed by <@U12345>" in message_text

        # Verify other steps remain pending
        assert "📋 Refund processing pending" in message_text
        assert "📋 Inventory restocking pending" in message_text

        # Verify no duplicate status lines
        status_lines = [
            line for line in message_text.split("\n") if "Order Canceled" in line
        ]
        assert (
            len(status_lines) == 1
        ), f"Found duplicate order status lines: {status_lines}"

    def test_refund_processing_replacement(self, slack_utils):
        """Test that refund processing replaces pending indicator with completion status"""
        # Create a message with progress indicators
        current_message = """📧 *Requested by:* John Doe (test@example.com)
*Order Number*: 42305
*Product Title:* Test Product

✅ *Order Not Canceled*, processed by <@U12345>
📋 Refund processing pending
📋 Inventory restocking pending

*Request Submitted At*: 09/10/25 at 10:27 PM
*Order Created At:* 09/10/25 at 8:15 PM
*Total Paid:* $50.00"""

        order_data = {
            "id": "gid://shopify/Order/12345",
            "line_items": [{"title": "Test Product"}],
        }

        result = slack_utils.build_comprehensive_success_message(
            order_data=order_data,
            refund_amount=50.0,
            refund_type="refund",
            raw_order_number="42305",
            order_cancelled=False,
            requestor_name={"first": "John", "last": "Doe"},
            requestor_email="test@example.com",
            processor_user="U67890",
            current_message_text=current_message,
        )

        message_text = result["text"]

        # The key test: verify refund processing is completed and no duplicate
        assert "✅ Refund processing completed" in message_text
        assert "$50.00 *refund* issued by <@U67890>" in message_text

        # Verify no old refund processing pending line remains
        assert "📋 Refund processing pending" not in message_text

        # Basic structure test
        refund_completed_lines = [
            line
            for line in message_text.split("\n")
            if "Refund processing completed" in line
        ]
        assert (
            len(refund_completed_lines) == 1
        ), f"Should have exactly 1 refund completion line, got: {refund_completed_lines}"

    def test_no_refund_processing_replacement(self, slack_utils):
        """Test that no refund processing replaces pending indicator properly"""
        current_message = """📧 *Requested by:* John Doe (test@example.com)
*Order Number*: 42305
*Product Title:* Test Product

✅ *Order Not Canceled*, processed by <@U12345>
📋 Refund processing pending
📋 Inventory restocking pending

*Request Submitted At*: 09/10/25 at 10:27 PM
*Total Paid:* $50.00"""

        order_data = {
            "id": "gid://shopify/Order/12345",
            "line_items": [{"title": "Test Product"}],
        }

        result = slack_utils.build_comprehensive_no_refund_message(
            order_data=order_data,
            raw_order_number="42305",
            order_cancelled=False,
            requestor_name={"first": "John", "last": "Doe"},
            requestor_email="test@example.com",
            processor_user="U67890",
            thread_ts="123456789.123",
            current_message_full_text=current_message,
        )

        message_text = result["text"]

        # Verify order status is preserved from current message
        assert "✅ *Order Not Canceled*, processed by <@U12345>" in message_text

        # Verify no refund status with new user
        assert "✅ *Not Refunded by <@U67890>*" in message_text

        # Verify inventory step remains pending
        assert "📋 Inventory restocking pending" in message_text

        # Verify no old refund processing pending line remains
        assert "📋 Refund processing pending" not in message_text

    def test_inventory_restocking_yes_replacement(self, slack_utils):
        """Test that inventory restocking (yes) replaces pending indicator properly"""
        current_message = """📧 *Requested by:* John Doe (test@example.com)
*Order Number*: 42305

✅ *Order Not Canceled*, processed by <@U12345>
✅ Refund processing completed
📋 Inventory restocking pending

$50.00 **refund** issued by <@U67890>"""

        result = slack_utils.build_completion_message_after_restocking(
            current_message_full_text=current_message,
            action_id="restock_test_variant",
            variant_name="Test Variant",
            restock_user="U99999",
            sheet_link="https://sheets.google.com/test",
            raw_order_number="42305",
        )

        # Verify order and refund status are preserved
        assert "✅ *Order Not Canceled*, processed by <@U12345>" in result
        assert "✅ Refund processing completed" in result

        # Verify inventory restocking is completed with new user
        assert "✅ *Inventory restocked (Test Variant) by <@U99999>*" in result

        # Verify no old inventory restocking pending line remains
        assert "📋 Inventory restocking pending" not in result

        # Verify no duplicate lines - check for any inventory-related lines
        inventory_lines = [line for line in result.split("\n") if "Inventory" in line]
        assert (
            len(inventory_lines) == 1
        ), f"Found duplicate inventory lines: {inventory_lines}"

    def test_inventory_restocking_no_replacement(self, slack_utils):
        """Test that inventory restocking (no) replaces pending indicator properly"""
        current_message = """📧 *Requested by:* John Doe (test@example.com)
*Order Number*: 42305

✅ *Order Not Canceled*, processed by <@U12345>
✅ *Not Refunded by <@U67890>*
📋 Inventory restocking pending"""

        result = slack_utils.build_completion_message_after_restocking(
            current_message_full_text=current_message,
            action_id="do_not_restock",
            variant_name="Test Variant",
            restock_user="U99999",
            sheet_link="https://sheets.google.com/test",
            raw_order_number="42305",
        )

        # Verify order and refund status are preserved
        assert "✅ *Order Not Canceled*, processed by <@U12345>" in result
        assert "✅ *Not Refunded by <@U67890>*" in result

        # Verify inventory not restocked with new user
        assert "✅ *Inventory not restocked by <@U99999>*" in result

        # Verify no old inventory restocking pending line remains
        assert "📋 Inventory restocking pending" not in result

    def test_no_duplicate_lines_comprehensive_flow(self, message_builder, slack_utils):
        """Test complete flow ensures no duplicate lines are ever added"""
        # Step 1: Initial order decision (not canceled)
        order_data = {
            "order": {
                "id": "gid://shopify/Order/12345",
                "line_items": [{"title": "Test Product"}],
                "customer": {"email": "test@example.com"},
            },
            "refund_calculation": {"amount": 50.0, "type": "refund"},
        }

        step1_result = message_builder.create_refund_decision_message(
            order_data=order_data,
            requestor_name={"first": "John", "last": "Doe"},
            requestor_email="test@example.com",
            refund_type="refund",
            sport_mention="@test",
            order_cancelled=False,
            slack_user_id="U12345",
        )

        # Step 2: Process refund
        step2_result = slack_utils.build_comprehensive_success_message(
            order_data=order_data["order"],
            refund_amount=50.0,
            refund_type="refund",
            raw_order_number="42305",
            order_cancelled=False,
            requestor_name={"first": "John", "last": "Doe"},
            requestor_email="test@example.com",
            processor_user="U67890",
            current_message_text=step1_result["text"],
        )

        # Step 3: Complete inventory restocking
        step3_result = slack_utils.build_completion_message_after_restocking(
            current_message_full_text=step2_result["text"],
            action_id="restock_test_variant",
            variant_name="Test Variant",
            restock_user="U99999",
            sheet_link="https://sheets.google.com/test",
            raw_order_number="42305",
        )

        final_message = step3_result

        # Verify final state has exactly one line for each status
        order_status_lines = [
            line for line in final_message.split("\n") if "Order Not Canceled" in line
        ]
        refund_status_lines = [
            line
            for line in final_message.split("\n")
            if "Refund processing completed" in line or "refund** issued by" in line
        ]
        inventory_status_lines = [
            line for line in final_message.split("\n") if "Inventory restocked" in line
        ]

        assert (
            len(order_status_lines) == 1
        ), f"Expected 1 order status line, got {len(order_status_lines)}: {order_status_lines}"
        assert (
            len(inventory_status_lines) == 1
        ), f"Expected 1 inventory status line, got {len(inventory_status_lines)}: {inventory_status_lines}"

        # Verify no pending indicators remain
        assert "📋 Order cancellation pending" not in final_message
        assert "📋 Refund processing pending" not in final_message
        assert "📋 Inventory restocking pending" not in final_message

        # Verify all user attributions are present
        assert "<@U12345>" in final_message  # Order processor
        assert "<@U67890>" in final_message  # Refund processor
        assert "<@U99999>" in final_message  # Inventory processor

    def test_user_attribution_format(self, message_builder):
        """Test that user attribution follows correct Slack mention format"""
        order_data = {
            "order": {
                "id": "gid://shopify/Order/12345",
                "product": {
                    "id": "gid://shopify/Product/7350462185566",
                    "title": "Test Product",
                },
                "line_items": [{"title": "Test Product"}],
                "customer": {"email": "test@example.com"},
            },
            "refund_calculation": {"amount": 50.0, "type": "refund"},
        }

        result = message_builder.create_refund_decision_message(
            order_data=order_data,
            requestor_name={"first": "John", "last": "Doe"},
            requestor_email="test@example.com",
            refund_type="refund",
            sport_mention="@sport_groups_test",
            order_cancelled=False,
            slack_user_id="U12345ABC",  # Test with longer user ID
        )

        message_text = result["text"]

        # Verify proper Slack mention format
        assert "<@U12345ABC>" in message_text
        assert "processed by <@U12345ABC>" in message_text

        # Verify it's not malformed in the processed by line specifically
        slack_user_id = "U12345ABC"
        lines = message_text.split("\n")
        processed_by_lines = [line for line in lines if "processed by" in line]
        for line in processed_by_lines:
            assert f"<@{slack_user_id}>" in line  # Proper format
            # Check for malformed patterns that would NOT be substrings of the correct format
            assert (
                f" @{slack_user_id}>" not in line
            )  # Missing opening < (with space before)
            assert (
                f"<@{slack_user_id} " not in line
            )  # Missing closing > (with space after)
