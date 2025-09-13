# 🚀 Deployment Guide

> 📖 **Navigation**: [← Back to README](../README.md) | [Contributing Guide](CONTRIBUTING.md) | [Security Policy](SECURITY.md) | [Pre-Commit Guide](PRE_COMMIT_GUIDE.md)

Complete deployment procedures for all BARS components.

## 🎯 Deployment Overview

| Component | Method | Trigger | Environment |
|-----------|--------|---------|-------------|
| Backend API | Render | Auto (main branch) | Production |
| Lambda Functions | GitHub Actions | Auto/Manual | AWS |
| Google Apps Scripts | Manual | clasp deploy | Google |

## 🔧 Backend Deployment (Render)

### Automatic Deployment
Deploys automatically when pushing to `main` branch with changes to:
- `backend/**`
- `requirements.txt`
- `render.yaml`
- `shared-utilities/**`

### Manual Deployment
```bash
# Deploy to Render
./scripts/deploy_to_render.sh

# Sync environment variables
./scripts/sync_render_secrets.py
```

### One-Time Render Setup

#### 1. Get Render Credentials
- Go to [Render Dashboard](https://dashboard.render.com)
- Navigate to **Account Settings** → **API Keys**
- Create API key and copy it
- Get Service ID from service dashboard URL: `srv-xxxxxxxxx`

#### 2. Configure Local Environment
```bash
# Run setup script
./setup_render_env.sh

# Restart terminal or reload profile
source ~/.zshrc
```

#### 3. GitHub Secrets Setup
Add to GitHub repository secrets:
```bash
RENDER_API_KEY=rnd_xxxxxxxxxxxxx
RENDER_SERVICE_ID=srv-xxxxxxxxxxxxx
```

### Environment Variables
Set in Render dashboard:
```bash
# Required
SHOPIFY_STORE=your-store.myshopify.com
SHOPIFY_TOKEN=shpat_xxxxxxxxxxxxx
SLACK_REFUNDS_BOT_TOKEN=xoxb-xxxxxxxxxxxxx

# SSL Configuration
SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Environment
ENVIRONMENT=production
```

### Deployment Verification
```bash
# Check deployment status
curl https://your-app.onrender.com/health

# Check logs in Render dashboard
# Monitor response times and errors
```

## ⚡ Lambda Functions Deployment

### Automatic Deployment (Self-Contained)
Auto-deploys on changes to:
- `lambda-functions/shopifyProductUpdateHandler/**`
- `shared-utilities/**`

Functions deployed:
- **shopifyProductUpdateHandler** - Shopify webhook processing

### Manual Deployment (Layer-Based)
For safety, lambda layers require manual deployment:

```bash
# Via GitHub Actions
# 1. Go to Actions tab
# 2. Select "Deploy Lambda Layer"
# 3. Click "Run workflow"
# 4. Type "CONFIRM" when prompted
```

### Local Testing
```bash
# Setup lambda development
python3 scripts/setup_local_development.py

# Test specific function
cd lambda-functions/shopifyProductUpdateHandler
python3 lambda_function.py

# Run lambda test suite
cd lambda-functions
python3 tests/run_tests.py unit
```

### AWS Configuration
Lambda functions require these environment variables:
```bash
# Set in AWS Lambda console
ENVIRONMENT=production
SHOPIFY_WEBHOOK_SECRET=your_webhook_secret
```

## 🤖 Google Apps Scripts Deployment

### Prerequisites
```bash
# Install clasp globally
npm install -g @google/clasp

# Setup authentication
cd GoogleAppsScripts
./scripts/setup-clasp-auth.sh
```

### Deploy Individual Project
```bash
cd GoogleAppsScripts

# Deploy specific project
./deploy.sh process-refunds-exchanges
./deploy.sh parse-registration-info
./deploy.sh leadership-discount-codes
./deploy.sh product-variant-creation
```

### Deploy All Projects
```bash
cd GoogleAppsScripts

# Deploy all projects
for project in projects/*/; do
  project_name=$(basename "$project")
  ./deploy.sh "$project_name"
done
```

### Deployment Verification
1. **Check Google Apps Script dashboard**
2. **Test form submissions**
3. **Verify spreadsheet updates**
4. **Check webhook endpoints**

### Environment Configuration
Set in Google Apps Script project properties:
```javascript
// In each project's properties
BACKEND_API_URL_PROD=https://your-app.onrender.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SHOPIFY_STORE_URL=https://your-store.myshopify.com
```

## 🔄 CI/CD Pipeline

### GitHub Actions Workflows

#### Backend Deployment
- **File**: `.github/workflows/deploy-to-render.yml`
- **Trigger**: Push to main (backend changes)
- **Steps**: Install deps → Validate → Deploy to Render

#### Lambda Deployment
- **File**: `.github/workflows/deploy-self-contained-lambdas.yml`
- **Trigger**: Push to main (lambda changes)
- **Steps**: Package → Deploy to AWS

#### Validation Only
- **File**: `.github/workflows/validate-changes.yml`
- **Trigger**: Documentation, test changes
- **Steps**: Lint → Test → Validate (no deployment)

### Deployment Notifications
All deployments send notifications:
- ✅ **Success**: Deployment completed
- ❌ **Failure**: Check logs and retry
- 🔄 **In Progress**: Deployment running

## 🔒 Security & Secrets

### Secret Management
| Environment | Method | Examples |
|-------------|--------|----------|
| Local | `.env` files | `backend/.env` |
| Render | Dashboard | Environment variables |
| GitHub Actions | Repository secrets | `RENDER_API_KEY` |
| AWS Lambda | Console | Environment variables |
| Google Apps Scripts | Properties | Script properties |

### Secret Rotation
```bash
# Rotate Shopify tokens
# 1. Generate new token in Shopify admin
# 2. Update in all environments
# 3. Test deployments
# 4. Revoke old token

# Rotate Slack tokens
# 1. Generate new bot token
# 2. Update SLACK_REFUNDS_BOT_TOKEN everywhere
# 3. Test Slack integration
# 4. Revoke old token
```

## 🚨 Rollback Procedures

### Backend Rollback
```bash
# Via Render dashboard
# 1. Go to service dashboard
# 2. Click "Rollback" on previous deployment
# 3. Confirm rollback

# Via GitHub
# 1. Revert problematic commit
# 2. Push to main (triggers auto-deployment)
```

### Lambda Rollback
```bash
# Via AWS Console
# 1. Go to Lambda function
# 2. Select "Versions" tab
# 3. Promote previous version to $LATEST

# Via GitHub Actions
# 1. Revert commit with lambda changes
# 2. Push to main (triggers deployment)
```

### Google Apps Scripts Rollback
```bash
# Via Google Apps Script dashboard
# 1. Open project
# 2. Go to "Manage versions"
# 3. Restore previous version

# Via clasp
cd GoogleAppsScripts
clasp versions  # List versions
clasp version [version_number]  # Restore version
```

## 📊 Monitoring & Health Checks

### Backend Monitoring
- **Render Dashboard**: Response times, memory usage, logs
- **Health Endpoint**: `GET /health`
- **Error Tracking**: Application logs
- **Uptime**: Render built-in monitoring

### Lambda Monitoring
- **CloudWatch**: Function metrics, logs, errors
- **X-Ray**: Distributed tracing (if enabled)
- **Alarms**: Set up for error rates, duration

### Google Apps Scripts Monitoring
- **Execution Transcript**: In GAS editor
- **Trigger History**: Failed executions
- **Email Notifications**: On script failures

## 🔧 Troubleshooting

### Common Deployment Issues

#### Backend Deployment Fails
```bash
# Check Render logs
# Common issues:
# - Missing environment variables
# - Requirements.txt issues
# - Port binding problems

# Fix:
# 1. Verify environment variables
# 2. Test locally first
# 3. Check requirements.txt syntax
```

#### Lambda Deployment Fails
```bash
# Check GitHub Actions logs
# Common issues:
# - Package size too large
# - Missing dependencies
# - Permission issues

# Fix:
# 1. Optimize package size
# 2. Check AWS permissions
# 3. Verify function configuration
```

#### Google Apps Scripts Deployment Fails
```bash
# Check clasp output
# Common issues:
# - Authentication expired
# - Project permissions
# - Syntax errors

# Fix:
clasp login  # Re-authenticate
clasp push   # Push changes
clasp deploy # Deploy new version
```

### Emergency Procedures

#### Complete System Outage
1. **Check Render status**: https://status.render.com
2. **Verify AWS status**: https://status.aws.amazon.com
3. **Check Google Workspace status**: https://www.google.com/appsstatus
4. **Rollback recent deployments**
5. **Contact support if needed**

#### Data Loss Prevention
- **Database backups**: Render automatic backups
- **Code backups**: Git repository
- **Configuration backups**: Environment variable exports
- **Google Sheets**: Built-in version history

## 📞 Support Contacts

- **Render Support**: https://render.com/support
- **AWS Support**: AWS Console → Support
- **Google Workspace**: Google Admin Console → Support
- **GitHub Support**: GitHub Settings → Support

---

**Need immediate help?** Check the troubleshooting section or contact the appropriate support channel above.
