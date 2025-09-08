# 🔧 Token Migration Guide

## Token Consolidation Summary

I've cleaned up the Slack bot tokens from **11 duplicates** down to **4 unique tokens**:

### ✅ **Consolidated Token Mapping**

| **New Standard Key** | **Token Value** | **Used For** | **Replace These Old Values** |
|---------------------|-----------------|--------------|------------------------------|
| `SLACK_BOT_TOKEN_REFUNDS` | `xoxb-...-vR5W3EeryK5T4lNeDHA3lNwh` | Refunds bot | (unique) |
| `SLACK_BOT_TOKEN_LEADERSHIP` | `xoxb-...-FPVrAJgSXAImytWSf2GKL0Zq` | Leadership, Joe test, Joe DM | `SLACK_BOT_TOKEN_JOE_TEST`, `SLACK_BOT_TOKEN_JOE_DM`, `SLACK_BOT_TOKEN_JOE_TEST_DM` |
| `SLACK_BOT_TOKEN_PAYMENT` | `xoxb-...-Z0eD6HhHG68MitN5xsfGstu5` | Payment, Exec Leadership | `SLACK_BOT_TOKEN_EXEC_LEADERSHIP` |
| `SLACK_BOT_TOKEN_GENERAL` | `xoxb-...-K6rtRGsLT6obQfluL1fPpdEs` | General, Web, Alternate | `SLACK_BOT_TOKEN_WEB`, `SLACK_BOT_TOKEN_ALTERNATE` |

## 🔄 **Code Migration Instructions**

### **Step 1: Use the Helper Function (Recommended)**

```javascript
// BEFORE (hardcoded):
bearerToken: 'xoxb-2602080084-8610961250834-FPVrAJgSXAImytWSf2GKL0Zq'

// AFTER (purpose-based):
bearerToken: getSlackBotToken('leadership')
```

**Available purposes:**
- `'refunds'` → `SLACK_BOT_TOKEN_REFUNDS`
- `'leadership'` → `SLACK_BOT_TOKEN_LEADERSHIP`  
- `'payment'` → `SLACK_BOT_TOKEN_PAYMENT`
- `'general'` → `SLACK_BOT_TOKEN_GENERAL`

### **Step 2: Or Use Direct Secret Keys**

```javascript
// BEFORE:
bearerToken: 'xoxb-2602080084-8610961250834-FPVrAJgSXAImytWSf2GKL0Zq'

// AFTER:
bearerToken: getSecret('SLACK_BOT_TOKEN_LEADERSHIP')
```

## 📁 **Files That Need Updates**

### `payment-assistance-tags/sendPaymentPlanRequest.gs`
**Lines 4, 10, 16, 22, 28** - Replace with:
```javascript
bearerToken: getSlackBotToken('leadership')  // Was: FPVrAJgSXAImytWSf2GKL0Zq
bearerToken: getSlackBotToken('payment')     // Was: Z0eD6HhHG68MitN5xsfGstu5  
bearerToken: getSlackBotToken('general')     // Was: K6rtRGsLT6obQfluL1fPpdEs
```

### `process-refunds-exchanges/SlackUtils.gs`
**Lines 15, 21** - Replace with:
```javascript
bearerToken: getSlackBotToken('refunds')     // Was: vR5W3EeryK5T4lNeDHA3lNwh
```

## 🚀 **Implementation Steps**

1. **Run `setupSecrets()`** in each Google Apps Script project
2. **Copy the helper functions** (`getSlackBotToken`, `getSecret`) into each script
3. **Update hardcoded token references** using the table above
4. **Test each script** to ensure tokens work correctly
5. **Delete** the setup file from each project

## ✅ **Benefits of This Cleanup**

- **4 tokens instead of 11** - Much cleaner
- **Purpose-based access** - `getSlackBotToken('refunds')`
- **Environment-aware** - Easy to switch between prod/test
- **Centralized management** - All secrets in PropertiesService
- **No more hardcoded tokens** in source code

## 🧪 **Testing**

After migration, test with:
```javascript
testSecrets(); // Verify all tokens are accessible
console.log(getSlackBotToken('refunds')); // Should show token preview
```

---

⚠️ **Note**: The old duplicate token keys are removed. Use the standardized keys above.
