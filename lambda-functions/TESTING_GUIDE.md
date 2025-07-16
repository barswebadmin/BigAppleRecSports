# 🧪 Lambda Functions Testing Guide

This guide explains how to create and run comprehensive tests for your BARS lambda functions to ensure code quality and prevent regressions.

## 🎯 **Testing Strategy Overview**

Our testing approach includes:

1. **Unit Tests** - Test individual functions and components with mocked dependencies
2. **Integration Tests** - Test complete lambda handler flows with realistic (but mocked) AWS services  
3. **Shared Utilities Tests** - Test the `bars_common_utils` layer functionality
4. **Regression Prevention** - Ensure future changes don't break existing logic

## 🚀 **Quick Start**

### **1. Run All Tests**
```bash
# From project root
cd lambda-functions
python3 tests/run_tests.py
```

### **2. Run Specific Test Types**
```bash
# Unit tests only
python3 tests/run_tests.py unit

# Integration tests only  
python3 tests/run_tests.py integration

# Tests for specific function
python3 tests/run_tests.py function --function MoveInventoryLambda

# Tests with coverage report
python3 tests/run_tests.py coverage
```

### **3. Run Tests During Development**
```bash
# Run tests matching a pattern
python3 tests/run_tests.py unit --pattern "test_veteran_to_early"

# Verbose output for debugging
python3 tests/run_tests.py unit --verbose
```

## 📁 **Test Structure**

```
lambda-functions/tests/
├── __init__.py                           # Tests package
├── conftest.py                          # Shared fixtures and setup
├── run_tests.py                         # Test runner script
├── unit/                                # Unit tests
│   ├── __init__.py
│   ├── test_move_inventory_lambda.py    # MoveInventoryLambda tests
│   ├── test_shopify_product_update_handler.py
│   └── test_bars_common_utils.py        # Lambda layer tests
├── integration/                         # Integration tests
│   ├── __init__.py
│   └── test_lambda_integration.py       # End-to-end flows
└── coverage_html/                       # Coverage reports (generated)
```

## 🔧 **Writing New Tests**

### **Unit Test Example**

```python
"""tests/unit/test_my_new_lambda.py"""
import pytest
import sys
import os
from unittest.mock import patch

# Add lambda function to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../MyNewLambda'))
from lambda_function import lambda_handler

class TestMyNewLambda:
    def test_successful_execution(self, sample_lambda_context):
        """Test successful lambda execution"""
        event = {"test": "data"}
        
        result = lambda_handler(event, sample_lambda_context)
        
        assert result['statusCode'] == 200
        assert result['body']['success'] is True
    
    def test_error_handling(self, sample_lambda_context):
        """Test error handling"""
        invalid_event = {}  # Missing required data
        
        result = lambda_handler(invalid_event, sample_lambda_context)
        
        assert result['statusCode'] == 500
        assert 'error' in result['body']
    
    @patch('my_module.external_api_call')
    def test_with_mocked_dependency(self, mock_api, sample_lambda_context):
        """Test with mocked external dependencies"""
        mock_api.return_value = {"success": True}
        event = {"action": "test"}
        
        result = lambda_handler(event, sample_lambda_context)
        
        assert result['statusCode'] == 200
        mock_api.assert_called_once()
```

### **Integration Test Example**

```python
"""tests/integration/test_my_integration.py"""
import pytest
from unittest.mock import patch

class TestMyLambdaIntegration:
    def test_complete_flow(self, mock_boto3_client, mock_shopify_utils, sample_lambda_context):
        """Test complete end-to-end flow"""
        from MyNewLambda.lambda_function import lambda_handler
        
        # Setup realistic event
        event = {
            'productId': 'gid://shopify/Product/12345',
            'action': 'update_inventory'
        }
        
        # Mock external services
        mock_shopify_utils['get_inventory'].return_value = {'quantity': 10}
        mock_boto3_client['scheduler'].create_schedule.return_value = {
            'ScheduleArn': 'arn:aws:scheduler:us-east-1:123:schedule/test'
        }
        
        result = lambda_handler(event, sample_lambda_context)
        
        # Verify complete flow
        assert result['statusCode'] == 200
        assert mock_shopify_utils['get_inventory'].called
        assert mock_boto3_client['scheduler'].create_schedule.called
```

## 🎨 **Available Test Fixtures**

### **AWS Service Mocks**
```python
def test_with_aws_services(mock_boto3_client, aws_credentials):
    """Use mocked AWS services"""
    scheduler = mock_boto3_client['scheduler']
    scheduler.create_schedule.return_value = {'ScheduleArn': 'test-arn'}
```

