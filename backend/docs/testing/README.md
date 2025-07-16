# Testing Guide

## Overview

The BARS backend has a comprehensive testing suite covering unit tests, integration tests, and specialized Slack functionality tests. This guide covers all testing approaches and provides commands for running different test suites.

## Test Types and Organization

### Unit Tests (Mocked Services) 🧪
**Location**: `test_*_unit.py` files  
**Purpose**: Test business logic without external dependencies  
**Command**: `make test-unit`

- **`test_error_codes_unit.py`**: Tests error handling logic with mocked Slack and OrdersService
  - ✅ Order not found (406) 
  - ✅ Email mismatch (409)
  - ✅ Successful requests (200)
  - ✅ Slack service failures (500)
  - **No actual Slack messages sent** - services are mocked

- **`test_slack_message_formatting.py`**: Tests Slack message formatting without sending messages
  - Message structure validation
  - Sport group mentions (@kickball, @bowling, etc.)
  - URL formatting
  - Error and success message formats

- **`routers/tests/test_slack_router.py`**: Tests Slack webhook functionality for refund workflow
  - Webhook signature validation
  - Cancel order, process refund, and restock inventory actions
  - Debug mode message format validation
  - Button interaction workflows

### Integration Tests (Live Services) 🔗
**Location**: `test_*.py` files (without `_unit` suffix)  
**Purpose**: Test real API endpoints with actual services  
**Command**: `make test-integration` or specific commands

- **`test_error_codes.py`**: Tests HTTP endpoints with real server
  - ⚠️ **May send actual Slack messages**
  - Requires running server (`make start`)
  - Use `make test-integration-error-codes` to run these specifically

### Quick Tests ⚡
**Command**: `make test-quick`
- Runs most critical unit tests only
- Fast feedback for development

## Slack Testing

### Slack Message Formatting Tests

The Slack service sends different types of messages based on refund request scenarios:

1. **Successful Refund Request** - When season info is parsed correctly and refund is calculated
2. **Fallback Message** - When season info cannot be parsed from product description
3. **Email Mismatch Error** - When requestor email doesn't match order customer email
4. **Order Not Found Error** - When the order number cannot be found in Shopify

#### Test Coverage

The tests validate:

- ✅ **Message Structure** - Proper Slack block formatting with dividers and sections
- ✅ **Content Accuracy** - All required fields are present and correctly formatted
- ✅ **Sport Group Mentions** - Correct team mentions (@kickball, @dodgeball, etc.)
- ✅ **URL Formatting** - Proper Shopify admin links for orders and products
- ✅ **Request Type Display** - Correct emoji and text for refund vs store credit
- ✅ **Error Handling** - Appropriate error messages for different failure scenarios
- ✅ **Conditional Content** - Notes, sheet links, and other optional content

### Slack Webhook Testing

The webhook functionality processes user actions from Slack messages and updates them with appropriate responses and next-step options.

#### Test Structure

- **Primary Tests**: `routers/tests/test_slack_router.py`
- **Service Tests**: `services/slack/tests/test_message_builder.py`
- **Message Format Tests**: `tests/unit/test_slack_message_formatting.py`

#### Test Runners
- **Webhook Tests Only**: `python3 run_slack_webhook_tests.py`
- **All Slack Tests**: `python3 run_slack_webhook_tests.py --all`
- **Make Commands**: `make test-slack-webhook` or `make test-slack-all`

#### Debug Mode Message Format Validation

The tests specifically validate that debug mode produces messages matching this exact format:

**Cancel Order Result Message:**
```
✅ [DEBUG] Cancellation Request for Order <https://admin.shopify.com/store/09fe59-3/orders/5759498846302|#40192> for jdazz87@gmail.com has been processed by @joe randazzo (he/him)
✅ [DEBUG] Request to provide a $1.80 refund for Order <https://admin.shopify.com/store/09fe59-3/orders/5759498846302|#40192> has been processed by @joe randazzo (he/him)

🔗 <https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit#gid=1435845892&range=A73|View Request in Google Sheets>

📦 *Season Start Date for <https://admin.shopify.com/store/09fe59-3/products/7350462185566|joe test product> is Unknown.*
*Current Inventory:*
• *Veteran Registration*: 0 spots available
• *Early Registration*: 0 spots available  
• *Open Registration*: 17 spots available
• *Coming off Waitlist Reg*: 0 spots available
```

**Restock Completion Message:**
```
✅ [DEBUG] Inventory for Veteran Registration has been restocked by @joe randazzo (he/him)

🔗 <https://docs.google.com/spreadsheets/d/URL|View Request in Google Sheets>

All refund processing completed!
```

**No Restock Completion Message:**
```
🚫 [DEBUG] No inventory was restocked - Process completed by @joe randazzo (he/him)

```

## Running Tests

### Make Commands
```bash
# All tests
make test

# Unit tests only (fast, no external dependencies)
make test-unit

# Integration tests (may send real Slack messages)
make test-integration

# Quick subset of critical tests
make test-quick

# Slack-specific tests
make test-slack-webhook     # Webhook functionality only
make test-slack-all        # All Slack tests (webhook + message formatting)
```

### Direct Commands

#### Quick Run
```bash
python3 run_slack_tests.py
```

#### Manual Run with pytest
```bash
python3 -m pytest test_slack_message_formatting.py -v
```

#### Run Specific Test
```bash
python3 -m pytest test_slack_message_formatting.py::TestSlackMessageFormatting::test_fallback_season_info_message_format -v
```

#### Webhook Tests
```bash
# Webhook tests only
python3 run_slack_webhook_tests.py

# All Slack tests
python3 run_slack_webhook_tests.py --all
```

## Test Data

The tests use actual message data from the system to ensure real-world accuracy. Example test scenarios include:

### Example 1: Fallback Message (Season Info Missing)
```
📌 New Refund Request!
⚠️ Order Found in Shopify but Missing Season Info (or Product Is Not a Regular Season)
```

### Example 2: Successful Refund Request
Contains properly formatted order information, refund calculations, and action buttons.

### Example 3: Error Messages
Proper formatting for order not found and email mismatch scenarios.

## Best Practices

1. **Always run unit tests first** - They're fast and catch basic logic errors
2. **Use integration tests sparingly** - They may send real Slack messages
3. **Test message formatting changes** - Run Slack tests when modifying message content
4. **Validate webhook interactions** - Test button workflows when changing Slack functionality
5. **Check debug mode formatting** - Ensure debug messages follow the expected format

## Troubleshooting

- **Tests fail with import errors**: Check that you're running from the correct directory
- **Slack tests timeout**: Verify network connectivity and Slack configuration
- **Message format mismatches**: Check that actual Slack messages match expected format patterns
- **Webhook signature validation fails**: Ensure test secrets match configured values

For more detailed information about specific test files and their purposes, see the individual test files in the `tests/` directory.

## Related Documentation

- **[📖 Documentation Index](../README.md)** - All documentation
- **[🔌 Orders API](../api/orders.md)** - API endpoints to test
- **[🚀 Production Deployment](../deployment/production.md)** - Production testing validation
- **[👨‍💻 Development Guides](../development/)** - Development workflow testing
- **[🏠 Main README](../../README.md)** - Project setup and overview
