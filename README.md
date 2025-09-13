# 🏀 BigAppleRecSports (BARS)

A comprehensive system for managing recreational sports leagues including backend API, Google Apps Scripts automation, and AWS Lambda functions.

## 📦 Quick Start

```bash
# Install dependencies
make install

# Start development server
make start

# Run tests
make test-backend-unit
```

## 🏗️ Architecture

- **Backend API** (FastAPI) - Handles refunds, orders, Slack integration
- **Google Apps Scripts** - Form processing, spreadsheet automation
- **Lambda Functions** - Shopify webhooks, inventory management
- **Render Deployment** - Production hosting with auto-deployment

## 📦 Installation & Dependencies

### Development Setup
```bash
# Full development environment
make install

# Production dependencies only
make install-prod

# Manual installation
pip install -r requirements.txt
```

### Dependencies Overview
All dependencies are managed in the root `requirements.txt`:
- **Backend**: FastAPI, uvicorn, requests, pydantic
- **Testing**: pytest, pytest-asyncio, httpx
- **Lambda Functions**: typing-extensions (most use standard library)
- **Google Apps Scripts**: No Python dependencies (uses GAS runtime)

## 🚀 Development

### Backend Development
```bash
# Start server with auto-reload
make start

# Start with tunnel (new terminal)
make tunnel

# Combined (server + tunnel)
make dev
```

### Testing
```bash
# Unit tests (safe, mocked)
make test-backend-unit

# Integration tests (requires server)
make test-backend-integration

# Slack message tests
make test-backend-slack

# All backend tests
make test-backend-all

# Specific test
make test-specific TEST=backend/test_orders_api.py::test_fetch_order
```

### Code Quality
```bash
# Check compilation
make compile backend

# Run all checks
make ready backend
```

## 🔧 Configuration

### Environment Variables
Create `.env` file in backend directory:
```bash
# Required
SHOPIFY_STORE=your-store.myshopify.com
SHOPIFY_TOKEN=your_admin_api_token
SLACK_REFUNDS_BOT_TOKEN=xoxb-your-bot-token

# Optional
ENVIRONMENT=development
SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
```

### Slack Configuration
The system supports multiple Slack channels with different mention strategies:
- **Channel routing**: Based on request parameters
- **Mention strategies**: `user|username`, `sport|sport_name`, `none`
- **Dynamic API clients**: Per-channel configuration

## 📡 API Endpoints

### Refunds API
```bash
POST /refunds/send-to-slack
# Process refund requests and send to Slack

GET /orders/{order_number}
# Fetch order details from Shopify
```

### Webhooks
```bash
POST /webhooks/shopify/product/update
# Handle Shopify product update webhooks
```

See `docs/api/` for detailed API documentation.

## 🤖 Google Apps Scripts

### Projects
- **process-refunds-exchanges** - Refund form processing
- **parse-registration-info** - Registration data parsing
- **leadership-discount-codes** - Discount code management
- **product-variant-creation** - Product creation automation

### Deployment
```bash
cd GoogleAppsScripts
./deploy.sh project-name
```

## ⚡ Lambda Functions

### Functions
- **shopifyProductUpdateHandler** - Process Shopify webhooks
- **changePricesOfOpenAndWaitlistVariants** - Price management
- **MoveInventoryLambda** - Inventory transfers
- **setProductLiveByAddingInventory** - Product activation

### Local Development
```bash
# Setup lambda development environment
python3 scripts/setup_local_development.py
```

## 🚀 Deployment

### Render (Backend)
Automatic deployment via GitHub Actions on push to `main`:
- Triggers on: `backend/**`, `requirements.txt`, `render.yaml`
- Environment: Production with SSL certificates
- Secrets: Managed via Render dashboard

### Manual Deployment
```bash
# Deploy to Render
./scripts/deploy_to_render.sh

# Sync secrets
./scripts/sync_render_secrets.py
```

### Lambda Functions
Deployed via GitHub Actions:
- **Self-contained**: Auto-deploy on code changes
- **Layer-based**: Manual deployment only (safety)

### Google Apps Scripts
```bash
cd GoogleAppsScripts
./deploy.sh project-name
```

## 🧪 Testing Strategy

### Unit Tests
- **Location**: `backend/tests/unit/`
- **Scope**: Individual functions, mocked dependencies
- **Safe**: No external API calls

### Integration Tests
- **Location**: `backend/tests/integration/`
- **Scope**: End-to-end workflows
- **Requirements**: Running server, valid credentials

### Slack Tests
- **Message formatting**: Validates Slack block structure
- **Mock mode**: Tests without real Slack API calls
- **Block Kit**: Validates against Slack's Block Kit Builder

## 🔒 Security

### Secrets Management
- **Local**: `.env` files (gitignored)
- **Production**: Render environment variables
- **CI/CD**: GitHub Secrets
- **GAS**: Google Apps Script properties

### API Security
- **Webhook verification**: Shopify HMAC validation
- **Rate limiting**: Built into FastAPI
- **SSL/TLS**: Enforced in production

## 🛠️ Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
make install
```

**Compilation Failures**
```bash
# Check syntax and imports
make compile backend

# Fix virtual environment issues
make install
```

**Slack Integration**
```bash
# Test Slack connectivity
make test-backend-slack

# Validate message format
python backend/test_slack_message_formatting.py
```

**Lambda Development**
```bash
# Setup symlinks for imports
python3 scripts/setup_local_development.py

# Test lambda functions
cd lambda-functions && python3 tests/run_tests.py unit
```

## 📚 Documentation

This README provides a complete overview of the BARS system. For detailed information on specific topics, see the extended documentation:

| Document | Description | Quick Link |
|----------|-------------|------------|
| **[Contributing Guide](README_EXT/CONTRIBUTING.md)** | Development setup, workflow, testing standards | 🚀 [Start Here](README_EXT/CONTRIBUTING.md#development-setup) |
| **[Deployment Guide](README_EXT/DEPLOYMENT.md)** | Complete deployment procedures for all components | 🚀 [Deploy Now](README_EXT/DEPLOYMENT.md#deployment-overview) |
| **[Security Policy](README_EXT/SECURITY.md)** | Security guidelines and vulnerability reporting | 🔒 [Security](README_EXT/SECURITY.md) |
| **[Pre-Commit Guide](README_EXT/PRE_COMMIT_GUIDE.md)** | Pre-commit hooks setup and usage | 🔧 [Setup Hooks](README_EXT/PRE_COMMIT_GUIDE.md#quick-setup) |

### 📖 Documentation Organization

- **README.md** (this file) - Complete project overview and quick reference
- **README_EXT/** - Extended documentation for detailed topics
- **Inline comments** - Code files link back to relevant documentation sections

## 🔗 Quick Links

- [Render Dashboard](https://dashboard.render.com)
- [Shopify Admin](https://admin.shopify.com)
- [Slack Block Kit Builder](https://app.slack.com/block-kit-builder)
- [GitHub Actions](https://github.com/barswebadmin/BigAppleRecSports/actions)

## 📄 License

This project is proprietary to Big Apple Recreational Sports.

---

**Need help?** Check the troubleshooting section above or refer to the detailed guides in the root directory.
