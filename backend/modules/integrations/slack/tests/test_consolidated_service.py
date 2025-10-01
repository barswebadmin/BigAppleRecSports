#!/usr/bin/env python3
"""
Test script for the consolidated SlackOrchestrator.
Tests both low-level API methods and high-level business logic.
"""

import sys
import os

# Set environment to dev to avoid Shopify token validation
os.environ["ENVIRONMENT"] = "dev"

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.integrations.slack.slack_orchestrator import SlackOrchestrator
from models.slack import Slack, RefundType, SlackMessageType
from modules.integrations.slack.slack_config import SlackConfig

def test_consolidated_slack_service():
    """Test the consolidated Slack service functionality"""
    
    print("🧪 Testing Consolidated SlackOrchestrator")
    print("=" * 50)
    
    # Initialize service
    slack_orchestrator = SlackOrchestrator()
    print(f"✅ Service initialized for {slack_orchestrator.environment} environment")
    print(f"📺 Default channel: {slack_orchestrator._get_default_channel()}")
    print(f"🏃 Sport groups: {len(slack_orchestrator._get_sport_groups())} configured")
    print()
    
    # Test 1: Low-level API methods
    print("🔧 Testing Low-level API Methods:")
    
    # Test send_message
    result = service.send_message(
        channel_id=SlackConfig.Channel.JoeTest,
        message_text="Test message from consolidated service",
        slack_text="Test message"
    )
    print(f"✅ send_message result: {result['success']}")
    
    # Test send_message_with_mentions
    result = service.send_message_with_mentions(
        channel=SlackConfig.Channel.JoeTest,
        message_text="Test message with mentions",
        users=[SlackConfig.User.Joe],
        groups=[SlackConfig.Group.Dodgeball]
    )
    print(f"✅ send_message_with_mentions result: {result['success']}")
    
    # Test update_message
    result = service.update_message(
        channel_id=SlackConfig.Channel.JoeTest,
        message_ts="1234567890.123456",
        message_text="Updated test message",
        slack_text="Updated message"
    )
    print(f"✅ update_message result: {result['success']}")
    
    # Test send_ephemeral_message
    result = service.send_ephemeral_message(
        channel_id=SlackConfig.Channel.JoeTest,
        user_id="U0278M72535",
        message_text="Ephemeral test message",
        slack_text="Ephemeral message"
    )
    print(f"✅ send_ephemeral_message result: {result['success']}")
    print()
    
    # Test 2: Custom message crafting
    print("🎨 Testing Custom Message Crafting:")
    
    # Test custom message with mentions at bottom
    result = service.send_custom_message(
        channel=SlackConfig.Channel.JoeTest,
        message_text="💰 *Custom Refund Message*\n\n**Order:** #12345\n**Amount:** $25.00",
        mention_users=[SlackConfig.User.Joe],
        mention_groups=[SlackConfig.Group.Dodgeball],
        mention_block_position="bottom",
        action_buttons=[
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Approve"},
                "action_id": "approve_refund",
                "value": "#12345",
                "style": "primary"
            }
        ]
    )
    print(f"✅ Custom message with mentions at bottom: {result['success']}")
    
    # Test custom message with mentions at top
    result = service.send_custom_message(
        channel=SlackConfig.Channel.JoeTest,
        message_text="📦 *Order Update*\n\n**Order:** #67890\n**Status:** Shipped",
        mention_users=[SlackConfig.User.Joe],
        mention_block_position="top"
    )
    print(f"✅ Custom message with mentions at top: {result['success']}")
    print()
    
    # Test 3: Business logic methods
    print("💼 Testing Business Logic Methods:")
    
    # Test refund notification
    refund_request = Slack.RefundNotification(
        order_number="#12345",
        requestor_name="John Doe",
        requestor_email="john.doe@example.com",
        refund_type=RefundType.REFUND,
        notes="Customer requested refund"
    )
    
    order_data = {
        "order": {
            "orderNumber": "#12345",
            "orderName": "#12345",
            "lineItems": {
                "edges": [
                    {
                        "node": {
                            "title": "Summer Kickball League"
                        }
                    }
                ]
            }
        }
    }
    
    result = service.send_refund_notification(
        refund_request=refund_request,
        order_data=order_data,
        mention_users=[SlackConfig.User.Joe],
        mention_groups=[SlackConfig.Group.Kickball]
    )
    print(f"✅ Refund notification result: {result['success']}")
    print()
    
    # Test 4: Backward compatibility
    print("🔄 Testing Backward Compatibility:")
    
    result = service.send_refund_request_notification(
        requestor_info={"name": "John", "email": "john@example.com", "refund_type": "refund"},
        sheet_link="https://docs.google.com/spreadsheets/d/example",
        order_data=order_data,
        slack_channel_name="joe-test",
        mention_strategy="sportAliases"
    )
    print(f"✅ Backward compatibility result: {result['success']}")
    print()
    
    # Test 5: Utility methods
    print("🛠️ Testing Utility Methods:")
    
    sport_mention = service.get_sport_group_mention("Summer Kickball League")
    print(f"✅ Sport group mention: {sport_mention}")
    
    order_url = service.get_order_url("gid://shopify/Order/12345", "#12345")
    print(f"✅ Order URL: {order_url}")
    
    product_url = service.get_product_url("gid://shopify/Product/67890")
    print(f"✅ Product URL: {product_url}")
    
    button_data = service.parse_button_value("rawOrderNumber=#12345|orderId=gid://shopify/Order/12345|refundAmount=36.00")
    print(f"✅ Button parsing: {button_data}")
    print()
    
    print("=" * 50)
    print("✅ Consolidated SlackOrchestrator Test Completed!")

