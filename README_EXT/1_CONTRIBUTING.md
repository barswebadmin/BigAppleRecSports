# 🤝 Contributing to BARS

> 📖 **Navigation**: [← Back to README](../README.md) | [Deployment Guide](2_DEPLOYMENT.md) | [Security Policy](3_SECURITY.md) | [Pre-Commit Guide](4_PRE_COMMIT_GUIDE.md)

This guide covers development setup, workflow, and standards for contributing to the BARS project.

## 🚀 Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ (for GAS development)
- Git with pre-commit hooks
- AWS CLI (for Lambda functions)

### Backend Architecture

The BARS backend is a FastAPI application with modular services:

```
backend/
├── main.py                 # FastAPI application entry point
├── config.py               # Configuration and environment settings
├── services/               # Business logic services
│   ├── orders/            # Order management
│   ├── slack/             # Slack integration
│   ├── leadership/        # Leadership processing
│   └── webhooks/          # Webhook handlers
├── routers/               # API route handlers
│   ├── orders.py          # Order endpoints
│   ├── refunds.py         # Refund endpoints
│   ├── slack.py           # Slack webhook endpoints
│   └── leadership.py      # Leadership endpoints
├── models/                # Pydantic request/response models
└── utils/                 # Utility functions
```

### Key Backend Features
- **CSV Processing** - Convert Google Sheets data to leadership tags and discount codes
- **Smart Email Detection** - Automatically detects email columns in CSV data
- **Batch Processing** - Efficient processing of large customer lists
- **Shopify Integration** - GraphQL/REST API integration with customer management
- **Leadership Segmentation** - Automatic customer tagging and segment creation
- **Seasonal Discounts** - Winter, Spring, Summer, Fall discount code generation
- **Refund Management** - Complete order lifecycle (fetch, cancel, refund, restock)
- **Multi-channel Slack** - Sport-specific mentions and dynamic channel routing

### Initial Setup
```bash
# Clone and setup
git clone <repo-url>
cd BigAppleRecSports-alt

# Install dependencies
make install

# Setup pre-commit hooks
pip install pre-commit
pre-commit install

# Setup lambda development
python3 scripts/setup_local_development.py
```

## 🔄 Development Workflow

### 1. Branch Strategy
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: your descriptive message"

# Push and create PR
git push -u origin feature/your-feature-name
```

### 2. Pre-Commit Hooks
Our hooks ensure code quality:
- **Safe auto-fixes**: trailing whitespace, EOF newlines, formatting
- **Manual fixes required**: linting errors (prevents breaking changes)

```bash
# If pre-commit fails on linting:
ruff check backend/  # See issues
ruff check --fix backend/  # Fix if you trust the changes
```

### 3. Testing Requirements
All PRs must pass:
```bash
# Unit tests (required)
make test-backend-unit

# Integration tests (if touching API)
make test-backend-integration

