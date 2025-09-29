#!/usr/bin/env python3
"""
Test script for custom message crafting capabilities.
Demonstrates how to create custom messages with mentions in specific positions.
"""

import sys
import os

# Set environment to dev to avoid Shopify token validation
os.environ["ENVIRONMENT"] = "dev"

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.slack.slack_service import SlackService
from slack_config import SlackConfig

def test_custom_message_crafting():
    """Test custom message crafting capabilities"""
    
    print("🧪 Testing Custom Message Crafting")
    print("=" * 50)
    
    # Initialize service
    service = SlackService()
    print(f"✅ Service initialized for {service.environment} environment")
    print()
    
    # Test 1: Custom message with mentions at bottom
    print("📋 Testing custom message with mentions at bottom:")
    result = service.send_custom_message(
        channel=SlackConfig.Channel.JoeTest,
        message_text="💰 *Refund Request Processed*\n\n**Order:** #12345\n**Customer:** John Doe\n**Amount:** $25.00\n**Status:** Completed",
        mention_users=[SlackConfig.User.Joe],
        mention_groups=[SlackConfig.Group.Dodgeball],
        mention_block_position="bottom",
        slack_text="Refund request processed for #12345"
    )
    print(f"✅ Result: {result['success']}")
    print()
    
    # Test 2: Custom message with mentions at top
    print("📋 Testing custom message with mentions at top:")
    result = service.send_custom_message(
        channel=SlackConfig.Channel.JoeTest,
        message_text="📦 *Order Update*\n\n**Order:** #67890\n**Status:** Shipped\n**Tracking:** 1Z999AA1234567890",
        mention_users=[SlackConfig.User.Joe],
        mention_block_position="top",
        slack_text="Order update for #67890"
    )
    print(f"✅ Result: {result['success']}")
    print()
    
    # Test 3: Custom message with custom blocks
    print("📋 Testing custom message with custom blocks:")
    custom_blocks = [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "🚨 *Urgent Refund Request*\n\n**Order:** #99999\n**Customer:** Jane Smith\n**Issue:** Payment failed"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Action Required:* Please review and process immediately"
            }
        },
        {"type": "divider"}
    ]
    
    result = service.send_custom_message_with_blocks(
        channel=SlackConfig.Channel.JoeTest,
        blocks=custom_blocks,
        mention_users=[SlackConfig.User.Joe],
        mention_groups=[SlackConfig.Group.Kickball],
        mention_block_position="bottom",
        slack_text="Urgent refund request for #99999"
    )
    print(f"✅ Result: {result['success']}")
    print()
    
    # Test 4: Custom message with action buttons
    print("📋 Testing custom message with action buttons:")
    action_buttons = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Approve"},
            "action_id": "approve_refund",
            "value": "#12345",
            "style": "primary"
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Deny"},
            "action_id": "deny_refund",
            "value": "#12345",
            "style": "danger"
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Request Info"},
            "action_id": "request_info",
            "value": "#12345"
        }
    ]
    
    result = service.send_custom_message(
        channel=SlackConfig.Channel.JoeTest,
        message_text="🔍 *Refund Review Required*\n\n**Order:** #12345\n**Amount:** $50.00\n**Reason:** Customer requested",
        action_buttons=action_buttons,
        mention_users=[SlackConfig.User.Joe],
        mention_block_position="bottom",
        slack_text="Refund review required for #12345"
    )
    print(f"✅ Result: {result['success']}")
    print()
    
    # Test 5: Complex custom message for refunds workflow
    print("📋 Testing complex refunds workflow message:")
    refund_blocks = [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "💰 *New Refund Request*\n\n**Order:** #ABC123\n**Customer:** John Doe (john.doe@example.com)\n**Product:** Summer Kickball League\n**Amount:** $75.00"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*Request Date:*\n2024-09-10 15:30:00"
                },
                {
                    "type": "mrkdwn",
                    "text": "*Reason:*\nSchedule conflict"
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "📋 <https://docs.google.com/spreadsheets/d/example|View in Google Sheets>"
                }
            ]
        },
        {"type": "divider"}
    ]
    
    result = service.send_custom_message_with_blocks(
        channel=SlackConfig.Channel.JoeTest,
        blocks=refund_blocks,
        mention_users=[SlackConfig.User.Joe],
        mention_groups=[SlackConfig.Group.Kickball],
        mention_block_position="bottom",
        slack_text="New refund request for #ABC123"
    )
    print(f"✅ Result: {result['success']}")
    print()
    
    print("=" * 50)
    print("✅ Custom Message Crafting Test Completed!")

def demonstrate_usage_examples():
    """Demonstrate real-world usage examples for custom messages"""
    
    print("\n📚 Custom Message Usage Examples")
    print("=" * 50)
    
    print("""
# Example 1: Refunds workflow with mentions at bottom
service = SlackService()

result = service.send_custom_message(
    channel=SlackConfig.Channel.RefundRequests,
    message_text="💰 *Refund Request Processed*\\n\\n**Order:** #12345\\n**Customer:** John Doe\\n**Amount:** $25.00",
    mention_users=[SlackConfig.User.Joe],
    mention_groups=[SlackConfig.Group.Dodgeball],
    mention_block_position="bottom",  # Mentions will appear at the bottom
    action_buttons=[
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "View Details"},
            "action_id": "view_details",
            "value": "#12345"
        }
    ]
)

# Example 2: Urgent message with mentions at top
result = service.send_custom_message(
    channel=SlackConfig.Channel.JoeTest,
    message_text="🚨 *Urgent: Payment Failed*\\n\\n**Order:** #67890\\n**Customer:** Jane Smith",
    mention_users=[SlackConfig.User.Joe],
    mention_block_position="top",  # Mentions will appear at the top
    slack_text="Urgent payment failure for #67890"
)

# Example 3: Custom blocks with mentions
custom_blocks = [
    {"type": "divider"},
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "📦 *Order Update*\\n\\n**Order:** #99999\\n**Status:** Shipped"
        }
    },
    {"type": "divider"}
]

result = service.send_custom_message_with_blocks(
    channel=SlackConfig.Channel.JoeTest,
    blocks=custom_blocks,
    mention_users=[SlackConfig.User.Joe],
    mention_groups=[SlackConfig.Group.Pickleball],
    mention_block_position="bottom"  # Mentions added as separate block
)

# Example 4: Complex refunds workflow message
refund_blocks = [
    {"type": "divider"},
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "💰 *New Refund Request*\\n\\n**Order:** #ABC123\\n**Customer:** John Doe"
        }
    },
    {
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": "*Amount:*\\n$75.00"
            },
            {
                "type": "mrkdwn",
                "text": "*Reason:*\\nSchedule conflict"
            }
        ]
    },
    {"type": "divider"}
]

result = service.send_custom_message_with_blocks(
    channel=SlackConfig.Channel.RefundRequests,
    blocks=refund_blocks,
    mention_users=[SlackConfig.User.Joe],
    mention_groups=[SlackConfig.Group.Kickball],
    mention_block_position="bottom"
)
""")
    
    print("=" * 50)
    print("✅ Usage Examples Complete!")

if __name__ == "__main__":
    test_custom_message_crafting()
    demonstrate_usage_examples()