def demonstrate_usage_examples():
    """Demonstrate usage examples for the consolidated service"""
    
    print("\n📚 Consolidated Service Usage Examples")
    print("=" * 50)
    
    print("""
# Example 1: Low-level API usage
service = SlackOrchestrator()

# Send a simple message
result = service.send_message(
    channel_id=SlackConfig.Channel.RefundRequests,
    message_text="New refund request received",
    slack_text="Refund request"
)

# Send message with mentions
result = service.send_message_with_mentions(
    channel=SlackConfig.Channel.JoeTest,
    message_text="Please review this refund",
    users=[SlackConfig.User.Joe],
    groups=[SlackConfig.Group.Dodgeball]
)

# Update an existing message
result = service.update_message(
    channel_id=SlackConfig.Channel.RefundRequests,
    message_ts="1234567890.123456",
    message_text="Refund request processed",
    action_buttons=[
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "View Details"},
            "action_id": "view_details",
            "value": "#12345"
        }
    ]
)

# Example 2: Custom message crafting
result = service.send_custom_message(
    channel=SlackConfig.Channel.RefundRequests,
    message_text="💰 *Refund Request Processed*\\n\\n**Order:** #12345\\n**Amount:** $25.00",
    mention_users=[SlackConfig.User.Joe],
    mention_groups=[SlackConfig.Group.Dodgeball],
    mention_block_position="bottom",  # Mentions at bottom
    action_buttons=[
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Approve"},
            "action_id": "approve_refund",
            "value": "#12345",
            "style": "primary"
        }
    ]
)

# Example 3: Business logic usage
refund_request = Slack.RefundNotification(
    order_number="#12345",
    requestor_name="John Doe",
    requestor_email="john.doe@example.com",
    refund_type=Slack.RefundType.REFUND,
    notes="Customer requested refund"
)

result = service.send_refund_notification(
    refund_request=refund_request,
    order_data=order_data,
    mention_users=[SlackConfig.User.Joe],
    mention_groups=[SlackConfig.Group.Kickball]
)

# Example 4: Backward compatibility
result = service.send_refund_request_notification(
    requestor_info={"name": "John", "email": "john@example.com", "refund_type": "refund"},
    sheet_link="https://docs.google.com/spreadsheets/d/example",
    order_data=order_data,
    slack_channel_name="refund-requests",
    mention_strategy="sportAliases"
)

# Example 5: Factory function (backward compatibility)
client = create_slack_orchestrator(
    token=SlackConfig.Token.get_active_token(),
    channel_id=SlackConfig.Channel.RefundRequests
)
result = client.send_message_to_channel(
    channel=SlackConfig.Channel.JoeTest,
    message_text="Message from factory-created client"
)
""")
    
    print("=" * 50)
    print("✅ Usage Examples Complete!")

if __name__ == "__main__":
    test_consolidated_slack_orchestrator()
    demonstrate_usage_examples()
