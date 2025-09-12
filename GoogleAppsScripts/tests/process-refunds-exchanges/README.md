# Process Refunds & Exchanges - Test Suite

This directory contains comprehensive tests for the Google Apps Script form submission flow and the backend API processing for refunds and exchanges.

## Overview

The test suite covers the complete workflow:
1. **Google Form Submission** → Google Apps Script processes form data
2. **Backend API Call** → GAS sends JSON payload to backend `/refunds/send-to-slack`
3. **Backend Processing** → Three possible outcomes:
   - ✅ **Success**: Order found, email matches → Send to Slack with action buttons
   - ⚠️ **Email Mismatch (409)**: Order found, email doesn't match → Send warning to Slack
   - ❌ **Order Not Found (406)**: Order not in Shopify → Send error to Slack, email requestor

## Test Files

### Google Apps Script Tests
- **`test_form_submission.js`** - Main test suite for GAS form processing
- **`run_tests.sh`** - Test runner script with colored output
- **`package.json`** - Node.js dependencies for testing

### Backend API Tests  
- **`../backend/tests/test_refunds_api.py`** - Comprehensive backend API tests
- **`../backend/tests/requirements.txt`** - Python testing dependencies

## Running the Tests

### Google Apps Script Tests

```bash
# Option 1: Use the test runner (recommended)
cd GoogleAppsScripts/tests/process-refunds-exchanges
./run_tests.sh

# Option 2: Run directly with Node.js
cd GoogleAppsScripts/tests/process-refunds-exchanges
npm install
node test_form_submission.js
```

### Backend API Tests

```bash
# From the backend directory
cd backend
pip install -r tests/requirements.txt
pytest tests/test_refunds_api.py -v

# Or run with coverage
pytest tests/test_refunds_api.py --cov=routers.refunds --cov-report=html
```

## Test Coverage

### Google Apps Script Tests

✅ **Form Data Extraction**
- Field keyword matching (case-insensitive)
- Requestor name parsing (first/last)
- Order number extraction
- Refund type detection ("refund" vs "credit")
- Notes field handling

✅ **Backend Payload Construction**
- Correct JSON structure matching backend API expectations
- Order number normalization
- Sheet link generation
- HTTP request options (headers, method, etc.)

✅ **API Call Handling**
- Successful responses (200)
- Error responses (406, 409, 500)
- Proper UrlFetchApp.fetch usage
- Response parsing

✅ **Field Variations**
- Different form field names and casing
- Missing optional fields (notes)
- Various requestor name formats

### Backend API Tests

✅ **Success Scenario (200)**
- Order found in Shopify
- Requestor email matches order customer email
- Successful Slack notification with action buttons
- Proper service method calls

✅ **Order Not Found (406)**
- Order not found in Shopify
- Returns 406 status code
- Sends error notification to Slack
- No action buttons in Slack message

✅ **Email Mismatch (409)**
- Order found but email doesn't match
- Returns 409 status code  
- Sends warning to Slack with edit/deny buttons
- Includes order's actual email in message

✅ **Request Validation**
- Pydantic model validation
- Required field validation
- Requestor name format handling
- Order number normalization

✅ **Error Handling**
- Service exceptions (Shopify API errors)
- Slack API failures
- Malformed requests
- Network timeouts

## Mocking Strategy

### No Real API Calls
- **Shopify API**: Mocked via `orders_service` dependency injection
- **Slack API**: Mocked via `slack_service` dependency injection  
- **Google Apps Script APIs**: Mocked `UrlFetchApp`, `Logger`, `MailApp`
- **Network Requests**: All HTTP calls are intercepted and mocked

### Test Data
- Realistic order data structures matching Shopify GraphQL responses
- Proper requestor information formats
- Valid Google Sheets links
- Authentic error messages and status codes

## Test Scenarios

### 1. Successful Processing
```json
{
  "order_number": "12345",
  "requestor_name": {"first": "John", "last": "Doe"},
  "requestor_email": "john.doe@example.com",
  "refund_type": "refund",
  "notes": "Schedule conflict"
}
```
**Expected**: 200 response, Slack message with approve/deny buttons

### 2. Order Not Found
```json
{
  "order_number": "99999",
  "requestor_email": "test@example.com",
  ...
}
```
**Expected**: 406 response, error Slack message, requestor emailed

### 3. Email Mismatch
```json
{
  "order_number": "12345",
  "requestor_email": "wrong@example.com",
  ...
}
```
**Expected**: 409 response, warning Slack message with edit/deny buttons

## Integration with CI/CD

These tests are designed to run in:
- ✅ **Local Development** - Quick feedback during development
- ✅ **GitHub Actions** - Automated testing on PRs and merges
- ✅ **Pre-commit Hooks** - Catch issues before commits

### GitHub Actions Integration
Add to `.github/workflows/tests.yml`:
```yaml
- name: Test Google Apps Script
  run: |
    cd GoogleAppsScripts/tests/process-refunds-exchanges
    ./run_tests.sh

- name: Test Backend API
  run: |
    cd backend
    pip install -r tests/requirements.txt
    pytest tests/test_refunds_api.py -v
```

## Debugging Failed Tests

### Common Issues

1. **Node.js not found**: Install Node.js 16+ 
2. **Python import errors**: Check backend dependencies
3. **Mock not working**: Verify import paths in tests
4. **Assertion failures**: Check expected vs actual data structures

### Verbose Output
```bash
# GAS tests with detailed logging
cd GoogleAppsScripts/tests/process-refunds-exchanges
node test_form_submission.js --verbose

# Backend tests with detailed output  
cd backend
pytest tests/test_refunds_api.py -vvs
```

## Updating Tests

When modifying the form processing or API:

1. **Update form fields**: Modify `test_form_submission.js` field extraction tests
2. **Change API payload**: Update both GAS and backend test expectations  
3. **New response codes**: Add test cases for new error conditions
4. **Slack message changes**: Mock new Slack service responses

## Security Notes

- ✅ No real API keys used in tests
- ✅ No actual emails sent during testing
- ✅ No real Slack messages posted
- ✅ All external services mocked
- ✅ Test data uses example.com emails