### **Shopify Service Mocks**
```python
def test_with_shopify(mock_shopify_utils, mock_shopify_env):
    """Use mocked Shopify services"""
    mock_shopify_utils['get_inventory_item_and_quantity'].return_value = {
        'inventoryItemId': 'test-id',
        'inventoryQuantity': 5
    }
```

### **Sample Events**
```python
def test_with_sample_events(sample_move_inventory_event, sample_shopify_product_event):
    """Use pre-built sample events"""
    # Events are already configured with realistic data
    pass
```

### **Lambda Context**
```python
def test_with_context(sample_lambda_context):
    """Use mocked Lambda context"""
    assert sample_lambda_context.function_name == 'test-function'
```

## 📊 **Test Categories & Patterns**

### **1. Happy Path Tests**
- Test successful execution with valid inputs
- Verify correct outputs and side effects
- Test different valid input variations

### **2. Error Handling Tests**
- Test with missing required fields
- Test with invalid data formats
- Test external service failures
- Test timeout scenarios

### **3. Edge Case Tests**
- Test boundary conditions
- Test empty/null inputs
- Test very large inputs
- Test concurrent execution scenarios

### **4. Integration Tests**
- Test complete lambda handler flows
- Test with realistic (but mocked) external services
- Test error propagation across components
- Test performance under load

## ⚙️ **Test Configuration**

### **Environment Variables**
Tests automatically set up these environment variables:
```python
AWS_DEFAULT_REGION=us-east-1
SHOPIFY_ACCESS_TOKEN=test_token
SHOPIFY_LOCATION_ID=test_location_id
```

### **Mock Configurations**
All external services are mocked by default:
- ✅ AWS services (boto3 clients)
- ✅ Shopify API calls
- ✅ HTTP requests (urllib.request)
- ✅ Time delays (wait_until_next_minute)

## 🔍 **Test Coverage**

### **Generate Coverage Reports**
```bash
# Run tests with coverage
python3 tests/run_tests.py coverage

# View HTML report
open lambda-functions/tests/coverage_html/index.html
```

### **Coverage Goals**
- **Unit Tests**: >90% line coverage
- **Integration Tests**: >80% feature coverage
- **Critical Functions**: 100% coverage

## 📋 **Testing Checklist for New Lambda Functions**

When adding a new lambda function, create tests for:

### **✅ Unit Tests**
- [ ] **Happy path execution** - Valid inputs produce expected outputs
- [ ] **Input validation** - Required fields are validated properly
- [ ] **Error handling** - Proper error responses for invalid inputs
- [ ] **External service mocking** - All AWS/Shopify calls are mocked
- [ ] **Edge cases** - Boundary conditions and unusual inputs
- [ ] **Type annotations** - Function signatures and imports work correctly

### **✅ Integration Tests**
- [ ] **Complete handler flow** - End-to-end execution with realistic events
- [ ] **Service interactions** - Proper calls to external services
- [ ] **Error propagation** - Errors are handled and reported correctly
- [ ] **Response format** - Proper HTTP response structure

### **✅ Regression Tests**
- [ ] **Existing functionality** - Ensure new changes don't break existing features
- [ ] **Performance** - No significant performance degradation
- [ ] **Backwards compatibility** - API contracts remain stable

## 🐛 **Debugging Tests**

### **Common Issues**

#### **Import Errors**
```bash
# Ensure proper Python path setup
export PYTHONPATH="/path/to/lambda-functions:$PYTHONPATH"

# Run tests from correct directory
cd lambda-functions
python3 tests/run_tests.py
```

#### **Mock Not Working**
```python
# Use patch.object for class methods
with patch.object(MyClass, 'method_name') as mock_method:
    mock_method.return_value = "test_value"

# Use patch for module functions
with patch('module.function_name') as mock_func:
    mock_func.return_value = "test_value"
```

#### **Fixture Not Found**
```python
# Make sure fixtures are imported correctly
# Check conftest.py for available fixtures
def test_example(mock_shopify_utils, sample_lambda_context):
    # Use fixtures here
    pass
```

### **Debugging Commands**
```bash
# Run single test with verbose output
python3 tests/run_tests.py unit --pattern "test_specific_function" --verbose

# Run tests and drop into debugger on failure
python3 -m pytest tests/unit/test_file.py::test_function --pdb

# Print all available fixtures
python3 -m pytest --fixtures tests/
```

## 🔄 **Continuous Integration**

### **Pre-commit Testing**
Add to your development workflow:
```bash
# Before committing changes
python3 tests/run_tests.py unit
python3 tests/run_tests.py integration
```

