# 🔐 BARS Google Apps Scripts - Secrets Audit Results

## Summary of Hardcoded Secrets Found

After scanning all Google Apps Script directories, here are the common secrets that need to be migrated to PropertiesService:

### 🛒 **Shopify Secrets** (CRITICAL)
- **`SHOPIFY_ACCESS_TOKEN`**: `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`
  - Found in: `payment-assistance-tags`, `process-refunds-exchanges`, `veteran-tags`, `product-variant-creation`, `waitlist-script`
  - **MOST CRITICAL** - This appears in 5+ scripts

### 💬 **Slack Bot Tokens** (CRITICAL)  
- **`SLACK_BOT_TOKEN_REFUNDS`**: `xoxb-2602080084-8649458379120-vR5W3EeryK5T4lNeDHA3lNwh`
- **`SLACK_BOT_TOKEN_LEADERSHIP`**: `xoxb-2602080084-8610961250834-FPVrAJgSXAImytWSf2GKL0Zq`
- **`SLACK_BOT_TOKEN_PAYMENT`**: `xoxb-2602080084-8601708038470-Z0eD6HhHG68MitN5xsfGstu5`
- **`SLACK_BOT_TOKEN_GENERAL`**: `xoxb-2602080084-8610974674770-K6rtRGsLT6obQfluL1fPpdEs`

### 📊 **Slack Channel IDs**
- Production Refunds: `C08J1EN7SFR`
- Test Channel: `C092RU7R6PL`  
- Payment Leadership: `C08J219EXN0`
- Payment General: `C086GG1H9BK`
- Leadership: `C02KAENF6`

### 🌐 **API Endpoints & URLs**
- Backend Production: `https://bars-backend.onrender.com`
- Lambda Schedule Changes: `https://6ltvg34u77der4ywcfk3zwr4fq0tcvvj.lambda-url.us-east-1.on.aws/`
- Lambda Payment Assistance: `https://xdakvg6v3jf5su2ioquv3izt2u0jcupn.lambda-url.us-east-1.on.aws/`
- Shopify GraphQL: `https://09fe59-3.myshopify.com/admin/api/2025-01/graphql.json`

### 📋 **Google Sheets IDs**
- Refunds Sheet: `11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw`
- Product Creation: `1w9Hj4JMmjTIQM5c8FbXuKnTMjVOLipgXaC6WqeSV_vc`
- Waitlist Responses: `1wFoayUoIx1PPOO0TtuS0Jnwb5hoIbgCd_kebMeYNzGQ`

## 📁 Secrets by Directory

### `payment-assistance-tags/`
- ✅ Shopify Access Token (CRITICAL)
- ✅ Slack Bot Tokens (4 different ones)
- ✅ Slack Channel IDs 
- ✅ BARS Logo URL
- ✅ Google Apps Script Execution URL

### `process-refunds-exchanges/`
- ✅ Shopify Access Token (CRITICAL)
- ✅ Slack Bot Tokens
- ✅ Slack Channel IDs
- ✅ Google Sheets IDs
- ✅ Backend API URLs
- ✅ BARS Logo URL

### `leadership-discount-codes/`
- ✅ Backend API URLs (Production & Local)
- ✅ Shopify Token (commented out but still visible)

### `veteran-tags/`
- ✅ Shopify Access Token (CRITICAL) 
- ✅ Shopify Store URL
- ✅ BARS Logo URL

### `product-variant-creation/`
- ✅ Shopify Access Token (CRITICAL)
- ✅ Shopify GraphQL & REST URLs
- ✅ Shopify Location GID
- ✅ Lambda URLs
- ✅ Local tunnel URLs

### `waitlist-script/`
- ✅ Shopify Access Token (CRITICAL)
- ✅ Google Apps Script Execution URL
- ✅ BARS Logo URL

### `parse-registration-info/`
- ✅ Google Sheets IDs
- ✅ Spreadsheet URLs

## 🚨 Security Risk Assessment

### **HIGH RISK** 🔴
- **Shopify Access Token**: Found in 5+ scripts, full admin access
- **Slack Bot Tokens**: Found in multiple scripts, can post to any channel

### **MEDIUM RISK** 🟡  
- **Slack Channel IDs**: Less sensitive but still should be centralized
- **Lambda URLs**: Could be misused if exposed

### **LOW RISK** 🟢
- **Google Sheets IDs**: Public sheets, low risk
- **BARS Logo URL**: Public asset, no risk

## ✅ Action Items

1. **IMMEDIATELY**: Run `setupSecrets()` in each Google Apps Script project
2. **Replace hardcoded values** with `getSecret()` calls
3. **Test each script** after migration
4. **Delete** the `unified-secrets-setup.js` file from each project after use
5. **Verify** no hardcoded secrets remain

## 🔧 Migration Examples

### Before:
```javascript
const SHOPIFY_ACCESS_TOKEN = "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";
const slackChannel = 'C08J1EN7SFR';
```

### After:
```javascript
const SHOPIFY_ACCESS_TOKEN = getSecret('SHOPIFY_ACCESS_TOKEN');
const slackChannel = getSlackChannel(true); // true for production
```

## 📊 Migration Progress

- [ ] `waitlist-script/`
- [ ] `product-variant-creation/`
- [ ] `parse-registration-info/`
- [ ] `process-refunds-exchanges/`
- [ ] `leadership-discount-codes/`
- [ ] `payment-assistance-tags/`
- [ ] `veteran-tags/`

**Total Scripts**: 7  
**Secrets to Migrate**: 25+  
**Critical Secrets**: 5  

---

⚠️ **SECURITY NOTE**: This audit file contains sensitive information. Keep it secure and delete after migration is complete.
