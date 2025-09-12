"""
Core status replacement logic test - ensures the fundamental functionality works.

This test validates that:
1. Status indicators are replaced rather than duplicated
2. User attribution is properly maintained
3. No regression in core functionality
"""

import pytest
from unittest.mock import Mock
from services.slack.message_builder import SlackMessageBuilder
from services.slack.slack_refunds_utils import SlackRefundsUtils


class TestCoreStatusLogic:
    """Test core status replacement functionality"""

    @pytest.fixture
    def mock_orders_service(self):
        mock = Mock()
        mock.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": {
                "id": "gid://shopify/Order/12345",
                "line_items": [{"title": "Test Product"}],
                "customer": {"email": "test@example.com"}
            }
        }
        return mock

    @pytest.fixture
    def mock_settings(self):
        mock = Mock()
        mock.is_debug_mode = False
        return mock

    @pytest.fixture
    def message_builder(self):
        return SlackMessageBuilder({"test": "@test"})

    @pytest.fixture
    def slack_utils(self, mock_orders_service, mock_settings):
        return SlackRefundsUtils(mock_orders_service, mock_settings)

    def test_order_decision_creates_proper_status(self, message_builder):
        """Test that order decision creates proper status indicators"""
        order_data = {
            "order": {
                "id": "gid://shopify/Order/12345",
                "line_items": [{"title": "Test Product"}],
                "customer": {"email": "test@example.com"}
            },
            "refund_calculation": {"amount": 50.0, "type": "refund"}
        }
        
        result = message_builder.create_refund_decision_message(
            order_data=order_data,
            requestor_name={"first": "John", "last": "Doe"},
            requestor_email="test@example.com",
            refund_type="refund",
            sport_mention="@test",
            order_cancelled=False,
            slack_user_id="U12345"
        )
        
        message_text = result["text"]
        
        # Core requirements
        assert "✅ *Order Not Canceled*, processed by <@U12345>" in message_text
        assert "📋 Refund processing pending" in message_text
        assert "📋 Inventory restocking pending" in message_text
        
        # No duplicate status
        order_lines = [line for line in message_text.split('\n') if "Order Not Canceled" in line]
        assert len(order_lines) == 1

    def test_refund_completion_updates_status(self, slack_utils):
        """Test that refund completion properly updates status"""
        current_message = """✅ *Order Not Canceled*, processed by <@U12345>
📋 Refund processing pending
📋 Inventory restocking pending"""

        order_data = {"id": "gid://shopify/Order/12345", "line_items": [{"title": "Test Product"}]}
        
        result = slack_utils.build_comprehensive_success_message(
            order_data=order_data,
            refund_amount=50.0,
            refund_type="refund",
            raw_order_number="42305",
            order_cancelled=False,
            requestor_name={"first": "John", "last": "Doe"},
            requestor_email="test@example.com",
            processor_user="U67890",
            current_message_text=current_message
        )
        
        message_text = result["text"]
        
        # Core requirements
        assert "✅ Refund processing completed" in message_text
        assert "$50.00 *refund* issued by <@U67890>" in message_text
        assert "📋 Refund processing pending" not in message_text

    def test_no_refund_updates_status(self, slack_utils):
        """Test that no refund properly updates status"""
        current_message = """✅ *Order Not Canceled*, processed by <@U12345>
📋 Refund processing pending
📋 Inventory restocking pending"""

        order_data = {"id": "gid://shopify/Order/12345", "line_items": [{"title": "Test Product"}]}
        
        result = slack_utils.build_comprehensive_no_refund_message(
            order_data=order_data,
            raw_order_number="42305",
            order_cancelled=False,
            requestor_name={"first": "John", "last": "Doe"},
            requestor_email="test@example.com",
            processor_user="U67890",
            thread_ts="123456789.123",
            current_message_full_text=current_message
        )
        
        message_text = result["text"]
        
        # CRITICAL: Verify user attribution is preserved
        assert "✅ *Order Not Canceled*, processed by <@U12345>" in message_text, f"Original order processor attribution missing in: {message_text}"
        assert "✅ *Not Refunded by <@U67890>*" in message_text, f"Refund processor attribution missing in: {message_text}"
        assert "📋 Inventory restocking pending" in message_text
        
        # Count user attributions to ensure both are present
        user_attributions = [line for line in message_text.split('\n') if '@U' in line]
        assert len(user_attributions) >= 2, f"Expected at least 2 user attributions, got {len(user_attributions)}: {user_attributions}"

    def test_inventory_completion_updates_status(self, slack_utils):
        """Test that inventory completion properly updates status"""
        current_message = """✅ *Order Not Canceled*, processed by <@U12345>
✅ Refund processing completed
📋 Inventory restocking pending"""

        result = slack_utils.build_completion_message_after_restocking(
            current_message_full_text=current_message,
            action_id="restock_test_variant",
            variant_name="Test Variant",
            restock_user="U99999",
            sheet_link="https://sheets.google.com/test",
            raw_order_number="42305"
        )
        
        # Core requirements
        assert "✅ *Inventory restocked (Test Variant) by <@U99999>*" in result
        assert "📋 Inventory restocking pending" not in result

    def test_user_attribution_format(self, message_builder):
        """Test that user attribution follows correct Slack format"""
        order_data = {
            "order": {
                "id": "gid://shopify/Order/12345",
                "line_items": [{"title": "Test Product"}],
                "customer": {"email": "test@example.com"}
            },
            "refund_calculation": {"amount": 50.0, "type": "refund"}
        }
        
        result = message_builder.create_refund_decision_message(
            order_data=order_data,
            requestor_name={"first": "John", "last": "Doe"},
            requestor_email="test@example.com",
            refund_type="refund",
            sport_mention="@test",
            order_cancelled=False,
            slack_user_id="U12345ABC"
        )
        
        message_text = result["text"]
        
        # User attribution should be properly formatted
        assert "<@U12345ABC>" in message_text
        assert "processed by <@U12345ABC>" in message_text

    def test_no_duplicate_status_lines(self, message_builder):
        """Critical test: ensure no duplicate status lines are created"""
        order_data = {
            "order": {
                "id": "gid://shopify/Order/12345", 
                "line_items": [{"title": "Test Product"}],
                "customer": {"email": "test@example.com"}
            },
            "refund_calculation": {"amount": 50.0, "type": "refund"}
        }
        
        result = message_builder.create_refund_decision_message(
            order_data=order_data,
            requestor_name={"first": "John", "last": "Doe"},
            requestor_email="test@example.com",
            refund_type="refund",
            sport_mention="@test",
            order_cancelled=False,
            slack_user_id="U12345"
        )
        
        message_text = result["text"]
        lines = message_text.split('\n')
        
        # Count occurrences of each type of status indicator
        order_status_count = len([line for line in lines if "Order Not Canceled" in line])
        refund_pending_count = len([line for line in lines if "📋 Refund processing pending" in line])
        inventory_pending_count = len([line for line in lines if "📋 Inventory restocking pending" in line])
        
        # Each status should appear exactly once
        assert order_status_count == 1, f"Order status appears {order_status_count} times, should be 1"
        assert refund_pending_count == 1, f"Refund pending appears {refund_pending_count} times, should be 1" 
        assert inventory_pending_count == 1, f"Inventory pending appears {inventory_pending_count} times, should be 1"

    def test_no_refund_preserves_user_attribution_in_all_paths(self, slack_utils, mock_orders_service):
        """CRITICAL TEST: Ensure no refund preserves user attribution in all code paths (main + fallbacks)"""
        
        # Test realistic current message with full context
        realistic_current_message = """📧 *Requested by:* John Doe (test@example.com)
*Order Number*: 42305
*Product Title:* Test Product

✅ *Order Not Canceled*, processed by <@U12345>
📋 Refund processing pending
📋 Inventory restocking pending

*Request Submitted At*: 09/10/25 at 10:27 PM
*Total Paid*: $50.00"""

        # Test 1: Main path (order fetch succeeds)
        mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": {"id": "gid://shopify/Order/12345", "line_items": [{"title": "Test Product"}]}
        }
        
        result = slack_utils.build_comprehensive_no_refund_message(
            order_data={"id": "gid://shopify/Order/12345", "line_items": [{"title": "Test Product"}]},
            raw_order_number="42305",
            order_cancelled=False,
            requestor_name={"first": "John", "last": "Doe"},
            requestor_email="test@example.com",
            processor_user="U67890",
            thread_ts="123456789.123",
            current_message_full_text=realistic_current_message
        )
        
        message_text = result["text"]
        
        # CRITICAL ASSERTIONS: Both user attributions must be preserved
        assert "processed by <@U12345>" in message_text, f"CRITICAL: Original order processor lost! Message: {message_text}"
        assert "by <@U67890>" in message_text, f"CRITICAL: Refund processor attribution lost! Message: {message_text}"
        
        # Verify specific format
        order_lines = [line for line in message_text.split('\n') if "Order Not Canceled" in line and "U12345" in line]
        refund_lines = [line for line in message_text.split('\n') if "Not Refunded" in line and "U67890" in line]
        
        assert len(order_lines) == 1, f"Expected exactly 1 order status line with U12345, got {len(order_lines)}: {order_lines}"
        assert len(refund_lines) == 1, f"Expected exactly 1 refund status line with U67890, got {len(refund_lines)}: {refund_lines}"

    def test_do_not_restock_updates_inventory_status(self, slack_utils):
        """CRITICAL TEST: Ensure do_not_restock properly updates inventory status with green check"""
        
        # Test realistic current message after no refund
        current_message = """📧 *Requested by:* John Doe (test@example.com)
*Order Number*: 42305
*Product Title:* Test Product

✅ *Order Not Canceled*, processed by <@U12345>
🚫 *Not Refunded by <@U67890>*
📋 Inventory restocking pending

🔗 *View Request in Google Sheets*

Current Inventory:
• No inventory information available
Restock Inventory?"""

        result = slack_utils.build_completion_message_after_restocking(
            current_message_full_text=current_message,
            action_id="do_not_restock",
            variant_name="",
            restock_user="U88888",
            sheet_link="https://docs.google.com/spreadsheets/test",
            raw_order_number="42305"
        )
        
        # CRITICAL ASSERTIONS: Inventory status must be properly updated
        assert "✅ *Inventory not restocked by <@U88888>*" in result, f"CRITICAL: Inventory status not updated! Message: {result}"
        assert "📋 Inventory restocking pending" not in result, f"CRITICAL: Pending inventory status still present! Message: {result}"
        
        # Verify specific format with green check emoji
        inventory_lines = [line for line in result.split('\n') if "Inventory not restocked" in line and "U88888" in line]
        assert len(inventory_lines) == 1, f"Expected exactly 1 inventory completion line, got {len(inventory_lines)}: {inventory_lines}"
        
        # Verify it starts with green check
        inventory_line = inventory_lines[0]
        assert inventory_line.startswith("✅"), f"Inventory status line should start with ✅, got: {inventory_line}"

    def test_restock_updates_inventory_status_with_variant(self, slack_utils):
        """Test that actual restocking updates inventory status with variant name and green check"""
        
        current_message = """📧 *Requested by:* John Doe (test@example.com)
*Order Number*: 42305
*Product Title:* Test Product

✅ *Order Not Canceled*, processed by <@U12345>
🚫 *Not Refunded by <@U67890>*
📋 Inventory restocking pending

🔗 *View Request in Google Sheets*

Current Inventory:
• Large: 5 available
Restock Inventory?"""

        result = slack_utils.build_completion_message_after_restocking(
            current_message_full_text=current_message,
            action_id="restock_large",
            variant_name="Large",
            restock_user="U77777",
            sheet_link="https://docs.google.com/spreadsheets/test",
            raw_order_number="42305"
        )
        
        # CRITICAL ASSERTIONS: Inventory status must show restocked with variant
        assert "✅ *Inventory restocked (Large) by <@U77777>*" in result, f"CRITICAL: Restock status not updated! Message: {result}"
        assert "📋 Inventory restocking pending" not in result, f"CRITICAL: Pending inventory status still present! Message: {result}"
        
        # Verify specific format with variant name
        inventory_lines = [line for line in result.split('\n') if "Inventory restocked" in line and "U77777" in line]
        assert len(inventory_lines) == 1, f"Expected exactly 1 inventory completion line, got {len(inventory_lines)}: {inventory_lines}"
        
        # Verify it contains variant name in parentheses
        inventory_line = inventory_lines[0]
        assert "(Large)" in inventory_line, f"Inventory status should include variant name, got: {inventory_line}"
        assert inventory_line.startswith("✅"), f"Inventory status line should start with ✅, got: {inventory_line}"
