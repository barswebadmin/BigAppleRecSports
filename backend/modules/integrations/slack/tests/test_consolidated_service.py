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
from config import config

def test_consolidated_slack_service():
    """Test the consolidated Slack service functionality"""
    
    print("🧪 Testing Consolidated SlackOrchestrator")
    print("=" * 50)
    
    # Initialize service
    slack_orchestrator = SlackOrchestrator()
    print(f"✅ Service initialized for {slack_orchestrator.environment} environment")
    print(f"🏃 Groups: {len(slack_orchestrator._get_groups())} configured")
    print()
    
    # Test 1: Low-level API methods
    print("🔧 Testing Low-level API Methods:")
    
    # Test send_message
    result = slack_orchestrator.send_message(
        channel_id=slack_orchestrator._get_channels()["JoeTest"],
        message_text="Test message from consolidated service",
        slack_text="Test message"
    )
    print(f"✅ send_message result: {result['success']}")
    
    # Test send_message_with_mentions
    result = slack_orchestrator.send_message_with_mentions(
        channel=slack_orchestrator._get_channels()["JoeTest"],
        message_text="Test message with mentions",
        users=slack_orchestrator._get_users()["Joe"],
        groups=slack_orchestrator._get_groups()["Dodgeball"]
    )
    print(f"✅ send_message_with_mentions result: {result['success']}")
    
    # Test update_message
    result = slack_orchestrator.update_message(
        channel_id=slack_orchestrator._get_channels()["JoeTest"],
        message_ts="1234567890.123456",
        message_text="Updated test message",
        slack_text="Updated message"
    )
    print(f"✅ update_message result: {result['success']}")
    
    # Test send_ephemeral_message
    result = slack_orchestrator.send_ephemeral_message(
        channel_id=slack_orchestrator._get_channels()["JoeTest"],
        user_id="U0278M72535",
        message_text="Ephemeral test message",
        slack_text="Ephemeral message"
    )
    print(f"✅ send_ephemeral_message result: {result['success']}")
    print()
    
    # Test 2: Custom message crafting
    print("🎨 Testing Custom Message Crafting:")
    
    # Test custom message with mentions at bottom
    result = slack_orchestrator.send_custom_message(
        channel=slack_orchestrator._get_channels()["JoeTest"],
        message_text="💰 *Custom Refund Message*\n\n**Order:** #12345\n**Amount:** $25.00",
        mention_users=slack_orchestrator._get_users()["Joe"],
        mention_groups=slack_orchestrator._get_groups()["Dodgeball"],
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
    result = slack_orchestrator.send_custom_message(
        channel=slack_orchestrator._get_channels()["JoeTest"],
        message_text="📦 *Order Update*\n\n**Order:** #67890\n**Status:** Shipped",
        mention_users=slack_orchestrator._get_users()["Joe"],
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
    
    result = slack_orchestrator.send_refund_notification(
        refund_request=refund_request,
        order_data=order_data,
        mention_users=slack_orchestrator._get_users()["Joe"],
        mention_groups=slack_orchestrator._get_groups()["Kickball"]
    )
    print(f"✅ Refund notification result: {result['success']}")
    print()
    
    # Test 4: Backward compatibility
    print("🔄 Testing Backward Compatibility:")
    
    result = slack_orchestrator.send_refund_request_notification(
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
    
    sport_mention = slack_orchestrator.get_sport_group_mention("Summer Kickball League")
    print(f"✅ Sport group mention: {sport_mention}")
    
    order_url = slack_orchestrator.get_order_url("gid://shopify/Order/12345", "#12345")
    print(f"✅ Order URL: {order_url}")
    
    product_url = slack_orchestrator.get_product_url("gid://shopify/Product/67890")
    print(f"✅ Product URL: {product_url}")
    
    button_data = slack_orchestrator.parse_button_value("rawOrderNumber=#12345|orderId=gid://shopify/Order/12345|refundAmount=36.00")
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
slack_orchestrator = SlackOrchestrator()

# Send a simple message
result = slack_orchestrator.send_message(
    channel_id=slack_orchestrator._get_channels()["RefundRequests"],
    message_text="New refund request received",
    slack_text="Refund request"
)

# Send message with mentions
result = slack_orchestrator.send_message_with_mentions(
    channel=slack_orchestrator._get_channels()["JoeTest"],
    message_text="Please review this refund",
    users=slack_orchestrator._get_users()["Joe"],
    groups=slack_orchestrator._get_groups()["Dodgeball"]
)

# Update an existing message
result = slack_orchestrator.update_message(
    channel_id=slack_orchestrator._get_channels()["RefundRequests"],
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
result = slack_orchestrator.send_custom_message(
    channel=slack_orchestrator._get_channels()["RefundRequests"],
    message_text="💰 *Refund Request Processed*\\n\\n**Order:** #12345\\n**Amount:** $25.00",
    mention_users=slack_orchestrator._get_users()["Joe"],
    mention_groups=slack_orchestrator._get_groups()["Dodgeball"],
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

result = slack_orchestrator.send_refund_notification(
    refund_request=refund_request,
    order_data=order_data,
    mention_users=slack_orchestrator._get_users()["Joe"],
    mention_groups=slack_orchestrator._get_groups()["Kickball"]
)

# Example 4: Backward compatibility
result = slack_orchestrator.send_refund_request_notification(
    requestor_info={"name": "John", "email": "john@example.com", "refund_type": "refund"},
    sheet_link="https://docs.google.com/spreadsheets/d/example",
    order_data=order_data,
    slack_channel_name="refund-requests",
    mention_strategy="sportAliases"
)

# Example 5: Factory function (backward compatibility)
client = slack_orchestrator.create_slack_orchestrator(
    token=slack_orchestrator._get_tokens()["RefundRequests"],
    channel_id=slack_orchestrator._get_channels()["RefundRequests"]
)
result = client.send_message_to_channel(
    channel=slack_orchestrator._get_channels()["JoeTest"],
    message_text="Message from factory-created client"
)
""")
    
    print("=" * 50)
    print("✅ Usage Examples Complete!")

if __name__ == "__main__":
    test_consolidated_slack_service()
    demonstrate_usage_examples()