# Compilation check
make compile backend
```

## 📝 Code Standards

### Python (Backend/Lambda)
- **Formatting**: Ruff (auto-applied)
- **Linting**: Ruff (manual fixes required)
- **Type hints**: Encouraged for new code
- **Docstrings**: Required for public functions

### JavaScript (Google Apps Scripts)
- **Style**: Google Apps Script conventions
- **Testing**: Manual testing in GAS environment
- **Documentation**: Inline comments for complex logic

### Git Commits
Follow conventional commits:
```bash
feat: add new feature
fix: bug fix
docs: documentation changes
style: formatting changes
refactor: code refactoring
test: adding tests
chore: maintenance tasks
```

## 🧪 Testing Guidelines

The BARS backend has a comprehensive testing suite covering unit tests, integration tests, and specialized Slack functionality tests.

### Test Types and Organization

#### Unit Tests (Mocked Services) 🧪
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

#### Integration Tests (Live Services) 🔗
**Location**: `test_*.py` files (without `_unit` suffix)
**Purpose**: Test real API endpoints with actual services
**Command**: `make test-integration` or specific commands

- **`test_error_codes.py`**: Tests HTTP endpoints with real server
  - ⚠️ **May send actual Slack messages**
  - Requires running server (`make start`)
  - Use `make test-integration-error-codes` to run these specifically

#### Quick Tests ⚡
**Command**: `make test-quick`
- Runs most critical unit tests only
- Fast feedback for development

### Slack Testing

#### Message Formatting Tests
The Slack service sends different types of messages based on refund request scenarios:

1. **Successful Refund Request** - When season info is parsed correctly and refund is calculated
2. **Fallback Message** - When season info cannot be parsed from product description
3. **Email Mismatch Error** - When requestor email doesn't match order customer email
4. **Order Not Found Error** - When the order number cannot be found in Shopify

**Test Coverage:**
- ✅ **Message Structure** - Proper Slack block formatting with dividers and sections
- ✅ **Content Accuracy** - All required fields are present and correctly formatted
- ✅ **Sport Group Mentions** - Correct team mentions (@kickball, @dodgeball, etc.)
- ✅ **URL Formatting** - Proper Shopify admin links for orders and products
- ✅ **Request Type Display** - Correct emoji and text for refund vs store credit
- ✅ **Error Handling** - Appropriate error messages for different failure scenarios
- ✅ **Conditional Content** - Notes, sheet links, and other optional content

#### Webhook Testing
The webhook functionality processes user actions from Slack messages and updates them with appropriate responses and next-step options.

**Test Structure:**
- **Primary Tests**: `routers/tests/test_slack_router.py`
- **Service Tests**: `services/slack/tests/test_message_builder.py`
- **Message Format Tests**: `tests/unit/test_slack_message_formatting.py`

**Test Runners:**
- **Webhook Tests Only**: `python3 run_slack_webhook_tests.py`
- **All Slack Tests**: `python3 run_slack_webhook_tests.py --all`
- **Make Commands**: `make test-slack-webhook` or `make test-slack-all`

**Debug Mode Message Format Validation:**

The tests specifically validate that debug mode produces messages matching this exact format:

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

### Running Tests

#### Make Commands
```bash
# All tests (recommended - unit tests only, safe)
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

#### Direct Commands

**Quick Run:**
```bash
python3 run_slack_tests.py
```

**Manual Run with pytest:**
```bash
python3 -m pytest test_slack_message_formatting.py -v
```

**Run Specific Test:**
```bash
python3 -m pytest test_slack_message_formatting.py::TestSlackMessageFormatting::test_fallback_season_info_message_format -v
```

**Webhook Tests:**
```bash
# Webhook tests only
python3 run_slack_webhook_tests.py

# All Slack tests
python3 run_slack_webhook_tests.py --all
```

### Test Best Practices

1. **Always run unit tests first** - They're fast and catch basic logic errors
2. **Use integration tests sparingly** - They may send real Slack messages
3. **Test message formatting changes** - Run Slack tests when modifying message content
4. **Validate webhook interactions** - Test button workflows when changing Slack functionality
5. **Check debug mode formatting** - Ensure debug messages follow the expected format

### Writing New Tests

#### Unit Test Example
```python
def test_calculate_refund_with_early_bird_discount():
    # Given
    order_data = {...}

    # When
    result = calculate_refund(order_data)

    # Then
    assert result["amount"] == 95.0
```

#### Integration Test Example
```python
def test_refund_api_endpoint():
    # Given
    client = TestClient(app)

    # When
    response = client.post("/refunds/send-to-slack", json=payload)

    # Then
    assert response.status_code == 200
```

### Troubleshooting Tests

- **Tests fail with import errors**: Check that you're running from the correct directory
- **Slack tests timeout**: Verify network connectivity and Slack configuration
- **Message format mismatches**: Check that actual Slack messages match expected format patterns
- **Webhook signature validation fails**: Ensure test secrets match configured values

## 🚀 Deployment Process

### Automatic Deployment
- **Backend**: Auto-deploys to Render on merge to `main`
- **Lambda**: Auto-deploys self-contained functions
- **GAS**: Manual deployment required

### Manual Deployment
```bash
# Backend to Render
./scripts/deploy_to_render.sh

# Google Apps Scripts
cd GoogleAppsScripts && ./deploy.sh project-name

# Lambda (if needed)
# Use GitHub Actions manual trigger
```

