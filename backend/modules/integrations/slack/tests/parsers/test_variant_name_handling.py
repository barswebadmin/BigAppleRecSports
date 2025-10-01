"""
Tests for variant name handling and formatting for restock options.
Tests that available variants are properly extracted and formatted with a "Do Not Restock" option.
"""

from unittest.mock import Mock
from modules.integrations.slack.slack_refunds_utils import SlackRefundsUtils


class TestVariantNameHandling:
    """Test variant name extraction and formatting for restock buttons"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_orders_service = Mock()
        self.mock_settings = Mock()
        self.slack_refunds_utils = SlackRefundsUtils(
            self.mock_orders_service, self.mock_settings
        )

        # Mock message builder
        self.mock_message_builder = Mock()
        self.slack_refunds_utils.message_builder = self.mock_message_builder

    def test_variant_extraction_from_order_data_comprehensive_format(self):
        """Test extracting variants from order data in comprehensive format"""

        order_data = {
            "variants": [
                {
                    "id": "gid://shopify/ProductVariant/41558875045982",
                    "title": "Veteran Registration",
                    "inventoryQuantity": 0,
                },
                {
                    "id": "gid://shopify/ProductVariant/41558875078750",
                    "title": "Early Registration",
                    "inventoryQuantity": 5,
                },
                {
                    "id": "gid://shopify/ProductVariant/41558875111518",
                    "title": "Open Registration",
                    "inventoryQuantity": 12,
                },
                {
                    "id": "gid://shopify/ProductVariant/41558917742686",
                    "title": "Coming off Waitlist Reg",
                    "inventoryQuantity": 0,
                },
            ]
        }

        current_message_text = "Sample message"

        result = self.slack_refunds_utils.build_comprehensive_success_message(
            order_data=order_data,
            refund_amount=1.90,
            refund_type="refund",
            raw_order_number="#42305",
            order_cancelled=True,
            requestor_name={"first": "joe", "last": "test1"},
            requestor_email="joe@test.com",
            processor_user="U0278M72535",
            current_message_text=current_message_text,
        )

        action_buttons = result["action_buttons"]

        # Should have 4 restock buttons + 1 "Do Not Restock" button
        assert len(action_buttons) == 5

        # Check button texts and structure
        button_texts = [btn["text"]["text"] for btn in action_buttons]
        assert "Restock Veteran" in button_texts
        assert "Restock Early" in button_texts
        assert "Restock Open" in button_texts
        assert "Restock Coming off Waitlist Reg" in button_texts
        assert "Do Not Restock" in button_texts

        # Check button action IDs
        action_ids = [btn["action_id"] for btn in action_buttons]
        assert "confirm_restock_veteran" in action_ids
        assert "confirm_restock_early" in action_ids
        assert "confirm_restock_open" in action_ids
        assert "confirm_restock_coming_off_waitlist_reg" in action_ids
        assert "confirm_do_not_restock" in action_ids

    def test_variant_extraction_from_product_variants_format(self):
        """Test extracting variants from order data in product.variants format"""

        order_data = {
            "product": {
                "variants": [
                    {
                        "id": "gid://shopify/ProductVariant/41558875045982",
                        "title": "Veteran Registration",
                        "inventoryQuantity": 2,
                    },
                    {
                        "id": "gid://shopify/ProductVariant/41558875078750",
                        "title": "Early Registration",
                        "inventoryQuantity": 8,
                    },
                ]
            }
        }

        current_message_text = "Sample message"

        result = self.slack_refunds_utils.build_comprehensive_success_message(
            order_data=order_data,
            refund_amount=2.50,
            refund_type="credit",
            raw_order_number="#12345",
            order_cancelled=False,
            requestor_name={"first": "jane", "last": "doe"},
            requestor_email="jane@test.com",
            processor_user="U1234567890",
            current_message_text=current_message_text,
        )

        action_buttons = result["action_buttons"]

        # Should have 2 restock buttons + 1 "Do Not Restock" button
        assert len(action_buttons) == 3

        # Check button texts
        button_texts = [btn["text"]["text"] for btn in action_buttons]
        assert "Restock Veteran" in button_texts
        assert "Restock Early" in button_texts
        assert "Do Not Restock" in button_texts

    def test_inventory_quantity_display_formatting(self):
        """Test that inventory quantities are properly formatted in the message"""

        order_data = {
            "variants": [
                {
                    "id": "gid://shopify/ProductVariant/41558875045982",
                    "title": "Veteran Registration",
                    "inventoryQuantity": 0,
                },
                {
                    "id": "gid://shopify/ProductVariant/41558875078750",
                    "title": "Early Registration",
                    "inventoryQuantity": 15,
                },
                {
                    "id": "gid://shopify/ProductVariant/41558875111518",
                    "title": "Open Registration",
                    "inventoryQuantity": 1,
                },
            ]
        }

        current_message_text = "Sample message"

        result = self.slack_refunds_utils.build_comprehensive_success_message(
            order_data=order_data,
            refund_amount=1.90,
            refund_type="refund",
            raw_order_number="#42305",
            order_cancelled=True,
            requestor_name={"first": "joe", "last": "test1"},
            requestor_email="joe@test.com",
            processor_user="U0278M72535",
            current_message_text=current_message_text,
        )

        message_text = result["text"]

        # Check inventory display formatting
        assert "• Veteran Registration: 0 spots available" in message_text
        assert "• Early Registration: 15 spots available" in message_text
        assert "• Open Registration: 1 spots available" in message_text
        assert "Current Inventory:" in message_text

    def test_button_value_structure_for_variants(self):
        """Test that restock buttons have proper JSON value structure"""

        order_data = {
            "variants": [
                {
                    "id": "gid://shopify/ProductVariant/41558875045982",
                    "title": "Veteran Registration",
                    "inventoryQuantity": 0,
                }
            ]
        }

        current_message_text = "Sample message"

        result = self.slack_refunds_utils.build_comprehensive_success_message(
            order_data=order_data,
            refund_amount=1.90,
            refund_type="refund",
            raw_order_number="#42305",
            order_cancelled=True,
            requestor_name={"first": "joe", "last": "test1"},
            requestor_email="joe@test.com",
            processor_user="U0278M72535",
            current_message_text=current_message_text,
            order_id="gid://shopify/Order/5876418969694",
        )

        action_buttons = result["action_buttons"]

        # Find the veteran restock button
        veteran_button = None
        for btn in action_buttons:
            if btn["action_id"] == "confirm_restock_veteran":
                veteran_button = btn
                break

        assert veteran_button is not None

        # Parse the button value (should be JSON)
        import json

        button_value = json.loads(veteran_button["value"])

        # Check required fields in button value
        assert button_value["action"] == "confirm_restock_variant"
        assert (
            button_value["variantId"] == "gid://shopify/ProductVariant/41558875045982"
        )
        assert button_value["variantTitle"] == "Veteran Registration"
        assert button_value["orderId"] == "gid://shopify/Order/5876418969694"
        assert button_value["rawOrderNumber"] == "#42305"

    def test_do_not_restock_button_structure(self):
        """Test that 'Do Not Restock' button has proper structure"""

        order_data = {
            "variants": [
                {
                    "id": "gid://shopify/ProductVariant/41558875045982",
                    "title": "Veteran Registration",
                    "inventoryQuantity": 0,
                }
            ]
        }

        current_message_text = "Sample message"

        result = self.slack_refunds_utils.build_comprehensive_success_message(
            order_data=order_data,
            refund_amount=1.90,
            refund_type="refund",
            raw_order_number="#42305",
            order_cancelled=True,
            requestor_name={"first": "joe", "last": "test1"},
            requestor_email="joe@test.com",
            processor_user="U0278M72535",
            current_message_text=current_message_text,
            order_id="gid://shopify/Order/5876418969694",
        )

        action_buttons = result["action_buttons"]

        # Find the "Do Not Restock" button
        do_not_restock_button = None
        for btn in action_buttons:
            if btn["action_id"] == "confirm_do_not_restock":
                do_not_restock_button = btn
                break

        assert do_not_restock_button is not None

        # Check button properties
        assert do_not_restock_button["text"]["text"] == "Do Not Restock"
        assert do_not_restock_button["action_id"] == "confirm_do_not_restock"

        # Parse the button value
        import json

        button_value = json.loads(do_not_restock_button["value"])

        # Check required fields for "do not restock"
        assert button_value["action"] == "confirm_do_not_restock"
        assert button_value["orderId"] == "gid://shopify/Order/5876418969694"
        assert button_value["rawOrderNumber"] == "#42305"

    def test_action_id_generation_from_variant_titles(self):
        """Test that action IDs are properly generated from variant titles"""

        test_cases = [
            ("Veteran Registration", "restock_veteran"),
            ("Early Registration", "restock_early"),
            ("Open Registration", "restock_open"),
            ("Coming off Waitlist Reg", "restock_coming_off_waitlist_reg"),
            ("Late Registration", "restock_late"),
            ("Premium Membership", "restock_premium_membership"),  # Full conversion
        ]

        for variant_title, expected_action_id in test_cases:
            order_data = {
                "variants": [
                    {
                        "id": "gid://shopify/ProductVariant/12345",
                        "title": variant_title,
                        "inventoryQuantity": 5,
                    }
                ]
            }

            result = self.slack_refunds_utils.build_comprehensive_success_message(
                order_data=order_data,
                refund_amount=1.90,
                refund_type="refund",
                raw_order_number="#42305",
                order_cancelled=True,
                requestor_name={"first": "joe", "last": "test1"},
                requestor_email="joe@test.com",
                processor_user="U0278M72535",
                current_message_text="Sample message",
            )

            action_buttons = result["action_buttons"]
            action_ids = [btn["action_id"] for btn in action_buttons]

            assert f"confirm_{expected_action_id}" in action_ids

    def test_no_variants_available(self):
        """Test behavior when no variants are available"""

        order_data = {}  # No variants data
        current_message_text = "Sample message"

        result = self.slack_refunds_utils.build_comprehensive_success_message(
            order_data=order_data,
            refund_amount=1.90,
            refund_type="refund",
            raw_order_number="#42305",
            order_cancelled=True,
            requestor_name={"first": "joe", "last": "test1"},
            requestor_email="joe@test.com",
            processor_user="U0278M72535",
            current_message_text=current_message_text,
        )

        action_buttons = result["action_buttons"]

        # Should only have "Do Not Restock" button when no variants available
        assert len(action_buttons) == 1
        assert action_buttons[0]["action_id"] == "confirm_do_not_restock"
        assert action_buttons[0]["text"]["text"] == "Do Not Restock"

    def test_empty_variants_list(self):
        """Test behavior when variants list is empty"""

        order_data = {"variants": []}  # Empty variants list
        current_message_text = "Sample message"

        result = self.slack_refunds_utils.build_comprehensive_success_message(
            order_data=order_data,
            refund_amount=1.90,
            refund_type="refund",
            raw_order_number="#42305",
            order_cancelled=True,
            requestor_name={"first": "joe", "last": "test1"},
            requestor_email="joe@test.com",
            processor_user="U0278M72535",
            current_message_text=current_message_text,
        )

        action_buttons = result["action_buttons"]

        # Should only have "Do Not Restock" button when variants list is empty
        assert len(action_buttons) == 1
        assert action_buttons[0]["action_id"] == "confirm_do_not_restock"
