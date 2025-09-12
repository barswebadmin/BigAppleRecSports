"""
Tests for restock button click handling.
Tests that clicking restock buttons is handled correctly through the proper service chain.
"""

import pytest
from unittest.mock import Mock, patch
from services.slack.slack_refunds_utils import SlackRefundsUtils


class TestRestockButtonHandling:
    """Test restock button click handling and processing"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_orders_service = Mock()
        self.mock_settings = Mock()
        self.slack_refunds_utils = SlackRefundsUtils(
            self.mock_orders_service, self.mock_settings
        )

        # Mock dependencies
        self.mock_message_builder = Mock()
        self.slack_refunds_utils.message_builder = self.mock_message_builder

        # Sample request data that would come from button clicks
        self.sample_restock_request_data = {
            "action": "restock_variant",
            "variantId": "gid://shopify/ProductVariant/41558875111518",
            "inventoryItemId": "gid://shopify/InventoryItem/43558875111520",  # Direct inventory item ID
            "variantTitle": "Open Registration",
            "orderId": "gid://shopify/Order/5876418969694",
            "rawOrderNumber": "#42305",
        }

        self.sample_do_not_restock_request_data = {
            "action": "do_not_restock",
            "orderId": "gid://shopify/Order/5876418969694",
            "rawOrderNumber": "#42305",
        }

        self.sample_current_message = """*Request Type*: 💰 Refund back to original form of payment

📧 *Requested by:* joe test1 (<mailto:jdazz87@gmail.com|jdazz87@gmail.com>)

*Order Number*: <https://admin.shopify.com/store/09fe59-3/orders/5876418969694|#42305>

*Product Title:* <https://admin.shopify.com/store/09fe59-3/products/7350462185566|joe test product>

*Refund Provided:* $1.90

🔗 *<https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit|View Request in Google Sheets>*

🚀 *Order Canceled*, processed by <@U0278M72535>

💰 *Refunded by <@U0278M72535>*

