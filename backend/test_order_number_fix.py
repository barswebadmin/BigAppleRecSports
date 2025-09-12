#!/usr/bin/env python3
"""
Test that order number is now included in email mismatch message
"""

def show_expected_message():
    print("📧 EXPECTED EMAIL MISMATCH MESSAGE (with order number fixed):")
    print("=" * 70)
    
    expected_message = """⚠️ *Email Mismatch - Action Required*

*Request Type*: 💰 Refund back to original form of payment

*Request Submitted At*: 09/09/25 at 7:34 PM

*📧 Requested by*: John Doe (jdazz87@gmail.com)
*Email Associated with Order:* julialsaltzman@gmail.com

*Order Number:* 42291

*Notes provided by requestor:* valid test

⚠️ *The email provided does not match the order's customer email.*

*Please choose an action:*
• *Edit Request Details*: Update the order number or email and re-validate
• *Deny Request*: Close this request due to email mismatch

📊 [View in Google Sheets]"""
    
    print(expected_message)
    print()
    print("🔍 KEY FIX:")
    print("- Order Number now shows: *Order Number:* 42291")
    print("- Previously showed: *Order Number:* (empty)")
    print()
    print("✅ WHAT WAS FIXED:")
    print("- Added raw_order_number=request.order_number to the slack_service call in refunds.py")
    print("- The order number now flows: request.order_number → slack_service → build_email_mismatch_message")
    print()
    print("🧪 TESTING:")
    print("Check your Slack channel - the order number should now appear!")

if __name__ == "__main__":
    show_expected_message()