## 🔧 Local Development Tips

### Backend Development
```bash
# Start with auto-reload
make start

# Start with tunnel (separate terminal)
make tunnel

# Combined start (opens new terminal for tunnel)
make dev

# Check status
make status

# View tunnel URL
make url
```

### Environment Variables
Create `backend/.env`:
```bash
SHOPIFY_STORE=your-store.myshopify.com
SHOPIFY_TOKEN=your_shopify_token_here
SLACK_REFUNDS_BOT_TOKEN=your_slack_bot_token_here
ENVIRONMENT=development
```

### Lambda Development
```bash
# Setup imports (run once)
python3 scripts/setup_local_development.py

# Test lambda locally
cd lambda-functions/shopifyProductUpdateHandler
python3 lambda_function.py
```

### Google Apps Scripts
```bash
# Setup clasp authentication
cd GoogleAppsScripts
./scripts/setup-clasp-auth.sh

# Deploy project
./deploy.sh project-name
```

## 🐛 Debugging

### Backend Issues
```bash
# Check logs
make start  # Logs appear in terminal

# Test specific endpoint
curl -X POST http://localhost:8000/refunds/send-to-slack \
  -H "Content-Type: application/json" \
  -d '{"order_number": "12345", ...}'

# Run specific test
make test-specific TEST=backend/test_orders_api.py::test_fetch_order
```

### Lambda Issues
```bash
# Check lambda tests
cd lambda-functions
python3 tests/run_tests.py unit

# Test specific function
cd shopifyProductUpdateHandler
python3 -c "import lambda_function; print(lambda_function.lambda_handler({}, {}))"
```

### Slack Issues
```bash
# Test message formatting
python backend/test_slack_message_formatting.py

# Validate blocks
# Copy output to https://app.slack.com/block-kit-builder
```

## 🔒 Security Guidelines

### Secrets
- **Never commit**: API keys, tokens, passwords
- **Use .env files**: For local development
- **Environment variables**: For production
- **Rotate regularly**: API tokens and keys

### API Security
- **Validate input**: All user inputs
- **Rate limiting**: Implement for public endpoints
- **HTTPS only**: All production traffic
- **Webhook verification**: Validate Shopify HMAC

## 📊 Performance

### Backend
- **Response time**: < 2 seconds for API calls
- **Memory usage**: Monitor in Render dashboard
- **Database queries**: Optimize N+1 queries

### Lambda Functions
- **Cold start**: Keep functions warm if needed
- **Memory allocation**: Right-size for workload
- **Timeout**: Set appropriate timeouts

## 🚨 Error Handling

### Backend
```python
# Use structured error responses
raise HTTPException(
    status_code=400,
    detail={
        "error": "validation_error",
        "message": "Order number is required",
        "field": "order_number"
    }
)
```

### Lambda Functions
```python
# Return structured responses
return {
    "statusCode": 200,
    "body": json.dumps({
        "success": True,
        "message": "Processing complete"
    })
}
```

## 📚 Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Slack Block Kit**: https://app.slack.com/block-kit-builder
- **Shopify Admin API**: https://shopify.dev/api/admin
- **Google Apps Script**: https://developers.google.com/apps-script
- **AWS Lambda**: https://docs.aws.amazon.com/lambda/

## 🤔 Getting Help

1. **Check documentation**: README.md and this guide
2. **Search issues**: GitHub issues for similar problems
3. **Ask questions**: Create GitHub issue with `question` label
4. **Code review**: Request review on PRs for guidance

## 🎯 Best Practices

### Code Organization
- **Single responsibility**: One function, one purpose
- **Clear naming**: Functions and variables should be self-documenting
- **Error handling**: Always handle expected error cases
- **Logging**: Use appropriate log levels

### Git Workflow
- **Small commits**: Atomic, focused changes
- **Descriptive messages**: Clear commit messages
- **Clean history**: Squash fixup commits before merge
- **Branch cleanup**: Delete merged branches

### Testing
- **Test first**: Write tests before or with code
- **Edge cases**: Test boundary conditions
- **Error paths**: Test error scenarios
- **Documentation**: Tests serve as documentation
