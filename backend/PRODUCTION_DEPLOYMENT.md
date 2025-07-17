# Production Deployment Guide

## Overview

The BARS refunds workflow is now fully consolidated to use a single `ENVIRONMENT` variable that controls both application configuration and API call behavior.

## Environment Configuration

### ENVIRONMENT Values

| Value | API Calls | Slack Channel | Debug Messages | CORS | Docs |
|-------|-----------|---------------|----------------|------|------|
| `production` | **Real Shopify API** | `#refunds` | None | Restricted | Disabled |
| `development` | Mock calls | `#joe-test` | `[DEBUG]` prefix | Open | Enabled |
| `debug` | Mock calls | `#joe-test` | `[DEBUG]` prefix | Open | Enabled |
| `test` | Mock calls | `#joe-test` | `[DEBUG]` prefix | Open | Enabled |

### Required Environment Variables

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

## Production Readiness Validation

Run the validation script to ensure production readiness:

```bash
python3 validate_production_refunds.py
```

### Expected Production Validation Results

```
🎉 ALL VALIDATIONS PASSED! 🎉
✅ Environment Configuration - ENVIRONMENT=production
✅ Service Initialization - All services loaded
✅ Shopify Connectivity - API accessible  
✅ Workflow Components - Production API calls enabled
✅ Security Configuration - CORS restricted, docs disabled
```

## Production Workflow Behavior

### Order Cancellation (`ENVIRONMENT=production`)
- ✅ **Makes real Shopify API calls** to cancel orders
- ✅ **Calculates actual refund amounts** from order data
- ✅ **Updates Slack with production messages** (no debug prefix)
- ✅ **Uses #refunds channel** for notifications

### Refund Processing (`ENVIRONMENT=production`)
- ✅ **Creates real refunds** in Shopify via API
- ✅ **Processes actual payment refunds** 
- ✅ **Updates order status** in Shopify
- ✅ **Sends completion notifications** to #refunds

### Inventory Restocking (`ENVIRONMENT=production`)
- ✅ **Makes real GraphQL mutations** to adjust inventory
- ✅ **Updates actual Shopify variant quantities**
- ✅ **Handles API errors gracefully**
- ✅ **Logs all inventory changes**

## Deployment Steps

### 1. Render.com Deployment

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

### 2. Google Apps Script Update

Update your Google Apps Script to use the production URL:

```javascript
const BACKEND_URL = "https://barsbackend.onrender.com";
```

### 3. Slack Webhook Configuration

Update your Slack app webhook URL:
```
https://barsbackend.onrender.com/slack/webhook
```

## Testing Production Workflow

### Safe Production Testing

1. **Test with a small order first** (< $5)
2. **Verify webhook signature validation**
3. **Check Slack notifications in #refunds**
4. **Confirm Shopify order cancellation**
5. **Validate refund processing**
6. **Test inventory restocking**

### Testing Sequence

```bash
# 1. Validate production configuration
python3 validate_production_refunds.py

# 2. Check webhook endpoint
curl -X POST https://barsbackend.onrender.com/slack/webhook \
  -H "Content-Type: application/json" \
  -d '{"challenge":"test"}'

# 3. Monitor logs
# Check Render.com logs for production behavior
```

## Monitoring & Logs

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

## Security Notes

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

## Rollback Plan

If issues occur in production:

1. **Quick rollback:** Revert to previous git commit
2. **Disable webhook:** Remove webhook URL from Slack temporarily  
3. **Debug mode:** Set `ENVIRONMENT=debug` temporarily for testing
4. **Manual processing:** Process refunds manually while investigating

## Support

For production issues:

1. **Check validation:** Run `python3 validate_production_refunds.py`
2. **Review logs:** Check Render.com application logs
3. **Test connectivity:** Verify Shopify API access
4. **Slack status:** Confirm #refunds channel access

The refunds workflow is now production-ready with full API integration! 🎉 