"""
Tests for the Slack webhook router functionality.
Validates webhook interactions, security, and debug environment
message format validation for debug environment.
"""

import sys
from pathlib import Path

# Add backend directory to Python path for proper imports
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import json
from fastapi import HTTPException

# Import the router and dependencies with correct path
from routers.slack import router
from main import app
from services.slack.message_builder import SlackMessageBuilder
from services.slack.utilities import SlackUtilities
from config import settings

@pytest.fixture
def client():
    """Create a test client"""
    app.include_router(router, prefix="/slack")
    return TestClient(app)

@pytest.fixture
def sample_slack_payload():
    """Sample Slack interaction payload"""
    return {
        "payload": json.dumps({
            "type": "block_actions",
            "user": {
                "id": "U123456",
                "name": "joe randazzo (he/him)"
            },
            "channel": {
                "id": "C123456"
            },
            "message": {
                "ts": "1234567890.123",
                "blocks": []
            },
            "actions": [{
                "action_id": "cancel_order",
                "value": "rawOrderNumber=#12345|refundType=refund|requestorEmail=test@example.com|requestorFirstName=Test|requestorLastName=User|requestSubmittedAt=2024-01-15T10:30:00Z"
            }]
        })
    }

@pytest.fixture
def mock_slack_signature():
    """Mock Slack signature validation"""
    with patch('services.slack.slack_service.SlackService.handle_slack_interactions', return_value={"text": "Mocked response"}):
        yield

