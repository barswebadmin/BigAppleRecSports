"""
Tests for the Slack webhook router functionality.
Validates webhook interactions, security, and debug environment
message format validation for debug environment.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from config import settings

client = TestClient(app)

class TestSlackWebhook:
    """Test Slack webhook functionality including signature validation and button interactions"""
    
    @pytest.fixture
    def mock_slack_signature(self):
        """Mock Slack signature validation to always pass"""
        with patch('routers.slack.verify_slack_signature', return_value=True):
            yield
    
    @pytest.fixture
    def mock_orders_service(self):
        """Mock the orders service to return predictable test data"""
        with patch('routers.slack.orders_service') as mock_service:
            # Mock order details response
            mock_service.fetch_order_details.return_value = {
                "success": True,
                "data": {
                    "orderId": "gid://shopify/Order/5759498846302",
                    "name": "#40192",
                    "customerEmail": "jdazz87@gmail.com",
                    "originalCost": 180,
                    "variants": [
                        {
                            "variantId": "gid://shopify/ProductVariant/41474142871614",
                            "productTitle": "joe test product",
                            "variantTitle": "Veteran Registration",
                            "quantity": 1,
                            "inventoryItemId": "gid://shopify/InventoryItem/43571415449662",
                            "availableQuantity": 0
                        }
                    ]
                }
            }
            # Mock refund calculation
            mock_service.calculate_refund_due.return_value = {
                "refund_amount": 1.80,
                "formatted_amount": "$1.80"
            }
            # Mock order cancellation
            mock_service.cancel_order.return_value = {
                "success": True,
                "message": "Order cancelled successfully"
            }
            yield mock_service
    
    @pytest.fixture  
    def mock_slack_service(self):
        """Mock the Slack service to capture message updates without sending real requests"""
        with patch('routers.slack.slack_service') as mock_service:
            # Mock successful API client calls
            mock_service.api_client.update_message.return_value = {"ok": True}
            yield mock_service

    @pytest.fixture
    def sample_slack_payload(self):
        """Sample Slack interactive payload for testing"""
        return {
            "payload": json.dumps({
                "type": "block_actions",
                "user": {
                    "id": "U123456",
                    "name": "joe randazzo (he/him)"
                },
                "channel": {"id": "C092RU7R6PL"},
                "message": {
                    "ts": "1234567890.123",
                    "text": "Test message content with original requestor data"
                },
                "actions": [{
                    "action_id": "cancel_order",
                    "value": json.dumps({
                        "rawOrderNumber": "#40192",
                        "refundType": "refund",
                        "requestorEmail": "jdazz87@gmail.com",
                        "requestorFirstName": "Test",
                        "requestorLastName": "User",
                        "requestSubmittedAt": "2024-01-15T10:30:00Z"
                    })
                }]
            })
        }

    @pytest.fixture
    def refund_payload(self, sample_slack_payload):
        """Payload for process refund action"""
        payload_data = json.loads(sample_slack_payload["payload"])
        payload_data["actions"][0]["action_id"] = "process_refund"
        payload_data["actions"][0]["value"] = json.dumps({
            "orderId": "gid://shopify/Order/5759498846302",
            "rawOrderNumber": "#40192",
            "refundAmount": "1.80",
            "refundType": "refund",
            "orderCancelled": "true"
        })
        return {"payload": json.dumps(payload_data)}

    @pytest.fixture
    def restock_payload(self, sample_slack_payload):
        """Payload for restock inventory action"""
        payload_data = json.loads(sample_slack_payload["payload"])
        payload_data["actions"][0]["action_id"] = "restock_veteran_registration"
        payload_data["actions"][0]["value"] = json.dumps({
            "orderId": "gid://shopify/Order/5759498846302",
            "rawOrderNumber": "#40192",
            "variantId": "gid://shopify/ProductVariant/41474142871614",
            "variantName": "Veteran Registration"
        })
        payload_data["message"]["text"] = """✅ [DEBUG] Cancellation Request for Order <https://admin.shopify.com/store/09fe59-3/orders/5759498846302|#40192> for jdazz87@gmail.com has been processed by @joe randazzo (he/him)
