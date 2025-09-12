# BARS Backend Deployment & Development Guide

This comprehensive guide covers deployment, testing, and version management for the BARS backend application.

## 🚀 Production Deployment

### Environment Configuration

#### ENVIRONMENT Values

| Value | API Calls | Slack Channel | Debug Messages | CORS | Docs |
|-------|-----------|---------------|----------------|------|------|
| `production` | **Real Shopify API** | `#refunds` | None | Restricted | Disabled |
| `development` | Mock calls | `#joe-test` | `[DEBUG]` prefix | Open | Enabled |
| `debug` | Mock calls | `#joe-test` | `[DEBUG]` prefix | Open | Enabled |
| `test` | Mock calls | `#joe-test` | `[DEBUG]` prefix | Open | Enabled |

#### Required Environment Variables

**Production (Required):**
```bash
ENVIRONMENT=production
SHOPIFY_TOKEN=shpat_your_actual_token_here
SLACK_REFUNDS_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-slack-signing-secret
```

**Development (Optional):**
```bash
ENVIRONMENT=development  # or debug/test
SHOPIFY_TOKEN=test_token  # can be test token
SLACK_REFUNDS_BOT_TOKEN=xoxb-test-token
SLACK_SIGNING_SECRET=test-secret
```

### Production Readiness Validation

Run the validation script to ensure production readiness:

```bash
python3 validate_production_refunds.py
```

#### Expected Production Validation Results

```
🎉 ALL VALIDATIONS PASSED! 🎉
✅ Environment Configuration - ENVIRONMENT=production
✅ Service Initialization - All services loaded
✅ Shopify Connectivity - API accessible  
✅ Workflow Components - Production API calls enabled
✅ Security Configuration - CORS restricted, docs disabled
```

### Deployment Steps

#### 1. Render.com Deployment

**Environment Variables:**
```bash
ENVIRONMENT=production
SHOPIFY_TOKEN=shpat_your_real_token_here
SLACK_REFUNDS_BOT_TOKEN=xoxb-your-real-bot-token  
SLACK_SIGNING_SECRET=your-real-signing-secret
```

**Deploy:**
```bash
git push origin main  # Triggers automatic deployment
```

#### 2. Google Apps Script Update

Update your Google Apps Script to use the production URL:

```javascript
const BACKEND_URL = "https://barsbackend.onrender.com";
```

#### 3. Slack Webhook Configuration

Update your Slack app webhook URL:
```
https://barsbackend.onrender.com/slack/webhook
```

### Production Workflow Behavior

#### Order Cancellation (`ENVIRONMENT=production`)
- ✅ **Makes real Shopify API calls** to cancel orders
- ✅ **Calculates actual refund amounts** from order data
- ✅ **Updates Slack with production messages** (no debug prefix)
- ✅ **Uses #refunds channel** for notifications

#### Refund Processing (`ENVIRONMENT=production`)
- ✅ **Creates real refunds** in Shopify via API
- ✅ **Processes actual payment refunds** 
- ✅ **Updates order status** in Shopify
- ✅ **Sends completion notifications** to #refunds

#### Inventory Restocking (`ENVIRONMENT=production`)
- ✅ **Makes real GraphQL mutations** to adjust inventory
- ✅ **Updates actual Shopify variant quantities**
- ✅ **Handles API errors gracefully**
- ✅ **Logs all inventory changes**

## 🧪 Testing Guide

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

#### Integration Tests (Live Services) 🔗
**Location**: `test_*.py` files (without `_unit` suffix)  
**Purpose**: Test real API endpoints with actual services  
**Command**: `make test-integration` or specific commands

- **`test_error_codes.py`**: Tests HTTP endpoints with real server
  - ⚠️ **May send actual Slack messages**
  - Requires running server (`make start`)

### Running Tests

#### Default Test Suite (Recommended)
```bash
make test
```
Runs all unit tests with mocked services - **safe, no external API calls**.

#### Unit Tests Only
```bash
make test-unit
```

