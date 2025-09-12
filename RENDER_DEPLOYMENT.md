# 🚀 Render Deployment Guide

This guide covers deploying BARS backend to Render with automatic secret synchronization.

## 🔧 **One-Time Setup**

### 1. Get Render Credentials
- Go to [Render Dashboard](https://dashboard.render.com)
- Navigate to **Account Settings** → **API Keys**
- Create a new API key and copy it
- Get your Service ID from your service dashboard URL: `srv-xxxxxxxxx`

### 2. Configure Local Environment
```bash
# Run the setup script
./setup_render_env.sh

# Restart your terminal or reload profile
source ~/.zshrc
```

## 🚀 **Deployment Commands**

### Quick Deploy (Recommended)
```bash
# Sync secrets and deploy in one command
./scripts/deploy_to_render.sh
```

### Step-by-Step Deploy
```bash
# 1. Test what would change (dry run)
./scripts/deploy_to_render.sh --dry-run

# 2. Sync secrets only (no deployment)
./scripts/deploy_to_render.sh --secrets-only

# 3. Deploy (if secrets were already synced)
./scripts/deploy_to_render.sh
```

### Advanced Usage
```bash
# Direct script usage
python3 scripts/pre_deploy_render.py --dry-run       # Preview changes
python3 scripts/pre_deploy_render.py --deploy        # Sync + Deploy
python3 scripts/pre_deploy_render.py                 # Sync only
```

## 📋 **What Gets Synced**

The deployment script will:

1. **📁 Read your `.env` file** - All environment variables
2. **☁️ Fetch current Render variables** - Compare with local
3. **🔄 Sync differences** - Add missing, update changed values
4. **🚀 Deploy** - Trigger new deployment (if requested)
5. **⏳ Wait** - Monitor deployment status until complete

## 🔍 **Environment Variables**

### Required for Deployment:
- `RENDER_API_KEY` - Your Render API key
- `RENDER_SERVICE_ID` - Your service ID (srv-xxxxx)

### Synced from `.env`:
- `ENVIRONMENT=production` - **Important**: Set this for production!
- `SHOPIFY_TOKEN` - Your Shopify access token
- `SLACK_REFUNDS_BOT_TOKEN` - Slack bot token
- `SLACK_SIGNING_SECRET` - Slack webhook verification
- `SHOPIFY_WEBHOOK_SECRET` - Shopify webhook verification
- `GAS_WAITLIST_FORM_WEB_APP_URL` - Google Apps Script URL

## ⚠️ **Important Notes**

### Before First Production Deploy:
1. **Set `ENVIRONMENT=production`** in your `.env` file
2. **Test with dry-run** to see what changes
3. **Monitor `#registration-refunds`** channel after deploy

### Production vs Development:
- `ENVIRONMENT=production` → Real Slack messages to `#registration-refunds`
- `ENVIRONMENT=development` → Mock messages to `#joe-test`

### Secret Safety:
- ✅ API keys stored in shell profile (not in repo)
- ✅ Local `.env` file is gitignored
- ✅ Dry-run mode to preview changes
- ✅ Only updates changed/missing variables

## 🛠️ **Troubleshooting**

### "RENDER_API_KEY not set"
```bash
# Re-run setup
./setup_render_env.sh

# Or manually add to ~/.zshrc
export RENDER_API_KEY="your_key_here"
export RENDER_SERVICE_ID="srv-your_id_here"
```

### "Failed to fetch Render environment variables"
- Check your API key is correct
- Verify service ID format: `srv-xxxxxxxxx`
- Ensure API key has permissions for the service

### "Deployment failed"
- Check Render dashboard for build logs
- Verify all required environment variables are set
- Check for any breaking changes in recent commits

## 📈 **Workflow Examples**

### Regular Update Deploy:
```bash
# 1. Make code changes
git add . && git commit -m "Update feature"

# 2. Update secrets if needed
echo "NEW_FEATURE_FLAG=true" >> .env

# 3. Deploy with secret sync
./scripts/deploy_to_render.sh

# 4. Monitor deployment
# Script will wait and show status
```

### Emergency Secret Update:
```bash
# Update secrets without code deploy
./scripts/deploy_to_render.sh --secrets-only

# Then manually deploy in Render dashboard if needed
```

### Production Readiness Check:
```bash
# Validate production configuration
cd backend && python validate_production_refunds.py

# Test deployment (no changes made)
./scripts/deploy_to_render.sh --dry-run
```

---

**🎉 Happy Deploying!** Your secrets will always be in sync with your code.
