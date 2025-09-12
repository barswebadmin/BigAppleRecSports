#!/usr/bin/env python3
"""
Test script to show the new email mismatch message format with buttons
"""

import json
import sys
from unittest.mock import patch, MagicMock

sys.path.append(".")


# Mock the required dependencies for testing
class MockDatetime:
    @staticmethod
    def now(tz):
        return MockDatetime()

    def __str__(self):
        return "2025-09-09T19:29:00"


def mock_format_date_and_time(dt):
    return "09/09/25 at 7:29 PM"


def mock_parse_shopify_datetime(dt):
    return MockDatetime()


def test_email_mismatch_message():
    print("🧪 Testing Email Mismatch Message with Buttons")
    print("=" * 60)

    # Use proper context manager mocking instead of global sys.modules pollution
    with patch("utils.date_utils.format_date_and_time", side_effect=mock_format_date_and_time), \
         patch("utils.date_utils.parse_shopify_datetime", side_effect=mock_parse_shopify_datetime):
        
        # Import inside the context manager to ensure proper mocking
        from services.slack.message_builder import SlackMessageBuilder
        
        # Create a SlackMessageBuilder instance
        sport_groups = {
            "@bowling": ["bowling"],
            "@kickball": ["kickball"],
            "@dodgeball": ["dodgeball"],
        }
        builder = SlackMessageBuilder(sport_groups)

        # Test data matching your curl request
        requestor_info = {
            "name": {"first": "John", "last": "Doe"},
            "email": "jdazz87@gmail.com",
            "refund_type": "refund",
            "notes": "valid test",
        }

        # Test the new email mismatch message
        result = builder.build_email_mismatch_message(
            requestor_info=requestor_info,
            raw_order_number="42291",
            order_customer_email="julialsaltzman@gmail.com",
            sheet_link="https://docs.google.com/spreadsheets/d/test/edit#gid=1&range=A6",
            order_data={"order": {"line_items": [{"title": "Kickball League"}]}},
        )

        print("📧 NEW EMAIL MISMATCH MESSAGE:")
        print("-" * 40)
        print("Slack Text:", result.get("slack_text", "N/A"))
        print()
        print("Message Text:")
        print(result.get("text", "No text"))
        print()

        action_buttons = result.get("action_buttons", [])
        print(f"🔘 Action Buttons ({len(action_buttons)}):")
        for i, button in enumerate(action_buttons, 1):
            button_text = button.get("text", {}).get("text", "No text")
            action_id = button.get("action_id", "No ID")
            style = button.get("style", "default")
            has_confirm = "confirm" in button
            print(
                f"  {i}. {button_text} (action_id: {action_id}, style: {style}, confirm: {has_confirm})"
            )

        print()
        print("🔍 BUTTON DETAILS:")
        print("-" * 40)
        for i, button in enumerate(action_buttons, 1):
            print(f"Button {i}: {json.dumps(button, indent=2)}")
            print()

        # Assert the test generated valid results
        assert result is not None, "Result should not be None"
        assert "text" in result, "Result should contain 'text' field"
        assert "action_buttons" in result, "Result should contain 'action_buttons' field"
        assert len(result["action_buttons"]) == 2, "Should have exactly 2 action buttons"


def show_old_vs_new():
    print("📊 COMPARISON: OLD vs NEW MESSAGE")
    print("=" * 60)

    print("❌ OLD MESSAGE (what you saw before):")
    print("━" * 40)
    old_message = """:x: Error with Refund Request - Email provided did not match order
Request Type: :dollar: Refund back to original form of payment
Request Submitted At: 09/09/25 at 7:29 PM
:e-mail: Requested by: John Doe (jdazz87@gmail.com)
Email Associated with Order: julialsaltzman@gmail.com
Order Number: 42291
Notes provided by requestor: valid test
:envelope_with_arrow: The requestor has been emailed to please provide correct order info. No action needed at this time."""

    print(old_message)
    print("\n🔘 OLD BUTTONS: None (0 buttons)")

    print("\n" + "=" * 60)

    print("✅ NEW MESSAGE (what you should see now):")
    print("━" * 40)
    result = test_email_mismatch_message()

    print("\n📈 IMPROVEMENT SUMMARY:")
    print("-" * 40)
    print("✅ Changed from error message to actionable message")
    print("✅ Added 2 action buttons for user interaction")
    print("✅ Clear instructions on what to do next")
    print("✅ Proper formatting with warning icon instead of error")
    print("✅ Buttons allow editing details or denying the request")


if __name__ == "__main__":
    show_old_vs_new()