#### Integration Tests (Use Carefully)
```bash
# Start server first
make start

# In another terminal
make test-integration-error-codes
```
⚠️ **Warning**: These may send actual Slack messages to #refunds channel.

### Test Coverage
- **406**: Order not found in Shopify
- **409**: Email mismatch (requestor email ≠ order customer email)  
- **200**: Successful refund request processing
- **500**: Internal server errors (Slack failures, etc.)

## 🚀 Version Management

### Semantic Versioning
The backend follows [Semantic Versioning (SemVer)](https://semver.org/):
- **MAJOR** (`2.0.0`): Breaking changes, API changes
- **MINOR** (`1.1.0`): New features, backwards compatible
- **PATCH** (`1.0.1`): Bug fixes, backwards compatible
- **BUILD** (`1.0.0.4`): Auto-incremented build number

### Automatic Detection
The system analyzes your commits and determines the version bump:

| Change Type | Triggers | Example |
|-------------|----------|---------|
| **Major** | API breaking changes, `BREAKING:` in commit | `feat: BREAKING change to API` |
| **Minor** | New features, `feat:` commits, API additions | `feat: add new endpoint` |
| **Patch** | Bug fixes, `fix:` commits | `fix: resolve authentication issue` |
| **Build** | Other changes | `docs: update README` |

### Conventional Commits

Use these commit prefixes for automatic categorization:

```bash
# Features (minor version bump)
feat: add new leadership endpoint
feature: implement email validation

# Bug fixes (patch version bump)  
fix: resolve CORS issue
bugfix: fix authentication timeout
patch: update error handling

# Breaking changes (major version bump)
feat: BREAKING change to API structure
BREAKING: remove deprecated endpoints

# Other changes (build increment only)
docs: update API documentation
refactor: improve code structure
test: add integration tests
style: fix formatting
```

### Development Workflow
```bash
# 1. Create feature branch and make changes
git checkout -b feature/email-validation
vi backend/services/leadership_service.py

# 2. Commit with conventional format (no version update yet)
git add backend/services/leadership_service.py
git commit -m "feat: add email validation to leadership processing"

# 3. Push and create PR
git push origin feature/email-validation

# 4. Merge PR to main - version updates automatically! 🎉
```

## 🔒 Security

### Production Security Features
- ✅ **CORS restricted** to approved domains only
- ✅ **API docs disabled** (`/docs` returns 404)
- ✅ **Slack signature validation** on all webhooks
- ✅ **Environment variables** for all secrets
- ✅ **HTTPS only** for all API endpoints

### Security Checklist
- [ ] All tokens stored in environment variables (not code)
- [ ] Slack webhook signature validation enabled
- [ ] CORS origins restricted to production domains
- [ ] API documentation disabled in production
- [ ] Logs don't contain sensitive data

## 📊 Monitoring & Logs

### Production Logs
Monitor these log patterns in production:

```
🚀 PRODUCTION MODE: Making real API calls
🏭 PRODUCTION MODE: Making real refund API call  
🏭 PRODUCTION MODE: Making real inventory adjustment
✅ Successfully adjusted inventory for variant X by 1
```

### Error Handling
Production errors are logged with full context:

```
❌ Failed to adjust Shopify inventory: HTTP 422: User errors
❌ Failed to create refund: Insufficient refund amount
❌ Order cancellation failed: Order already cancelled
```

## 🆘 Rollback Plan

If issues occur in production:

1. **Quick rollback:** Revert to previous git commit
2. **Disable webhook:** Remove webhook URL from Slack temporarily  
3. **Debug mode:** Set `ENVIRONMENT=debug` temporarily for testing
4. **Manual processing:** Process refunds manually while investigating

## 📞 Support

For production issues:

1. **Check validation:** Run `python3 validate_production_refunds.py`
2. **Review logs:** Check Render.com application logs
3. **Test connectivity:** Verify Shopify API access
4. **Slack status:** Confirm #refunds channel access

The refunds workflow is now production-ready with full API integration! 🎉
