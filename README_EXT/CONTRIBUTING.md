# 🤝 Contributing to BARS

> 📖 **Navigation**: [← Back to README](../README.md) | [Deployment Guide](DEPLOYMENT.md) | [Security Policy](SECURITY.md) | [Pre-Commit Guide](PRE_COMMIT_GUIDE.md)

This guide covers development setup, workflow, and standards for contributing to the BARS project.

## 🚀 Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ (for GAS development)
- Git with pre-commit hooks

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

### Unit Tests
- **Location**: `backend/tests/unit/`
- **Scope**: Test individual functions with mocks
- **Coverage**: Aim for >80% on new code
- **Naming**: `test_function_name_scenario`

```python
def test_calculate_refund_with_early_bird_discount():
    # Given
    order_data = {...}

    # When
    result = calculate_refund(order_data)

    # Then
    assert result["amount"] == 95.0
```

### Integration Tests
- **Location**: `backend/tests/integration/`
- **Scope**: Test full workflows
- **Requirements**: Running server, test credentials
- **Cleanup**: Always clean up test data

### Slack Tests
- **Mock mode**: Use `MockSlackApiClient` for testing
- **Block validation**: Ensure messages render correctly
- **Error scenarios**: Test error handling paths

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
SHOPIFY_STORE=test-store.myshopify.com
SHOPIFY_TOKEN=test_token
SLACK_REFUNDS_BOT_TOKEN=test_slack_token
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