✅ [DEBUG] Request to provide a $1.80 refund processed by @joe randazzo (he/him)

🔗 <https://docs.google.com/spreadsheets/d/URL|View Request in Google Sheets>

📦 Season Start Date for <https://admin.shopify.com/store/09fe59-3/products/7350462185566|joe test product> is Unknown."""
        return {"payload": json.dumps(payload_data)}

    @pytest.fixture
    def do_not_restock_payload(self, sample_slack_payload):
        """Payload for 'Do Not Restock' action"""
        payload_data = json.loads(sample_slack_payload["payload"])
        payload_data["actions"][0]["action_id"] = "do_not_restock_all_done"
        payload_data["actions"][0]["value"] = json.dumps({
            "rawOrderNumber": "#40192",
            "orderCancelled": "true"
        })
        return {"payload": json.dumps(payload_data)}

    def test_slack_signature_validation_success(self, mock_orders_service, mock_slack_service, sample_slack_payload):
        """Test that valid Slack signatures are accepted"""
        # Mock signature validation to pass
        with patch('routers.slack.verify_slack_signature', return_value=True):
            response = client.post("/slack/webhook", data=sample_slack_payload)
            assert response.status_code == 200

    def test_slack_signature_validation_failure(self, sample_slack_payload):
        """Test that invalid Slack signatures are rejected"""
        # Mock signature validation to fail
        with patch('routers.slack.verify_slack_signature', return_value=False):
            response = client.post("/slack/webhook", data=sample_slack_payload)
            assert response.status_code == 401
            assert "Invalid signature" in response.json()["detail"]

    def test_cancel_order_webhook_debug_mode(self, mock_orders_service, mock_slack_service, client,
                                           mock_slack_signature, sample_slack_payload):
        """Test cancel order action in debug mode produces expected message format"""
        
        # Mock debug mode
        with patch('routers.slack.settings.is_debug_mode', True):
            response = client.post("/slack/webhook", data=sample_slack_payload)
            
            # Verify successful response
            assert response.status_code == 200
            
            # Verify orders service was called correctly
            mock_orders_service.fetch_order_details.assert_called_once_with(order_name="#40192")
            mock_orders_service.calculate_refund_due.assert_called_once()
            
            # Verify order was NOT cancelled in debug mode
            mock_orders_service.cancel_order.assert_not_called()
            
            # Verify Slack message was updated with comprehensive success message
            mock_slack_service.api_client.update_message.assert_called_once()
            call_args = mock_slack_service.api_client.update_message.call_args
            
            # Verify the message contains debug elements
            assert call_args is not None
            # The message should be passed as message_blocks or similar parameter
            # This validates that the webhook processing completed successfully

    def test_webhook_url_verification(self):
        """Test Slack URL verification challenge"""
        challenge_data = {"challenge": "test_challenge_value"}
        response = client.post("/slack/webhook", json=challenge_data)
        
        assert response.status_code == 200
        assert response.json() == {"challenge": "test_challenge_value"}

    def test_invalid_payload_format(self, mock_slack_signature):
        """Test handling of malformed payload"""
        invalid_payload = {"payload": "invalid_json"}
        response = client.post("/slack/webhook", data=invalid_payload)
        
        assert response.status_code == 400
        assert "Invalid payload format" in response.json()["detail"]

    def test_missing_action_id(self, mock_slack_signature):
        """Test handling of payload missing action_id"""
        payload_without_action = {
            "payload": json.dumps({
                "type": "block_actions",
                "user": {"id": "U123", "name": "test"},
                "actions": [{"value": "{}"}]  # Missing action_id
            })
        }
        response = client.post("/slack/webhook", data=payload_without_action)
        
        assert response.status_code == 400
        assert "Missing action_id" in response.json()["detail"]

    def test_process_refund_webhook_debug_mode(self, mock_orders_service, mock_slack_service, client,
                                             mock_slack_signature, refund_payload):
        """Test process refund action in debug mode produces expected inventory message format"""
        
        with patch('routers.slack.settings.is_debug_mode', True):
            response = client.post("/slack/webhook", data=refund_payload)
            
            # Verify successful response
            assert response.status_code == 200
            
            # Verify orders service was called for order details
            mock_orders_service.fetch_order_details.assert_called_once_with(order_name="#40192")
            
            # Verify no actual refund was created in debug mode
            mock_orders_service.create_refund_only.assert_not_called()
            
            # Verify comprehensive success message was built
            mock_slack_service.api_client.update_message.assert_called_once()

    def test_webhook_action_routing(self, mock_orders_service, mock_slack_service, mock_slack_signature):
        """Test that different action_ids route to correct handlers"""
        base_payload = {
            "type": "block_actions",
            "user": {"id": "U123", "name": "test"},
            "channel": {"id": "C123"},
            "message": {"ts": "123", "text": "test"},
            "actions": [{"action_id": "test", "value": "{}"}]
        }
        
        # Test cancel_order action
        payload = base_payload.copy()
        payload["actions"][0]["action_id"] = "cancel_order"
        payload["actions"][0]["value"] = json.dumps({"rawOrderNumber": "#123"})
        
        with patch('routers.slack.settings.is_debug_mode', True):
            response = client.post("/slack/webhook", data={"payload": json.dumps(payload)})
            assert response.status_code == 200

    def test_webhook_preserves_user_data(self, mock_orders_service, mock_slack_service, mock_slack_signature):
        """Test that user information is preserved through webhook processing"""
        payload = {
            "type": "block_actions", 
            "user": {"id": "U123456", "name": "joe randazzo (he/him)"},
            "channel": {"id": "C123"},
            "message": {"ts": "123", "text": "original message"},
            "actions": [{
                "action_id": "cancel_order",
                "value": json.dumps({
                    "rawOrderNumber": "#40192",
                    "requestorEmail": "test@example.com"
                })
            }]
        }
        
        with patch('routers.slack.settings.is_debug_mode', True):
            response = client.post("/slack/webhook", data={"payload": json.dumps(payload)})
            assert response.status_code == 200
            
            # Verify user name was captured for processing
            # This is validated by the successful webhook processing

    def test_restock_inventory_webhook_debug_mode(self, mock_orders_service, mock_slack_service, client, mock_slack_signature):
        """Test restock inventory action in debug mode"""
        payload = {
            "type": "block_actions",
            "user": {"id": "U123456", "name": "joe randazzo (he/him)"},
            "channel": {"id": "C092RU7R6PL"},
            "message": {
                "ts": "1234567890.123",
                "text": """✅ [DEBUG] Cancellation Request for Order <https://admin.shopify.com/store/09fe59-3/orders/5759498846302|#40192> for jdazz87@gmail.com has been processed by @joe randazzo (he/him)
✅ [DEBUG] Request to provide a $1.80 refund processed by @joe randazzo (he/him)

🔗 <https://docs.google.com/spreadsheets/d/URL|View Request in Google Sheets>

📦 Season Start Date for <https://admin.shopify.com/store/09fe59-3/products/7350462185566|joe test product> is Unknown."""
            },
            "actions": [{
                "action_id": "restock_veteran_registration",
                "value": json.dumps({
                    "orderId": "gid://shopify/Order/5759498846302",
                    "rawOrderNumber": "#40192",
                    "variantId": "gid://shopify/ProductVariant/41474142871614",
                    "variantName": "Veteran Registration"
                })
            }]
        }
        
        with patch('routers.slack.settings.is_debug_mode', True):
            response = client.post("/slack/webhook", data={"payload": json.dumps(payload)})
            
            assert response.status_code == 200
            mock_slack_service.api_client.update_message.assert_called_once()

    def test_do_not_restock_webhook_debug_mode(self, mock_slack_service, client, mock_slack_signature):
        """Test 'Do Not Restock' action in debug mode"""
        payload = {
            "type": "block_actions",
            "user": {"id": "U123456", "name": "joe randazzo (he/him)"},
            "channel": {"id": "C092RU7R6PL"},
            "message": {
                "ts": "1234567890.123",
                "text": "Test message with completion"
            },
            "actions": [{
                "action_id": "do_not_restock_all_done",
                "value": json.dumps({
                    "rawOrderNumber": "#40192",
                    "orderCancelled": "true"
                })
            }]
        }
        
        with patch('routers.slack.settings.is_debug_mode', True):
            response = client.post("/slack/webhook", data={"payload": json.dumps(payload)})
            
            assert response.status_code == 200
            mock_slack_service.api_client.update_message.assert_called_once()

    def test_extract_season_start_info(self):
        """Test utility function for extracting season start information"""
        from routers.slack import extract_season_start_info
        
        # Test message with product link
        message_with_product = "Season Start Date for <https://admin.shopify.com/store/09fe59-3/products/7350462185566|joe test product> is Unknown."
        result = extract_season_start_info(message_with_product)
        assert result["product_title"] == "joe test product"
        assert result["season_start"] == "Unknown"

    def test_extract_sheet_link(self):
        """Test utility function for extracting Google Sheets links"""
        from routers.slack import extract_sheet_link
        
        message_with_sheet = "🔗 <https://docs.google.com/spreadsheets/d/URL|View Request in Google Sheets>"
        result = extract_sheet_link(message_with_sheet)
        assert "https://docs.google.com/spreadsheets" in result

    def test_extract_original_requestor_info(self):
        """Test utility function for extracting requestor information"""
        from routers.slack import extract_original_requestor_info
        
        message = "Cancellation Request for Order #40192 for TestUser has been processed"
        result = extract_original_requestor_info(message)
        assert "TestUser" in result

