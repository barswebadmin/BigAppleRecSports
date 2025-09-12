# Backend Tests Organization

## 📁 Test Structure

```
tests/
├── unit/                           # Unit tests (mock dependencies)
│   ├── test_error_codes_unit.py   # Error code unit tests
│   ├── test_order_fetching.py     # Order service unit tests (with mocks)
│   ├── test_refunds_endpoint.py   # Refunds endpoint JSON validation tests
│   └── test_slack_message_formatting.py  # Slack message formatting tests
├── integration/                    # Integration tests (real dependencies)
│   ├── test_actual_refunds_api.py  # End-to-end refunds API test
│   ├── test_error_codes.py        # Error code integration tests
│   ├── test_mute_exceptions.py    # Exception handling integration tests
│   ├── test_orders_api.py         # Orders API integration tests
│   └── test_sheet_link.py         # Sheet link integration tests
└── README.md                      # This file
```

## 🧪 Test Categories

### **Unit Tests** (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Dependencies**: Mocked using `unittest.mock`
- **Speed**: Fast execution
- **Examples**:
  - JSON schema validation
  - Business logic functions
  - Service layer methods with mocked external calls

### **Integration Tests** (`tests/integration/`)
- **Purpose**: Test components working together with real dependencies
- **Dependencies**: Real external services (Shopify API, Slack API, etc.)
- **Speed**: Slower execution, requires network calls
- **Examples**:
  - End-to-end API endpoint testing
  - Real Shopify API calls
  - Real Slack API calls

## 🚀 Running Tests

### Run All Tests
```bash
cd backend
python -m pytest tests/ -v
```

### Run Unit Tests Only
```bash
cd backend
python -m pytest tests/unit/ -v
```

### Run Integration Tests Only
```bash
cd backend
python -m pytest tests/integration/ -v
```

### Run Specific Test
```bash
cd backend
python -m pytest tests/unit/test_refunds_endpoint.py::TestRefundsEndpointJSONValidation::test_pydantic_model_validation_valid_refund -v
```

## 🔧 Test Dependencies

### **Unit Tests Requirements**
- `pytest`
- `unittest.mock` (built-in)
- `pydantic`
- `fastapi`

### **Integration Tests Requirements**
- All unit test requirements
- `requests` (for HTTP calls)
- Working internet connection
- Valid API credentials in environment

## 📝 Test File Naming Convention

- **Unit tests**: `test_<component>_<feature>.py`
- **Integration tests**: `test_<endpoint/flow>_<integration_type>.py`
- **Test classes**: `Test<ComponentName><Feature>`
- **Test methods**: `test_<what_is_being_tested>`

## 🎯 Recently Added Tests

### **Order Fetching Fix (SSL Certificate Issue)**
- **Unit**: `tests/unit/test_order_fetching.py`
  - Tests OrdersService with mocked Shopify API
  - Tests SSL fallback mechanism
  - Tests error handling scenarios

- **Integration**: `tests/integration/test_actual_refunds_api.py`
  - Tests real API endpoint with exact frontend JSON
  - Confirms SSL certificate fix works end-to-end
  - Tests both Shopify API and backend API

### **JSON Schema Validation**
- **Unit**: `tests/unit/test_refunds_endpoint.py`
  - Tests exact JSON format from Google Apps Script
  - Validates required/optional fields
  - Tests error handling for malformed JSON
  - Ensures frontend compatibility

## 🛡️ Best Practices

1. **Isolation**: Unit tests should not depend on external services
2. **Mocking**: Use `unittest.mock` to mock external dependencies
3. **Real Testing**: Integration tests should use real services when safe
4. **Error Cases**: Test both success and failure scenarios
5. **Documentation**: Include docstrings explaining what each test validates
6. **Naming**: Use descriptive test method names that explain the scenario

## 🔍 Debugging Test Failures

### Check Test Output
```bash
python -m pytest tests/unit/test_order_fetching.py -v -s
```

### Run Single Test with Full Output
```bash
python -m pytest tests/unit/test_order_fetching.py::TestOrderFetching::test_orders_service_fetch_by_order_name_success -v -s --tb=long
```

### Skip Integration Tests (for faster development)
```bash
python -m pytest tests/unit/ -v
```