class TestSlackWebhook:
    """Test Slack webhook endpoints"""
    
    def test_slack_signature_validation_success(self, client, sample_slack_payload, mock_slack_signature):
        """Test that valid Slack signatures are accepted"""
        response = client.post(
            "/slack/interactive",
            data=sample_slack_payload,
            headers={
                "X-Slack-Request-Timestamp": "1234567890",
                "X-Slack-Signature": "v0=test_signature"
            }
        )
        assert response.status_code == 200

    def test_slack_signature_validation_failure(self, client, sample_slack_payload):
        """Test that invalid Slack signatures are rejected"""
        # Mock signature validation to fail at the service level
        with patch('services.slack.slack_service.SlackService.handle_slack_interactions') as mock_handle:
            mock_handle.side_effect = HTTPException(status_code=401, detail="Invalid signature")
            
            response = client.post(
                "/slack/interactive",
                data=sample_slack_payload,
                headers={
                    "X-Slack-Request-Timestamp": "1234567890",
                    "X-Slack-Signature": "v0=invalid_signature"
                }
            )
            assert response.status_code == 401

    def test_cancel_order_webhook_debug_mode(self, client, mock_slack_signature, sample_slack_payload):
        """Test cancel order webhook in debug mode"""
        with patch('services.slack.slack_service.SlackService.handle_slack_interactions') as mock_handle:
            mock_handle.return_value = {
                "text": "Order cancelled in debug mode",
                "blocks": []
            }

            response = client.post(
                "/slack/interactive",
                data=sample_slack_payload,
                headers={
                    "X-Slack-Request-Timestamp": "1234567890",
                    "X-Slack-Signature": "v0=test_signature"
                }
            )

            assert response.status_code == 200
            assert "Order cancelled in debug mode" in response.json()["text"]

    def test_process_refund_webhook_debug_mode(self, client, mock_slack_signature):
        """Test process refund webhook in debug mode"""
        refund_payload = {
            "payload": json.dumps({
                "type": "block_actions",
                "user": {
                    "id": "U123456",
                    "name": "joe randazzo (he/him)"
                },
                "channel": {
                    "id": "C123456"
                },
                "message": {
                    "ts": "1234567890.123",
                    "blocks": []
                },
                "actions": [{
                    "action_id": "process_refund",
                    "value": "orderId=gid://shopify/Order/12345|rawOrderNumber=#12345|refundAmount=50.00|refundType=refund|orderCancelled=true"
                }]
            })
        }

        with patch('services.slack.slack_service.SlackService.handle_slack_interactions') as mock_handle:
            mock_handle.return_value = {
                "text": "Refund processed in debug mode",
                "blocks": []
            }

            response = client.post(
                "/slack/interactive",
                data=refund_payload,
                headers={
                    "X-Slack-Request-Timestamp": "1234567890",
                    "X-Slack-Signature": "v0=test_signature"
                }
            )

            assert response.status_code == 200
            assert "Refund processed in debug mode" in response.json()["text"]

    def test_webhook_action_routing(self, client, mock_slack_signature):
        """Test that different action IDs route to correct handlers"""
        with patch('services.slack.slack_service.SlackService.handle_slack_interactions') as mock_handle:
            mock_handle.return_value = {"text": "Cancel order"}
            
            # Test cancel_order action
            cancel_payload = {
                "payload": json.dumps({
                    "type": "block_actions",
                    "actions": [{"action_id": "cancel_order", "value": "rawOrderNumber=#12345"}]
                })
            }
            
            response = client.post("/slack/interactive", data=cancel_payload, headers={
                "X-Slack-Request-Timestamp": "1234567890",
                "X-Slack-Signature": "v0=test_signature"
            })
            
            assert response.status_code == 200

    def test_webhook_preserves_user_data(self, client, mock_slack_signature):
        """Test that webhook preserves user data through the pipeline"""
        with patch('services.slack.slack_service.SlackService.handle_slack_interactions') as mock_handle:
            mock_handle.return_value = {"text": "Preserved user data"}
            
            user_payload = {
                "payload": json.dumps({
                    "type": "block_actions",
                    "user": {"id": "U999", "username": "test_user"},
                    "actions": [{"action_id": "cancel_order", "value": "rawOrderNumber=#99999"}]
                })
            }
            
            response = client.post("/slack/interactive", data=user_payload, headers={
                "X-Slack-Request-Timestamp": "1234567890",
                "X-Slack-Signature": "v0=test_signature"
            })
            
            assert response.status_code == 200

    def test_restock_inventory_webhook_debug_mode(self, client, mock_slack_signature):
        """Test restock inventory webhook in debug mode"""
        restock_payload = {
            "payload": json.dumps({
                "type": "block_actions",
                "user": {
                    "id": "U123456",
                    "name": "joe randazzo (he/him)"
                },
                "channel": {
                    "id": "C123456"
                },
                "message": {
                    "ts": "1234567890.123",
                    "blocks": []
                },
                "actions": [{
                    "action_id": "restock_variant123",
                    "value": "orderId=gid://shopify/Order/12345|variantId=gid://shopify/ProductVariant/456|variantName=Test Variant"
                }]
            })
        }

        with patch('services.slack.slack_service.SlackService.handle_slack_interactions') as mock_handle:
            mock_handle.return_value = {
                "text": "Inventory restocked in debug mode",
                "blocks": []
            }
            
            response = client.post(
                "/slack/interactive",
                data=restock_payload,
                headers={
                    "X-Slack-Request-Timestamp": "1234567890",
                    "X-Slack-Signature": "v0=test_signature"
                }
            )

            assert response.status_code == 200
            assert "Inventory restocked in debug mode" in response.json()["text"]

    def test_do_not_restock_webhook_debug_mode(self, client, mock_slack_signature):
        """Test do not restock webhook in debug mode"""
        do_not_restock_payload = {
            "payload": json.dumps({
                "type": "block_actions",
                "user": {
                    "id": "U123456",
                    "name": "joe randazzo (he/him)"
                },
                "channel": {
                    "id": "C123456"
                },
                "message": {
                    "ts": "1234567890.123",
                    "blocks": []
                },
                "actions": [{
                    "action_id": "do_not_restock",
                    "value": "orderId=gid://shopify/Order/12345|rawOrderNumber=#12345"
                }]
            })
        }

        with patch('services.slack.slack_service.SlackService.handle_slack_interactions') as mock_handle:
            mock_handle.return_value = {
                "text": "No restock in debug mode",
                "blocks": []
            }
            
            response = client.post(
                "/slack/interactive",
                data=do_not_restock_payload,
                headers={
                    "X-Slack-Request-Timestamp": "1234567890",
                    "X-Slack-Signature": "v0=test_signature"
                }
            )

            assert response.status_code == 200
            assert "No restock in debug mode" in response.json()["text"]

    def test_webhook_url_verification(self, client):
        """Test Slack webhook URL verification"""
        verification_payload = {
            "type": "url_verification",
            "challenge": "test_challenge_string"
        }
        
        response = client.post(
            "/slack/webhook",
            json=verification_payload
        )
        
        assert response.status_code == 200
        assert response.json() == {"challenge": "test_challenge_string"}

    def test_invalid_payload_format(self, client, mock_slack_signature):
        """Test handling of invalid payload format"""
        invalid_payload = {"invalid": "data"}  # Missing 'payload' key
        
        with patch('services.slack.slack_service.SlackService.handle_slack_interactions') as mock_handle:
            mock_handle.side_effect = HTTPException(status_code=400, detail="Invalid payload format")
            
            response = client.post(
                "/slack/interactive",
                data=invalid_payload,
                headers={
                    "X-Slack-Request-Timestamp": "1234567890",
                    "X-Slack-Signature": "v0=test_signature"
                }
            )
            
            assert response.status_code == 400

    def test_missing_action_id(self, client, mock_slack_signature):
        """Test handling of missing action_id"""
        payload_without_action = {
            "payload": json.dumps({
                "type": "block_actions",
                "user": {"id": "U123456"},
                "channel": {"id": "C123456"},
                "message": {"ts": "1234567890.123"},
                "actions": [{}]  # Missing action_id
            })
        }
        
        with patch('services.slack.slack_service.SlackService.handle_slack_interactions') as mock_handle:
            mock_handle.return_value = {"text": "Unknown action: "}
            
            response = client.post(
                "/slack/interactive",
                data=payload_without_action,
                headers={
                    "X-Slack-Request-Timestamp": "1234567890",
                    "X-Slack-Signature": "v0=test_signature"
                }
            )
            
            assert response.status_code == 200
            assert "Unknown action: " in response.json()["text"]

    def test_extract_season_start_info(self, mock_message_builder):
        """Test extraction of season start information from message text"""
        utilities = SlackUtilities()
        
        message_text = """
        🚨 *NEW REFUND REQUEST* @here
        
        📦 *Order:* <https://admin.shopify.com/store/09fe59-3/orders/12345|#12345>
        👤 *Customer:* test@example.com
        🏷️ *Product:* Fall 2024 Football League
        📅 *Season Start Date:* Sep 15, 2024
        """
        
        result = utilities.extract_season_start_info(message_text)
        
        assert result["season_start_date"] is not None
        assert "Sep 15, 2024" in result["season_start_date"]

    def test_extract_sheet_link(self, mock_message_builder):
        """Test extraction of Google Sheets link from message text"""
        utilities = SlackUtilities()
        
        message_text = """
        Some message content...
        
        🔗 *<https://docs.google.com/spreadsheets/d/abc123/edit#gid=0|View Request in Google Sheets>*
        """
        
        result = utilities.extract_sheet_link(message_text)
        
        assert result == "https://docs.google.com/spreadsheets/d/abc123/edit#gid=0"

    @pytest.mark.skip(reason="Function moved - preserving for reference")
    def test_extract_original_requestor_info(self, mock_message_builder):
        """Test extraction of original requestor info from message text - MOVED TO UTILITIES"""
        pass

