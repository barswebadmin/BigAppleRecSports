# Slack Webhook Testing Guide

## Overview

This guide covers testing the Slack webhook functionality that handles refund request button interactions. The webhook processes user actions from Slack messages and updates them with appropriate responses and next-step options.

## Test Structure

### Unit Tests Location
- **Primary Tests**: `routers/tests/test_slack_router.py`
- **Service Tests**: `services/slack/tests/test_message_builder.py`
- **Message Format Tests**: `tests/unit/test_slack_message_formatting.py`

### Test Runners
- **Webhook Tests Only**: `python3 run_slack_webhook_tests.py`
- **All Slack Tests**: `python3 run_slack_webhook_tests.py --all`
- **Make Commands**: `make test-slack-webhook` or `make test-slack-all`

## Debug Mode Message Format Validation

The tests specifically validate that debug mode produces messages matching this exact format:

### Cancel Order Result Message
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

### Restock Completion Message
```
✅ [DEBUG] Inventory for Veteran Registration has been restocked by @joe randazzo (he/him)

🔗 <https://docs.google.com/spreadsheets/d/URL|View Request in Google Sheets>

All refund processing completed!
```

### No Restock Completion Message
```
🚫 [DEBUG] No inventory was restocked - Process completed by @joe randazzo (he/him)

🔗 <https://docs.google.com/spreadsheets/d/URL|View Request in Google Sheets>

All refund processing completed!
```

## Test Categories

### 1. Webhook Signature Validation
- **Test**: `test_webhook_signature_validation`
- **Purpose**: Ensures webhook properly validates Slack signatures
- **Coverage**: HMAC signature verification, timestamp validation

### 2. Cancel Order Action (Step 1)
- **Test**: `test_cancel_order_webhook_debug_mode`
- **Purpose**: Validates cancel order button produces correct debug message
- **Expected**: Message with "[DEBUG]" prefix, order cancellation confirmation, refund options

### 3. Process Refund Action (Step 2) 
- **Test**: `test_process_refund_webhook_debug_mode`
- **Purpose**: Validates refund processing produces inventory management message
- **Expected**: Debug refund confirmation, inventory listing, restock buttons

### 4. Restock Inventory Actions (Step 3)
- **Test**: `test_restock_inventory_webhook_debug_mode`
- **Purpose**: Validates specific variant restock actions
- **Expected**: Debug completion message with variant name

### 5. "Do Not Restock" Action (Step 3 Alternative)
- **Test**: `test_do_not_restock_webhook_debug_mode`  
- **Purpose**: Validates completion without restocking
- **Expected**: Debug completion message indicating no restock

### 6. Utility Function Tests
- **Tests**: `test_parse_button_value`, `test_extract_text_from_blocks`, etc.
- **Purpose**: Validates helper functions work correctly
- **Coverage**: Button value parsing, text extraction, link parsing

### 7. Message Format Validation
- **Tests**: `TestSlackWebhookMessageFormats` class
- **Purpose**: Validates specific message format requirements
- **Coverage**: Debug vs production differences, exact text matching

## Key Test Features

### Mocking Strategy
- **Slack API**: Mocked to prevent real messages during tests
- **Orders Service**: Mocked to return predictable order data
- **Settings**: Patched to control debug/production mode behavior

### Debug Mode Testing
All tests specifically validate debug mode behavior:
- Messages include `[DEBUG]` prefix
- User names preserved exactly (e.g., "joe randazzo (he/him)")
- Order URLs properly linked to Shopify admin
- Product titles extracted from message content
- Google Sheets links preserved through workflow

### Data Validation
Tests ensure data preservation through webhook workflow:
- Original requestor information maintained
- Google Sheets links extracted and preserved
- Product titles and links correctly parsed
- Order numbers properly linked to Shopify
- Inventory data accurately displayed

## Running Tests

### Quick Test (Webhook Only)
```bash
make test-slack-webhook
```

### Comprehensive Test (All Slack)
```bash
make test-slack-all
```

### Manual Test Execution
```bash
# Webhook tests only
python3 -m pytest routers/tests/test_slack_router.py -v

# Specific test
python3 -m pytest routers/tests/test_slack_router.py::TestSlackWebhook::test_process_refund_webhook_debug_mode -v

# With coverage
python3 -m pytest routers/tests/test_slack_router.py --cov=routers.slack --cov-report=html
```

## Integration with Development Workflow

### Before Committing
```bash
make test-slack-all
```

### During Development
```bash
make test-slack-webhook  # Quick webhook validation
```

### CI/CD Pipeline
```bash
python3 -m pytest routers/tests/test_slack_router.py --junitxml=webhook_test_results.xml
```

## Expected Test Output

### Successful Run
```
🧪 Running Slack Webhook Tests...
============================================================
📋 Testing webhook functionality including:
   • Signature validation
   • Cancel order webhook actions
   • Process refund webhook actions
   • Restock inventory webhook actions
   • Debug mode message formatting
   • Message content validation
============================================================

routers/tests/test_slack_router.py::TestSlackWebhook::test_webhook_signature_validation PASSED
routers/tests/test_slack_router.py::TestSlackWebhook::test_cancel_order_webhook_debug_mode PASSED
routers/tests/test_slack_router.py::TestSlackWebhook::test_process_refund_webhook_debug_mode PASSED
...

✅ All Slack webhook tests passed!
🎯 Debug message formatting is working correctly
🔒 Webhook signature validation is working
📨 Message format matches expected debug environment output
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure running from `backend/` directory
2. **Missing pytest**: Run `pip install pytest` or use test runners
3. **Signature Validation Fails**: Check SLACK_SIGNING_SECRET configuration
4. **Message Format Mismatch**: Verify debug mode settings and message builders

### Debug Tips

1. **Verbose Output**: Add `-v` flag to pytest commands
2. **Print Debugging**: Tests include detailed debug output
3. **Isolate Tests**: Run specific test methods to narrow down issues
4. **Mock Verification**: Check that mocks are being called correctly

## Maintenance

### When to Update Tests

- ✅ **Always** when changing webhook functionality
- ✅ **Always** when modifying message formats
- ✅ **Always** when adding new webhook actions
- ✅ When changing debug mode behavior
- ✅ When updating Slack API integration

### Test Maintenance Checklist

1. Update test payloads if Slack message structure changes
2. Verify message format expectations match actual output
3. Update mock data when order structure changes
4. Ensure coverage of all webhook action types
5. Validate debug vs production mode differences

---

**Remember**: These tests are the safety net for webhook functionality. Keep them updated and run them regularly to ensure reliable Slack integration! 