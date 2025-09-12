# Slack Message Formatting Tests

This directory contains comprehensive tests for Slack message formatting to ensure **behavior-driven development consistency**. These tests are based on actual Slack messages sent by the system and validate that future changes don't break the expected message format.

## Purpose

The Slack service sends different types of messages based on refund request scenarios:

1. **Successful Refund Request** - When season info is parsed correctly and refund is calculated
2. **Fallback Message** - When season info cannot be parsed from product description
3. **Email Mismatch Error** - When requestor email doesn't match order customer email
4. **Order Not Found Error** - When the order number cannot be found in Shopify

## Test Coverage

The tests validate:

- ✅ **Message Structure** - Proper Slack block formatting with dividers and sections
- ✅ **Content Accuracy** - All required fields are present and correctly formatted
- ✅ **Sport Group Mentions** - Correct team mentions (@kickball, @dodgeball, etc.)
- ✅ **URL Formatting** - Proper Shopify admin links for orders and products
- ✅ **Request Type Display** - Correct emoji and text for refund vs store credit
- ✅ **Error Handling** - Appropriate error messages for different failure scenarios
- ✅ **Conditional Content** - Notes, sheet links, and other optional content

## Running the Tests

### Quick Run
```bash
python3 run_slack_tests.py
```

### Manual Run with pytest
```bash
python3 -m pytest test_slack_message_formatting.py -v
```

### Run Specific Test
```bash
python3 -m pytest test_slack_message_formatting.py::TestSlackMessageFormatting::test_fallback_season_info_message_format -v
```

## Test Data

The tests use actual message data from the system:

### Example 1: Fallback Message (Season Info Missing)
```
📌 New Refund Request!
⚠️ Order Found in Shopify but Missing Season Info (or Product Is Not a Regular Season)
Request Type: 💵 Refund back to original form of payment
📧 Requested by: joe test (jdazz87@gmail.com)
Request Submitted At: 07/14/25 at 11:12 PM
Order Number Provided: #40192
Order Created At: 06/25/25 at 8:39 AM
Product Title: joe test product
Total Paid: $2.00
⚠️ Could not parse 'Season Dates' from this order's description...
```

### Example 2: Email Mismatch Error
```
❌ Error with Refund Request - Email provided did not match order
Request Type: 🎟️ Store Credit to use toward a future order
📧 Requested by: joe test (jdazz87@gmail.com)
Email Associated with Order: lilaanchors@gmail.com
Order Number: #39611
📩 The requestor has been emailed to please provide correct order info...
```

### Example 3: Successful Request
```
📌 New Refund Request!
Request Type: 💵 Refund back to original form of payment
📧 Requested by: Amy Dougherty (lilaanchors@gmail.com)
Order Number: #39611
Sport/Season/Day: Big Apple Dodgeball - Wednesday - WTNB+ Division - Summer 2025
Season Start Date: 7/9/25
Total Paid: $115.00
Estimated Refund Due: $92.00
(This request is calculated to have been submitted after the start of week 2...)
```

## When to Run These Tests

🚨 **CRITICAL**: Run these tests whenever you make changes to:

- `services/slack_service.py` - Any modifications to message formatting
- `utils/date_utils.py` - Changes to date/time formatting functions
- Message templates or text content
- Error handling logic
- Sport group mentions or team assignments

## Expected Behavior

✅ **All tests should pass** - This ensures message formatting consistency

❌ **If tests fail** - This indicates that message formatting has changed and may need:
- Test updates to reflect intentional changes
- Code fixes to maintain expected behavior
- Review of the changes to ensure they're intentional

## Adding New Tests

When adding new message types or scenarios:

1. **Capture the actual Slack message** from the system
2. **Create a test method** following the existing pattern
3. **Validate all key components** of the message
4. **Update this README** with the new test case

## Integration with Development Workflow

These tests should be integrated into your development workflow:

```bash
# Before committing changes
python3 run_slack_tests.py

# As part of CI/CD pipeline
python3 -m pytest test_slack_message_formatting.py --junitxml=slack_test_results.xml
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the backend directory
2. **Missing pytest**: The test runner will auto-install pytest if needed
3. **Date/Time Formatting**: Tests use mocked datetime for consistency

### Test Environment

Tests use mocked Slack API calls to avoid sending actual messages during testing. The focus is on validating message content and structure, not API integration.

---

**Remember**: These tests are your safety net for maintaining consistent user experience in Slack notifications. Keep them updated and run them regularly! 