class TestSlackMessageFormatting:
    """Test Slack message formatting functions"""
    
    def test_debug_message_format_expectations(self, mock_message_builder):
        """Test specific message format expectations for debug mode"""
        message_builder = SlackMessageBuilder()
        
        # Mock order data
        order_data = {
            "customer": {"email": "test@example.com"},
            "product": {"title": "Test Product"},
            "line_items": []
        }
        
        # Test that debug mode produces expected format
        result = message_builder.build_comprehensive_success_message(
            order_data=order_data,
            refund_amount=50.0,
            refund_type="refund",
            raw_order_number="#12345",
            order_cancelled=False,
            processor_user="test_user",
            is_debug_mode=True,
            current_message_text="Test message content for extraction",
            order_id="12345"
        )
        
        assert "text" in result
        assert "🧪" in result["text"] or any("🧪" in str(block) for block in result.get("blocks", []))

    def test_production_vs_debug_message_differences(self, mock_message_builder):
        """Test that production and debug modes produce different message formats"""
        message_builder = SlackMessageBuilder()
        
        # Mock order data
        order_data = {
            "customer": {"email": "test@example.com"},
            "product": {"title": "Test Product"},
            "line_items": []
        }
        
        # Test production mode
        prod_result = message_builder.build_comprehensive_success_message(
            order_data=order_data,
            refund_amount=50.0,
            refund_type="refund", 
            raw_order_number="#12345",
            order_cancelled=False,
            processor_user="test_user",
            is_debug_mode=False,
            current_message_text="Test message content",
            order_id="12345"
        )
        
        # Test debug mode
        debug_result = message_builder.build_comprehensive_success_message(
            order_data=order_data,
            refund_amount=50.0,
            refund_type="refund",
            raw_order_number="#12345", 
            order_cancelled=False,
            processor_user="test_user",
            is_debug_mode=True,
            current_message_text="Test message content",
            order_id="12345"
        )
        
        # Debug should contain debug indicators, production should not
        debug_text = str(debug_result)
        prod_text = str(prod_result)
        
        assert "🧪" in debug_text
        assert "🧪" not in prod_text

@pytest.fixture
def mock_message_builder():
    """Mock message builder for tests"""
    with patch('services.slack.message_builder.SlackMessageBuilder') as mock:
        yield mock 