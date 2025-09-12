"""
Test suite for duplicate refund detection functionality.
Tests the check_existing_refunds method and duplicate refund message building.
"""

from unittest.mock import Mock, patch
from services.orders import OrdersService
from services.slack.message_builder import SlackMessageBuilder


class TestDuplicateRefundDetection:
    """Test class for duplicate refund detection functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.orders_service = OrdersService()

        # Mock sport groups for message builder
        sport_groups = {
            "dodgeball": "<@DODGEBALL_GROUP>",
            "kickball": "<@KICKBALL_GROUP>",
            "default": "<@DEFAULT_GROUP>",
        }
        self.message_builder = SlackMessageBuilder(sport_groups)

        # Mock Shopify service to avoid real API calls
        self.mock_shopify_service = Mock()
        self.orders_service.shopify_service = self.mock_shopify_service

        # Sample order data
        self.sample_order_id = "gid://shopify/Order/5876418969694"
        self.sample_order_name = "#42305"

        # Sample refund data from Shopify API
        self.sample_shopify_response_with_refunds = {
            "data": {
                "order": {
                    "id": "gid://shopify/Order/5876418969694",
                    "name": "#42305",
                    "refunds": [
                        {
                            "createdAt": "2024-09-10T15:30:00Z",
                            "id": "gid://shopify/Refund/123456789",
                            "legacyResourceId": "123456789",
                            "note": "Refund issued via Slack workflow for $19.00",
                            "totalRefundedSet": {
                                "presentmentMoney": {
                                    "amount": "19.00",
                                    "currencyCode": "USD",
                                }
                            },
                            "updatedAt": "2024-09-10T15:30:00Z",
                            "staffMember": {
                                "id": "gid://shopify/StaffMember/98765",
                                "firstName": "John",
                                "lastName": "Admin",
                                "email": "admin@bigapplerecsports.com",
                            },
                            "transactions": {
                                "edges": [
                                    {
                                        "node": {
                                            "id": "gid://shopify/OrderTransaction/123456",
                                            "kind": "REFUND",
                                            "status": "SUCCESS",
                                            "amount": "19.00",
                                            "gateway": "shopify_payments",
                                            "createdAt": "2024-09-10T15:30:00Z",
                                        }
                                    }
                                ]
                            },
                            "refundLineItems": {
                                "edges": [
                                    {
                                        "node": {
                                            "id": "gid://shopify/RefundLineItem/987654321",
                                            "quantity": 1,
                                            "lineItem": {
                                                "id": "gid://shopify/LineItem/111222333",
                                                "title": "Dodgeball - Open Registration",
                                            },
                                        }
                                    }
                                ]
                            },
                        }
                    ],
                }
            }
        }

        self.sample_shopify_response_no_refunds = {
            "data": {
                "order": {
                    "id": "gid://shopify/Order/5876418969694",
                    "name": "#42305",
                    "refunds": [],
                }
            }
        }

        # Sample requestor info
        self.sample_requestor_info = {
            "name": {"first": "Joe", "last": "Test"},
            "email": "joetest@example.com",
            "refund_type": "refund",
            "notes": "Customer requested refund due to schedule conflict",
        }

    def test_check_existing_refunds_with_refunds(self):
        """Test check_existing_refunds when order has existing refunds"""
        # Setup mock response
        self.mock_shopify_service._make_shopify_request.return_value = (
            self.sample_shopify_response_with_refunds
        )

        # Call the method
        result = self.orders_service.check_existing_refunds(self.sample_order_id)

        # Verify the result
        assert result["success"] is True
        assert result["has_refunds"] is True
        assert result["total_refunds"] == 1
        assert result["order_id"] == "gid://shopify/Order/5876418969694"
        assert result["order_name"] == "#42305"

        # Check refund details
        refunds = result["refunds"]
        assert len(refunds) == 1

        refund = refunds[0]
        assert refund["id"] == "gid://shopify/Refund/123456789"
        assert (
            refund["total_refunded"] == "19.0"
        )  # Updated: now calculated from transactions
        assert refund["status"] == "completed"  # New: status field
        assert refund["status_display"] == "$19.00 (Completed)"  # New: display format
        assert refund["currency"] == "USD"
        assert refund["note"] == "Refund issued via Slack workflow for $19.00"

        # Check transaction details
        assert len(refund["transactions"]) == 1
        transaction = refund["transactions"][0]
        assert transaction["kind"] == "REFUND"
        assert transaction["status"] == "SUCCESS"
        assert transaction["amount"] == "19.00"

        # Check line items
        assert len(refund["line_items"]) == 1
        line_item = refund["line_items"][0]
        assert line_item["title"] == "Dodgeball - Open Registration"
        assert line_item["quantity"] == 1

    def test_check_existing_refunds_no_refunds(self):
        """Test check_existing_refunds when order has no existing refunds"""
        # Setup mock response
        self.mock_shopify_service._make_shopify_request.return_value = (
            self.sample_shopify_response_no_refunds
        )

        # Call the method
        result = self.orders_service.check_existing_refunds(self.sample_order_id)

        # Verify the result
        assert result["success"] is True
        assert result["has_refunds"] is False
        assert result["total_refunds"] == 0
        assert result["order_id"] == "gid://shopify/Order/5876418969694"
        assert result["order_name"] == "#42305"
        assert result["refunds"] == []

    def test_check_existing_refunds_api_failure(self):
        """Test check_existing_refunds when Shopify API fails"""
        # Setup mock to return None (API failure)
        self.mock_shopify_service._make_shopify_request.return_value = None

        # Call the method
        result = self.orders_service.check_existing_refunds(self.sample_order_id)

        # Verify the result
        assert result["success"] is False
        assert (
            "Failed to check existing refunds or order not found" in result["message"]
        )

    def test_check_existing_refunds_malformed_response(self):
        """Test check_existing_refunds when Shopify API returns malformed data"""
        # Setup mock to return malformed response
        self.mock_shopify_service._make_shopify_request.return_value = {
            "data": {"order": None}
        }

        # Call the method
        result = self.orders_service.check_existing_refunds(self.sample_order_id)

        # Verify the result
        assert result["success"] is False
        assert (
            "Failed to check existing refunds or order not found" in result["message"]
        )

    def test_build_duplicate_refund_message(self):
        """Test building a duplicate refund Slack message"""
        # Sample existing refunds data
        existing_refunds_data = {
            "success": True,
            "order_id": "gid://shopify/Order/5876418969694",
            "order_name": "#42305",
            "has_refunds": True,
            "total_refunds": 1,
            "refunds": [
                {
                    "id": "gid://shopify/Refund/123456789",
                    "total_refunded": "19.00",
                    "created_at": "2024-09-10T15:30:00Z",
                    "note": "Refund issued via Slack workflow for $19.00",
                }
            ],
        }

        # Sample order data
        order_data = {
            "order": {"id": "gid://shopify/Order/5876418969694", "name": "#42305"}
        }

        # Call the method
        result = self.message_builder.build_duplicate_refund_message(
            requestor_info=self.sample_requestor_info,
            raw_order_number="#42305",
            sheet_link="https://docs.google.com/spreadsheets/d/test",
            order_data=order_data,
            existing_refunds_data=existing_refunds_data,
        )

        # Verify the result
        assert "text" in result
        assert "action_buttons" in result
        assert "slack_text" in result

        # Check message content
        message_text = result["text"]
        assert "⚠️ *Refund request – Refund Already Processed*" in message_text
        assert "Joe Test" in message_text
        assert "joetest@example.com" in message_text
        assert "#42305" in message_text
        assert "already has 1 refund(s) processed" in message_text
        assert "$19.00, issued on 9/10/24" in message_text
        assert "*Total Already Refunded*: $19.00" in message_text

        # Check action buttons
        action_buttons = result["action_buttons"]
        assert len(action_buttons) == 2

        # Check update button
        update_button = action_buttons[0]
        assert update_button["text"]["text"] == "🔄 Update Request Details"
        assert (
            update_button["action_id"] == "edit_request_details"
        )  # Updated: same as email mismatch
        assert update_button["style"] == "primary"

        # Check deny button
        deny_button = action_buttons[1]
        assert deny_button["text"]["text"] == "❌ Deny Refund Request"
        assert deny_button["action_id"] == "deny_duplicate_refund_request"
        assert deny_button["style"] == "danger"
        assert "confirm" in deny_button

    def test_build_duplicate_refund_message_no_existing_data(self):
        """Test building duplicate refund message when existing_refunds_data is None"""
        # Call the method without existing refunds data
        result = self.message_builder.build_duplicate_refund_message(
            requestor_info=self.sample_requestor_info,
            raw_order_number="#42305",
            sheet_link="https://docs.google.com/spreadsheets/d/test",
            order_data=None,
            existing_refunds_data=None,
        )

        # Verify the result still works
        assert "text" in result
        assert "⚠️ *Refund request – Refund Already Processed*" in result["text"]
        assert "Joe Test" in result["text"]
        assert "#42305" in result["text"]
        assert "already has 0 refund(s) processed" in result["text"]

    def test_duplicate_refund_button_creation(self):
        """Test the creation of duplicate refund action buttons"""
        # Test update button creation
        update_button = self.message_builder._create_update_refund_details_button(
            order_name="42305",  # Test without # prefix
            requestor_name={"first": "Joe", "last": "Test"},
            requestor_email="joetest@example.com",
            refund_type="refund",
            current_time="09/10/24 at 3:30 PM",
        )

        assert update_button["text"]["text"] == "🔄 Update Request Details"
        assert update_button["action_id"] == "edit_request_details"
        assert update_button["style"] == "primary"
        assert "#42305" in update_button["value"]  # Should add # prefix
        assert "Joe Test" in update_button["value"]

        # Test deny button creation
        deny_button = self.message_builder._create_deny_duplicate_refund_button(
            order_name="#42305",  # Test with # prefix
            requestor_name={"first": "Joe", "last": "Test"},
            requestor_email="joetest@example.com",
            refund_type="credit",
            current_time="09/10/24 at 3:30 PM",
        )

        assert deny_button["text"]["text"] == "❌ Deny Refund Request"
        assert deny_button["action_id"] == "deny_duplicate_refund_request"
        assert deny_button["style"] == "danger"
        assert "confirm" in deny_button
        assert "#42305" in deny_button["value"]
        assert "Joe Test" in deny_button["value"]

        # Check confirmation dialog
        confirm = deny_button["confirm"]
        assert confirm["title"]["text"] == "Deny Refund Request?"
        assert "#42305" in confirm["text"]["text"]
        assert confirm["confirm"]["text"] == "Yes, deny request"
        assert confirm["deny"]["text"] == "Cancel"

    @patch("services.orders.orders_service.logger")
    def test_check_existing_refunds_exception_handling(self, mock_logger):
        """Test check_existing_refunds exception handling"""
        # Setup mock to raise an exception
        self.mock_shopify_service._make_shopify_request.side_effect = Exception(
            "API Error"
        )

        # Call the method
        result = self.orders_service.check_existing_refunds(self.sample_order_id)

        # Verify the result
        assert result["success"] is False
        assert "Error checking existing refunds: API Error" in result["message"]

        # Verify logging
        mock_logger.error.assert_called_once()
        assert "Error checking existing refunds for order" in str(
            mock_logger.error.call_args
        )

    def test_check_existing_refunds_with_pending_refund(self):
        """Test check_existing_refunds when order has pending refunds"""
        # Create sample response with pending refund
        sample_pending_response = {
            "data": {
                "order": {
                    "id": "gid://shopify/Order/5876418969694",
                    "name": "#42305",
                    "refunds": [
                        {
                            "createdAt": "2024-09-10T15:30:00Z",
                            "id": "gid://shopify/Refund/123456789",
                            "legacyResourceId": "123456789",
                            "note": "Refund issued via Slack workflow for $19.00",
                            "totalRefundedSet": {
                                "presentmentMoney": {
                                    "amount": "0.00",  # Pending refunds show 0 here
                                    "currencyCode": "USD",
                                }
                            },
                            "updatedAt": "2024-09-10T15:30:00Z",
                            "staffMember": None,
                            "transactions": {
                                "edges": [
                                    {
                                        "node": {
                                            "id": "gid://shopify/OrderTransaction/123456",
                                            "kind": "REFUND",
                                            "status": "PENDING",  # This makes it pending
                                            "amount": "19.00",  # Actual amount from transaction
                                            "gateway": "shopify_payments",
                                            "createdAt": "2024-09-10T15:30:00Z",
                                        }
                                    }
                                ]
                            },
                            "refundLineItems": {"edges": []},
                        }
                    ],
                }
            }
        }

        # Setup mock response
        self.mock_shopify_service._make_shopify_request.return_value = (
            sample_pending_response
        )

        # Call the method
        result = self.orders_service.check_existing_refunds(self.sample_order_id)

        # Verify the result
        assert result["success"] is True
        assert result["has_refunds"] is True
        assert result["total_refunds"] == 1

        # Check pending refund details
        refunds = result["refunds"]
        assert len(refunds) == 1

        refund = refunds[0]
        assert refund["id"] == "gid://shopify/Refund/123456789"
        assert refund["total_refunded"] == "19.0"  # Calculated from pending transaction
        assert refund["status"] == "pending"  # Should be pending
        assert refund["status_display"] == "$19.00 (Pending)"  # Should show as pending
        assert refund["pending_amount"] == 19.0
        assert refund["completed_amount"] == 0.0

        # Check transaction details
        assert len(refund["transactions"]) == 1
        transaction = refund["transactions"][0]
        assert transaction["kind"] == "REFUND"
        assert transaction["status"] == "PENDING"
        assert transaction["amount"] == "19.00"
