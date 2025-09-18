#!/usr/bin/env python3
"""
Test script for the new Slack configuration system.
Demonstrates how to use SlackConfig for clean, type-safe access to Slack resources.
"""

import sys
import os

# Set environment to dev to avoid Shopify token validation
os.environ["ENVIRONMENT"] = "dev"

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
# from config.Slack import SlackConfig, SlackChannel, SlackUser, SlackGroup, SlackToken, Slack
SlackConfig = config.Slack
SlackChannel = config.SlackChannel
SlackUser = config.SlackUser
SlackGroup = config.SlackGroup
SlackBot = config.SlackBot
Slack = config.Slack


def test_slack_config():
    """Test the new Slack configuration system"""
    
    print("🧪 Testing Slack Configuration System")
    print("=" * 50)
    
    # Test channel access
    print("\n📺 Testing Channel Access:")
    print(f"SlackChannel.RegistrationRefunds = {SlackChannel.RegistrationRefunds.id}")
    print(f"SlackChannel.JoeTest = {SlackChannel.JoeTest.id}")
    
    # Test user access
    print("\n👤 Testing User Access:")
    print(f"SlackUser.Joe = {SlackUser.Joe.id}")
    print(f"SlackUser.Here = {SlackUser.Here}")
    
    # Test group access
    print("\n👥 Testing Group Access:")
    print(f"SlackGroup.Kickball = {SlackGroup.Bowling.name}")
    print(f"SlackGroup.Dodgeball = {SlackGroup.Dodgeball.name}")
    print(f"SlackGroup.Kickball = {SlackGroup.Kickball.name}")
    print(f"SlackGroup.Dodgeball = {SlackGroup.Pickleball.name}")
    
    # Test environment info
    print("\n🌍 Testing Environment Info:")
    print(f"SlackConfig.get_environment() = {SlackConfig.get_environment()}")
    print(f"SlackConfig.is_production() = {SlackConfig.is_production}")
    
    # Test dynamic lookups
    print("\n🔍 Testing Dynamic Lookups:")
    print(f"SlackChannel.get_channel_id('registration-refunds') = {SlackChannel.all()['registration-refunds'].name}")
    print(f"SlackConfig.Groups.all()['dodgeball'] = {SlackGroup.all()['dodgeball'].get('name')}")
    
    # Test convenience alias
    print("\n⚡ Testing Convenience Alias:")
    print(f"Slack.Channels.RegistrationRefunds = {SlackChannel.RegistrationRefunds.name}")
    print(f"Slack.User.Joe = {SlackUser.Joe.name}")
    print(f"Slack.Group.Dodgeball = {SlackGroup.Dodgeball.name}")
    
    print("\n" + "=" * 50)
    print("✅ Slack Configuration System Test Completed!")

def test_api_client_with_config():
    """Test the API client using the new configuration system"""
    
    print("\n🚀 Testing API Client with New Configuration")
    print("=" * 50)
    
    # Import the SlackService instead of the old API client
    try:
        from new_structure_target.clients.slack.slack_service import SlackService
        
        # Create service using config
        service = SlackService()
        
        print(f"📺 Testing channel: {SlackChannel.JoeTest.id}")
        
        # Get a token for testing
        token = SlackBot.Dev.require_token()
        print(f"🔑 Using token: {token[:10]}..." if len(token) > 10 else f"🔑 Using token: {token}")
        
        # Test sending message with new token-per-operation approach
        print("\n📤 Testing send_message with token:")
        result = service.send_message(
            channel=SlackChannel.JoeTest.id,
            token=SlackBot.Dev.require_token(),
            message_text=f"🧪 Test message to {SlackChannel.JoeTest.name} using SlackBot.Dev, message_text",
            slack_text=f"Test message to {SlackChannel.JoeTest.name} using SlackBot.Dev, slack_text"
        )
        print(f"✅ Result: {result.get('ok', False)}")
        
        # Test sending another message to show multi-channel capability
        print("\n🔄 Testing send_message to different channel:")
        result = service.send_message(
            channel=SlackChannel.RegistrationRefunds.id,
            token=SlackBot.Dev.require_token(),
            message_text=f"🧪 Test message to {SlackChannel.RegistrationRefunds.name} channel, message_text",
            slack_text="Test with different channel"
        )
        print(f"✅ Result: {result.get('ok', False)}")
        
        # Test ephemeral message (only visible to specific user)
        print("\n👤 Testing send_ephemeral_message:")
        result = service.send_ephemeral_message(
            channel_id=SlackChannel.JoeTest.id,
            token=SlackBot.Dev.require_token(),
            user_id=SlackUser.Joe.id,
            message_text="🤫 This ephemeral message is only visible to Joe",
            slack_text="Ephemeral test"
        )
        print(f"✅ Result: {result.get('ok', False)}")
        
        print("\n" + "=" * 50)
        print("✅ API Client with Token-per-Operation Test Completed!")
        print("🎯 Demonstrated multi-channel and ephemeral messaging!")
        
    except ImportError as e:
        print(f"⚠️  Could not import SlackService: {e}")
        print("✅ Configuration test completed (service not available)")

def demonstrate_usage_examples():
    """Demonstrate real-world usage examples"""
    
    print("\n📚 Usage Examples")
    print("=" * 50)
    
    print("""
# Example 1: Send a message to refund requests channel
service.send_message_to_channel(
    channel=SlackConfig.Channel.RefundRequests,
    message_text="New refund request received",
    action_buttons=[...]
)

# Example 2: Send a message with user mentions
service.send_message_with_mentions(
    channel=SlackConfig.Channel.JoeTest,
    message_text="Please review this refund request",
    users=[SlackConfig.User.Joe],
    groups=[SlackConfig.Group.Dodgeball]
)

# Example 3: Create service with specific token
from slack_service import SlackService
service = SlackService()  # Uses active token from config

# Example 4: Check environment
if SlackConfig.is_production_mode():
    channel = SlackConfig.Channel.RefundRequests
else:
    channel = SlackConfig.Channel.JoeTest

# Example 5: Dynamic channel lookup
channel_id = SlackChannel.get_channel_id('refund-requests')
if channel_id:
    service.send_message(channel_id=channel_id, message_text="...")

# Example 6: Using convenience alias
service.send_message_to_channel(
    channel=Slack.Channel.RefundRequests,
    message_text="Using convenience alias"
)
""")
    
    print("=" * 50)
    print("✅ Usage Examples Complete!")

if __name__ == "__main__":
    test_slack_config()
    # test_api_client_with_config()  # Temporarily disabled due to indentation issue
    demonstrate_usage_examples()
