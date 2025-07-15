# BARS Backend Testing Guide

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

## Running Tests

### Default Test Suite (Recommended)
```bash
make test
```
Runs all unit tests with mocked services - **safe, no external API calls**.

### Unit Tests Only
```bash
make test-unit
```

### Integration Tests (Use Carefully)
```bash
# Start server first
make start

# In another terminal
make test-integration-error-codes
```
⚠️ **Warning**: These may send actual Slack messages to #refunds channel.

### Test Everything
```bash
make test-all
```

## Test Coverage

### Error Code Testing
- **406**: Order not found in Shopify
- **409**: Email mismatch (requestor email ≠ order customer email)  
- **200**: Successful refund request processing
- **500**: Internal server errors (Slack failures, etc.)

### Slack Message Testing
- **Fallback messages**: When season info missing
- **Error messages**: Order not found, email mismatch
- **Success messages**: Normal refund requests
- **Sport mentions**: Automatic @group mentions based on product names

## Mocking Strategy

### Unit Tests Use Mocks For:
- `OrdersService.fetch_order_details()` - Returns test order data
- `OrdersService.calculate_refund_due()` - Returns mock refund calculations  
- `SlackService.send_refund_request_notification()` - Returns success/failure without API calls

### Integration Tests Use Real:
- HTTP requests to running server
- Actual Shopify API calls (if configured)
- **Actual Slack API calls** ⚠️

## Best Practices

1. **Always run unit tests first** - they're fast and safe
2. **Use integration tests sparingly** - they affect real systems
3. **Mock external services** in unit tests to avoid side effects
4. **Test error conditions** thoroughly with mocked failures
5. **Validate message formats** without sending actual messages

## Development Workflow

```bash
# During development - safe and fast
make test-unit

# Before committing - full validation  
make test

# For integration testing (careful!)
make start  # Terminal 1
make test-integration-error-codes  # Terminal 2
``` 