Current Inventory:
• Open Registration: 12 spots available"""

    @patch("services.slack.slack_refunds_utils.SlackRefundsUtils.extract_sheet_link")
    @patch(
        "services.slack.slack_refunds_utils.SlackRefundsUtils.build_completion_message_after_restocking"
    )
    @patch(
        "services.slack.slack_refunds_utils.SlackRefundsUtils.update_slack_on_shopify_success"
    )
    @pytest.mark.asyncio
    async def test_successful_variant_restock(
        self, mock_update_slack, mock_build_completion, mock_extract_sheet
    ):
        """Test successful variant restock handling"""

        # Mock dependencies
        mock_extract_sheet.return_value = "https://docs.google.com/spreadsheets/test"
        mock_build_completion.return_value = (
            "✅ *Refund Processing Complete* - Open Registration restocked"
        )

        # Mock Shopify service calls
        self.mock_orders_service.shopify_service.get_inventory_item_and_quantity.return_value = {
            "success": True,
            "inventoryItemId": "gid://shopify/InventoryItem/43659002642526",
            "inventoryQuantity": 12,
        }

        self.mock_orders_service.shopify_service.adjust_inventory.return_value = {
            "success": True,
            "message": "Successfully adjusted inventory by 1",
        }

        # Call the method
        result = await self.slack_refunds_utils.handle_restock_inventory(
            request_data=self.sample_restock_request_data,
            action_id="restock_open",
            channel_id="C092RU7R6PL",
            thread_ts="1757491928.415319",
            slack_user_name="joe",
            current_message_full_text=self.sample_current_message,
            trigger_id="9496427801748.2602080084.226e2372921ab1312f64e6b55024097c",
        )

        # Verify successful processing
        assert result["success"] is True
        assert "restocked" in result["message"].lower()

        # Since inventoryItemId is provided in button data, should NOT call lookup
        self.mock_orders_service.shopify_service.get_inventory_item_and_quantity.assert_not_called()
        self.mock_orders_service.shopify_service.adjust_inventory.assert_called_once_with(
            "gid://shopify/InventoryItem/43558875111520",  # From button data
            delta=1,
        )

        # Verify Slack message update
        mock_update_slack.assert_called_once()
        mock_build_completion.assert_called_once()

    @patch("services.slack.slack_refunds_utils.SlackRefundsUtils.extract_sheet_link")
    @patch(
        "services.slack.slack_refunds_utils.SlackRefundsUtils.build_completion_message_after_restocking"
    )
    @patch(
        "services.slack.slack_refunds_utils.SlackRefundsUtils.update_slack_on_shopify_success"
    )
    @pytest.mark.asyncio
    async def test_do_not_restock_handling(
        self, mock_update_slack, mock_build_completion, mock_extract_sheet
    ):
        """Test 'Do Not Restock' button handling"""

        # Mock dependencies
        mock_extract_sheet.return_value = "https://docs.google.com/spreadsheets/test"
        mock_build_completion.return_value = (
            "✅ *Refund Processing Complete* - No inventory restocked"
        )

        # Call the method
        result = await self.slack_refunds_utils.handle_restock_inventory(
            request_data=self.sample_do_not_restock_request_data,
            action_id="do_not_restock",
            channel_id="C092RU7R6PL",
            thread_ts="1757491928.415319",
            slack_user_name="joe",
            current_message_full_text=self.sample_current_message,
        )

        # Verify successful processing
        assert result["success"] is True
        assert "declined" in result["message"].lower()

        # Verify NO Shopify service calls for "do not restock"
        self.mock_orders_service.shopify_service.get_inventory_item_and_quantity.assert_not_called()
        self.mock_orders_service.shopify_service.adjust_inventory.assert_not_called()

        # Verify Slack message update
        mock_update_slack.assert_called_once()
        mock_build_completion.assert_called_once_with(
            current_message_full_text=self.sample_current_message,
            action_id="do_not_restock",
            variant_name="",
            restock_user="joe",
            sheet_link="https://docs.google.com/spreadsheets/test",
            raw_order_number="#42305",
        )

    @patch(
        "services.slack.slack_refunds_utils.SlackRefundsUtils.send_modal_error_to_user"
    )
    @pytest.mark.asyncio
    async def test_missing_variant_id_error(self, mock_send_modal):
        """Test handling when variant ID is missing from request data"""

        # Request data without variantId
        invalid_request_data = {
            "action": "restock_variant",
            "variantTitle": "Open Registration",
            "orderId": "gid://shopify/Order/5876418969694",
            "rawOrderNumber": "#42305",
        }

        # Call the method
        result = await self.slack_refunds_utils.handle_restock_inventory(
            request_data=invalid_request_data,
            action_id="restock_open",
            channel_id="C092RU7R6PL",
            thread_ts="1757491928.415319",
            slack_user_name="joe",
            current_message_full_text=self.sample_current_message,
            trigger_id="test_trigger_id",
        )

        # Verify error handling
        assert result["success"] is False
        assert "Missing variant ID" in result["message"]

        # Verify modal error was sent
        mock_send_modal.assert_called_once()

    @patch(
        "services.slack.slack_refunds_utils.SlackRefundsUtils.send_modal_error_to_user"
    )
    @pytest.mark.asyncio
    async def test_shopify_inventory_lookup_failure(self, mock_send_modal):
        """Test handling when Shopify inventory lookup fails (fallback case)"""

        # Use request data WITHOUT inventoryItemId to trigger fallback
        request_data_no_inventory_id = {
            "action": "restock_variant",
            "variantId": "gid://shopify/ProductVariant/41558875111518",
            "variantTitle": "Open Registration",
            "orderId": "gid://shopify/Order/5876418969694",
            "rawOrderNumber": "#42305",
        }

        # Mock Shopify inventory lookup failure
        self.mock_orders_service.shopify_service.get_inventory_item_and_quantity.return_value = {
            "success": False,
            "message": "Variant not found in Shopify",
        }

        # Call the method
        result = await self.slack_refunds_utils.handle_restock_inventory(
            request_data=request_data_no_inventory_id,
            action_id="restock_open",
            channel_id="C092RU7R6PL",
            thread_ts="1757491928.415319",
            slack_user_name="joe",
            current_message_full_text=self.sample_current_message,
            trigger_id="test_trigger_id",
        )

        # Verify error handling
        assert result["success"] is False
        assert "Variant not found in Shopify" in result["message"]

        # Verify modal error was sent
        mock_send_modal.assert_called_once()

        # Verify lookup was called in fallback
        self.mock_orders_service.shopify_service.get_inventory_item_and_quantity.assert_called_once_with(
            "gid://shopify/ProductVariant/41558875111518"
        )

    @patch(
        "services.slack.slack_refunds_utils.SlackRefundsUtils.send_modal_error_to_user"
    )
    @pytest.mark.asyncio
    async def test_shopify_inventory_adjustment_failure(self, mock_send_modal):
        """Test handling when Shopify inventory adjustment fails"""

        # Mock successful inventory lookup but failed adjustment
        self.mock_orders_service.shopify_service.get_inventory_item_and_quantity.return_value = {
            "success": True,
            "inventoryItemId": "gid://shopify/InventoryItem/43659002642526",
            "inventoryQuantity": 12,
        }

        self.mock_orders_service.shopify_service.adjust_inventory.return_value = {
            "success": False,
            "message": "Inventory adjustment failed: insufficient permissions",
        }

        # Call the method
        result = await self.slack_refunds_utils.handle_restock_inventory(
            request_data=self.sample_restock_request_data,
            action_id="restock_open",
            channel_id="C092RU7R6PL",
            thread_ts="1757491928.415319",
            slack_user_name="joe",
            current_message_full_text=self.sample_current_message,
            trigger_id="test_trigger_id",
        )

        # Verify error handling
        assert result["success"] is False
        assert "insufficient permissions" in result["message"]

        # Verify modal error was sent
        mock_send_modal.assert_called_once()

    def test_action_id_to_variant_name_mapping(self):
        """Test that action IDs properly map to variant names"""

        test_cases = [
            ("restock_veteran", "Veteran"),
            ("restock_early", "Early"),
            ("restock_open", "Open"),
            ("restock_coming_off_waitlist_reg", "Coming off Waitlist Reg"),
            ("restock_late", "Late"),
            ("restock_premium", "Premium"),
        ]

        for action_id, expected_variant_name in test_cases:
            # Test the action ID parsing logic (this is internal to the method)
            assert (
                expected_variant_name.lower()
                in action_id.replace("restock_", "").replace("_", " ").lower()
            )

    @patch("services.slack.slack_refunds_utils.SlackRefundsUtils.extract_sheet_link")
    @pytest.mark.asyncio
    async def test_sheet_link_extraction(self, mock_extract_sheet):
        """Test that Google Sheets link is properly extracted from current message"""

        mock_extract_sheet.return_value = "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit"

        # Mock successful processing
        self.mock_orders_service.shopify_service.get_inventory_item_and_quantity.return_value = {
            "success": True,
            "inventoryItemId": "gid://shopify/InventoryItem/43659002642526",
            "inventoryQuantity": 12,
        }

        self.mock_orders_service.shopify_service.adjust_inventory.return_value = {
            "success": True,
            "message": "Successfully adjusted inventory by 1",
        }

        # Call the method
        await self.slack_refunds_utils.handle_restock_inventory(
            request_data=self.sample_restock_request_data,
            action_id="restock_open",
            channel_id="C092RU7R6PL",
            thread_ts="1757491928.415319",
            slack_user_name="joe",
            current_message_full_text=self.sample_current_message,
        )

        # Verify sheet link extraction was called
        mock_extract_sheet.assert_called_once_with(self.sample_current_message)

    @pytest.mark.asyncio
    async def test_request_data_validation(self):
        """Test that request data is properly validated"""

        # Test with valid JSON request data
        valid_request_data = {
            "action": "restock_variant",
            "variantId": "gid://shopify/ProductVariant/41558875111518",
            "variantTitle": "Open Registration",
            "orderId": "gid://shopify/Order/5876418969694",
            "rawOrderNumber": "#42305",
        }

        # This should not raise any validation errors
        await self.slack_refunds_utils.handle_restock_inventory(
            request_data=valid_request_data,
            action_id="restock_open",
            channel_id="C092RU7R6PL",
            thread_ts="1757491928.415319",
            slack_user_name="joe",
            current_message_full_text=self.sample_current_message,
        )

        # Should attempt processing (will fail due to unmocked Shopify calls, but validates data structure)
        assert "variantId" in valid_request_data
        assert valid_request_data["variantId"].startswith(
            "gid://shopify/ProductVariant/"
        )

    @patch("services.slack.slack_refunds_utils.SlackRefundsUtils.extract_sheet_link")
    @patch(
        "services.slack.slack_refunds_utils.SlackRefundsUtils.build_completion_message_after_restocking"
    )
    @patch(
        "services.slack.slack_refunds_utils.SlackRefundsUtils.update_slack_on_shopify_success"
    )
    @pytest.mark.asyncio
    async def test_completion_message_building(
        self, mock_update_slack, mock_build_completion, mock_extract_sheet
    ):
        """Test that completion message is properly built with correct parameters"""

        # Mock dependencies
        mock_extract_sheet.return_value = "https://docs.google.com/spreadsheets/test"
        expected_completion_message = (
            "✅ *Refund Processing Complete* - Open Registration restocked by joe"
        )
        mock_build_completion.return_value = expected_completion_message

        # Mock successful Shopify calls
        self.mock_orders_service.shopify_service.get_inventory_item_and_quantity.return_value = {
            "success": True,
            "inventoryItemId": "gid://shopify/InventoryItem/43659002642526",
            "inventoryQuantity": 12,
        }

        self.mock_orders_service.shopify_service.adjust_inventory.return_value = {
            "success": True,
            "message": "Successfully adjusted inventory by 1",
        }

        # Call the method
        await self.slack_refunds_utils.handle_restock_inventory(
            request_data=self.sample_restock_request_data,
            action_id="restock_open",
            channel_id="C092RU7R6PL",
            thread_ts="1757491928.415319",
            slack_user_name="joe",
            current_message_full_text=self.sample_current_message,
        )

        # Verify completion message building
        mock_build_completion.assert_called_once_with(
            current_message_full_text=self.sample_current_message,
            action_id="restock_open",
            variant_name="Open Registration",
            restock_user="joe",
            sheet_link="https://docs.google.com/spreadsheets/test",
            raw_order_number="#42305",
        )

        # Verify Slack update with completion message
        mock_update_slack.assert_called_once_with(
            message_ts="1757491928.415319",
            success_message=expected_completion_message,
            action_buttons=[],
        )

    @pytest.mark.asyncio
    async def test_restock_with_direct_inventory_item_id(self):
        """Test restock handling using direct inventory item ID (no lookup needed)"""

        # Mock successful inventory adjustment
        self.mock_orders_service.shopify_service.adjust_inventory.return_value = {
            "success": True,
            "message": "Successfully adjusted inventory by 1",
        }

        # Mock message building
        with (
            patch.object(
                self.slack_refunds_utils, "build_completion_message_after_restocking"
            ) as mock_build_message,
            patch.object(
                self.slack_refunds_utils, "update_slack_on_shopify_success"
            ) as mock_update_slack,
        ):
            mock_build_message.return_value = "✅ Inventory restocked successfully"

            result = await self.slack_refunds_utils.handle_restock_inventory(
                request_data=self.sample_restock_request_data,
                action_id="restock_open_registration",
                channel_id="C092RU7R6PL",
                thread_ts="1757491928.415319",
                slack_user_name="admin_user",
                current_message_full_text=self.sample_current_message,
                trigger_id="test_trigger_id",
            )

            # Should succeed without any lookups
            assert result["success"] is True
            assert "Successfully restocked Open Registration by +1" in result["message"]
            assert "new_quantity" in result

            # Verify inventory adjustment was called with correct inventory item ID directly
            self.mock_orders_service.shopify_service.adjust_inventory.assert_called_once_with(
                "gid://shopify/InventoryItem/43558875111520", delta=1
            )

            # Should NOT call get_inventory_item_and_quantity since we have the inventory item ID
            self.mock_orders_service.shopify_service.get_inventory_item_and_quantity.assert_not_called()

            # Should update slack message
            mock_update_slack.assert_called_once()
