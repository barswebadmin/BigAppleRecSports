#!/usr/bin/env python3
"""
Test script for the new Slack models.
Demonstrates how to use the new Slack models system.
"""

import sys
import os

# Set environment to dev to avoid Shopify token validation
os.environ["ENVIRONMENT"] = "dev"

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.slack import Slack, RefundType, SlackActionType, SlackMessageType

def test_slack_models():
    """Test the new Slack models system"""
    
    print("🧪 Testing Slack Models System")
    print("=" * 50)
    
    # Test RefundNotification
    print("\n📋 Testing RefundNotification:")
    refund_request = Slack.RefundNotification(
        order_number="#12345",
        requestor_name="John Doe",
        requestor_email="john.doe@example.com",
        refund_type=RefundType.REFUND,
        notes="Customer requested refund due to schedule conflict",
        sheet_link="https://docs.google.com/spreadsheets/d/example",
        request_submitted_at="2024-09-10T15:30:00Z"
    )
    print(f"✅ RefundNotification created: {refund_request.order_number}")
    print(f"   Requestor: {refund_request.requestor_name}")
    print(f"   Type: {refund_request.refund_type}")
    
    # Test RefundConfirmation
    print("\n✅ Testing RefundConfirmation:")
    refund_confirmation = Slack.RefundConfirmation(
        order_number="#12345",
        customer_name="John Doe",
        customer_email="john.doe@example.com",
        refund_amount=25.00,
        refund_type=RefundType.REFUND,
        processed_by="joe",
        processed_at="2024-09-10T16:30:00Z",
        notes="Refund processed successfully",
        shopify_refund_id="refund_123"
    )
    print(f"✅ RefundConfirmation created: {refund_confirmation.order_number}")
    print(f"   Amount: ${refund_confirmation.refund_amount}")
    print(f"   Processed by: {refund_confirmation.processed_by}")
    
    # Test RefundDenial
    print("\n❌ Testing RefundDenial:")
    refund_denial = Slack.RefundDenial(
        order_number="#12345",
        customer_name="John Doe",
        customer_email="john.doe@example.com",
        denial_reason="Event already occurred",
        denied_by="joe",
        denied_at="2024-09-10T16:30:00Z",
        notes="Customer contacted after event date"
    )
    print(f"✅ RefundDenial created: {refund_denial.order_number}")
    print(f"   Reason: {refund_denial.denial_reason}")
    print(f"   Denied by: {refund_denial.denied_by}")
    
    # Test OrderUpdate
    print("\n📦 Testing OrderUpdate:")
    order_update = Slack.OrderUpdate(
        order_number="#12345",
        customer_name="John Doe",
        update_type="status_change",
        old_status="pending",
        new_status="confirmed",
        updated_by="system",
        updated_at="2024-09-10T16:30:00Z",
        notes="Order confirmed after payment processing"
    )
    print(f"✅ OrderUpdate created: {order_update.order_number}")
    print(f"   Update: {order_update.old_status} → {order_update.new_status}")
    print(f"   Updated by: {order_update.updated_by}")
    
    # Test LeadershipNotification
    print("\n👥 Testing LeadershipNotification:")
    leadership_notification = Slack.LeadershipNotification(
        notification_type="csv_processed",
        spreadsheet_title="2024 Leadership List",
        year=2024,
        records_processed=25,
        records_added=20,
        records_updated=5,
        processed_by="system",
        processed_at="2024-09-10T16:30:00Z",
        notes="Leadership CSV processed successfully"
    )
    print(f"✅ LeadershipNotification created: {leadership_notification.notification_type}")
    print(f"   Records: {leadership_notification.records_processed} processed, {leadership_notification.records_added} added")
    print(f"   Year: {leadership_notification.year}")
    
    # Test ProcessLeadershipCSV
    print("\n📊 Testing ProcessLeadershipCSV:")
    csv_request = Slack.ProcessLeadershipCSV(
        csv_data=[
            ["Email", "First Name", "Last Name"],
            ["user1@example.com", "John", "Doe"],
            ["user2@example.com", "Jane", "Smith"]
        ],
        spreadsheet_title="2024 Leadership List",
        year=2024
    )
    print(f"✅ ProcessLeadershipCSV created: {csv_request.spreadsheet_title}")
    print(f"   Records: {len(csv_request.csv_data) - 1} data rows")
    print(f"   Year: {csv_request.year}")
    
    # Test Enums
    print("\n🔢 Testing Enums:")
    print(f"RefundType.REFUND = {RefundType.REFUND}")
    print(f"RefundType.CREDIT = {RefundType.CREDIT}")
    print(f"SlackActionType.BUTTON = {SlackActionType.BUTTON}")
    print(f"SlackMessageType.REFUND_REQUEST = {SlackMessageType.REFUND_REQUEST}")
    
    # Test Slack User and Channel models
    print("\n👤 Testing Slack User and Channel:")
    slack_user = Slack.User(
        id="U0278M72535",
        name="joe",
        email="joe@example.com",
        display_name="Joe"
    )
    slack_channel = Slack.Channel(
        id="C092RU7R6PL",
        name="joe-test"
    )
    print(f"✅ Slack User: {slack_user.display_name} ({slack_user.id})")
    print(f"✅ Slack Channel: {slack_channel.name} ({slack_channel.id})")
    
    print("\n" + "=" * 50)
    print("✅ Slack Models System Test Completed!")

def demonstrate_usage_examples():
    """Demonstrate real-world usage examples"""
    
    print("\n📚 Usage Examples")
    print("=" * 50)
    
    print("""
# Example 1: Create a refund notification
refund_request = Slack.RefundNotification(
    order_number="#12345",
    requestor_name="John Doe",
    requestor_email="john.doe@example.com",
    refund_type=Slack.RefundType.REFUND,
    notes="Customer requested refund"
)

# Example 2: Create a refund confirmation
confirmation = Slack.RefundConfirmation(
    order_number="#12345",
    customer_name="John Doe",
    customer_email="john.doe@example.com",
    refund_amount=25.00,
    refund_type=Slack.RefundType.REFUND,
    processed_by="joe",
    processed_at="2024-09-10T16:30:00Z"
)

# Example 3: Create an order update
update = Slack.OrderUpdate(
    order_number="#12345",
    customer_name="John Doe",
    update_type="status_change",
    old_status="pending",
    new_status="confirmed",
    updated_by="system",
    updated_at="2024-09-10T16:30:00Z"
)

# Example 4: Create a leadership notification
leadership = Slack.LeadershipNotification(
    notification_type="csv_processed",
    spreadsheet_title="2024 Leadership List",
    year=2024,
    records_processed=25,
    processed_by="system",
    processed_at="2024-09-10T16:30:00Z"
)

# Example 5: Using enums
refund_type = Slack.RefundType.REFUND
action_type = Slack.ActionType.BUTTON
message_type = Slack.MessageType.REFUND_REQUEST
""")
    
    print("=" * 50)
    print("✅ Usage Examples Complete!")

if __name__ == "__main__":
    test_slack_models()
    demonstrate_usage_examples()