### **GitHub Actions Integration**
Add to `.github/workflows/lambda-tests.yml`:
```yaml
name: Lambda Function Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          cd lambda-functions
          pip install pytest boto3
      - name: Run tests
        run: |
          cd lambda-functions
          python3 tests/run_tests.py
```

## 📚 **Best Practices**

### **✅ Do:**
- **Write tests first** (TDD approach)
- **Use descriptive test names** that explain what is being tested
- **Mock all external dependencies** (AWS, Shopify, HTTP calls)
- **Test both success and failure scenarios**
- **Keep tests isolated** (no shared state between tests)
- **Use fixtures** for common setup/teardown
- **Assert specific values**, not just truthy/falsy
- **Test the public interface**, not internal implementation

### **❌ Don't:**
- **Test implementation details** - focus on behavior
- **Make real API calls** - always use mocks
- **Share state between tests** - use fresh fixtures
- **Write tests that depend on timing** - mock time functions
- **Skip edge cases** - they often reveal bugs
- **Ignore test failures** - fix them immediately

## 🎯 **Example: Adding Tests for New Lambda Function**

Let's say you're adding a new lambda function called `SendEmailNotification`:

### **1. Create Unit Tests**
```python
# tests/unit/test_send_email_notification.py
import pytest
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../SendEmailNotification'))
from lambda_function import lambda_handler

class TestSendEmailNotification:
    def test_successful_email_send(self, sample_lambda_context):
        event = {
            'recipient': 'test@example.com',
            'subject': 'Test Subject',
            'body': 'Test message'
        }
        
        with patch('boto3.client') as mock_boto3:
            mock_ses = mock_boto3.return_value
            mock_ses.send_email.return_value = {'MessageId': 'test-id'}
            
            result = lambda_handler(event, sample_lambda_context)
            
            assert result['statusCode'] == 200
            assert 'test-id' in result['body']['messageId']
            mock_ses.send_email.assert_called_once()
    
    def test_missing_recipient_error(self, sample_lambda_context):
        event = {
            'subject': 'Test Subject',
            'body': 'Test message'
            # Missing recipient
        }
        
        result = lambda_handler(event, sample_lambda_context)
        
        assert result['statusCode'] == 400
        assert 'recipient' in result['body']['error']
```

### **2. Create Integration Tests**
```python
# tests/integration/test_email_integration.py
def test_complete_email_flow(self, mock_boto3_client, sample_lambda_context):
    from SendEmailNotification.lambda_function import lambda_handler
    
    event = {
        'recipient': 'customer@example.com',
        'template': 'refund_notification',
        'data': {'order_number': '#12345', 'amount': '$25.00'}
    }
    
    # Mock SES service
    mock_boto3_client['ses'] = MagicMock()
    mock_boto3_client['ses'].send_templated_email.return_value = {
        'MessageId': 'msg-12345'
    }
    
    result = lambda_handler(event, sample_lambda_context)
    
    assert result['statusCode'] == 200
    assert result['body']['success'] is True
    mock_boto3_client['ses'].send_templated_email.assert_called_once()
```

### **3. Add to Test Runner**
```python
# In tests/run_tests.py, update the test_patterns dict:
test_patterns = {
    'MoveInventoryLambda': 'test_move_inventory',
    'shopifyProductUpdateHandler': 'test_shopify_product_update',
    'SendEmailNotification': 'test_send_email_notification',  # Add this
    # ... other functions
}
```

### **4. Run the Tests**
```bash
# Test the new function specifically
python3 tests/run_tests.py function --function SendEmailNotification

# Run all tests to ensure no regressions
python3 tests/run_tests.py
```

## 🏆 **Testing Success Metrics**

### **Code Quality Indicators**
- ✅ **All tests passing** consistently
- ✅ **Coverage > 90%** for critical functions
- ✅ **No skipped tests** without good reason
- ✅ **Fast test execution** (< 30 seconds total)
- ✅ **Clear test failure messages** for debugging

### **Regression Prevention**
- ✅ **New features have tests** before deployment
- ✅ **Bug fixes include regression tests**
- ✅ **Tests run in CI/CD pipeline**
- ✅ **Failed deployments are blocked** by test failures

---

## 🎉 **You're Ready to Test!**

With this comprehensive testing framework, you can:
- **Prevent regressions** by catching breaking changes early
- **Refactor confidently** knowing tests will catch issues
- **Document behavior** through executable test specifications
- **Improve code quality** through test-driven development

Start by running the existing tests, then add tests for any new lambda functions you create! 🚀 