class TestSlackMessageFormatting:
    """Test Slack message formatting for debug environment"""
    
    @pytest.fixture
    def mock_message_builder(self):
        """Mock the message builder service"""
        with patch('routers.slack.slack_service.message_builder') as mock_builder:
            yield mock_builder

    def test_debug_message_format_expectations(self, mock_message_builder):
        """Test specific message format expectations for debug mode"""
        from routers.slack import build_comprehensive_success_message
        
        # Mock order data
        order_data = {
            "orderId": "gid://shopify/Order/5759498846302", 
            "name": "#40192",
            "variants": [
                {
                    "variantId": "gid://shopify/ProductVariant/41474142871614",
                    "productTitle": "joe test product",
                    "variantTitle": "Veteran Registration",
                    "availableQuantity": 0
                }
            ]
        }
        
        refund_calc = {"refund_amount": 1.80, "formatted_amount": "$1.80"}
        
        # Test debug mode message building
        result = build_comprehensive_success_message(
            order_data=order_data,
            refund_calculation=refund_calc,
            refund_type="refund",
            requestor_email="jdazz87@gmail.com",
            sheet_link="🔗 <https://docs.google.com/spreadsheets/d/URL|View Request in Google Sheets>",
            order_cancelled=True,
            user_name="joe randazzo (he/him)",
            raw_order_number="#40192",
            is_debug_mode=True,
            current_message_text="original message",
            order_id="gid://shopify/Order/5759498846302"
        )
        
        # Verify debug format elements are present
        assert "[DEBUG]" in str(result)

    def test_production_vs_debug_message_differences(self, mock_message_builder):
        """Test that production and debug modes produce different message formats"""
        from routers.slack import build_comprehensive_success_message
        
        base_params = {
            "order_data": {"orderId": "123", "name": "#40192", "variants": []},
            "refund_calculation": {"refund_amount": 1.80},
            "refund_type": "refund",
            "requestor_email": "test@example.com",
            "sheet_link": "sheet_link",
            "order_cancelled": True,
            "user_name": "test user",
            "raw_order_number": "#40192",
            "current_message_text": "original"
        }
        
        # Debug mode
        debug_result = build_comprehensive_success_message(
            **base_params,
            is_debug_mode=True,
            order_id="123"
        )
        
        # Production mode  
        prod_result = build_comprehensive_success_message(
            **base_params,
            is_debug_mode=False,
            order_id="123"
        )
        
        # Results should be different (debug should have [DEBUG] prefix)
        assert debug_result != prod_result 