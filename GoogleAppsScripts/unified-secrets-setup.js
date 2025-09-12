/**
 * UNIFIED SECRETS SETUP FOR ALL BARS GOOGLE APPS SCRIPTS
 * 
 * ⚠️  IMPORTANT SECURITY INSTRUCTIONS:
 * 1. Copy this code into EACH Google Apps Script project
 * 2. Replace all REPLACE_WITH_* values with your actual secrets
 * 3. Run setupSecrets() ONCE in each project
 * 4. DELETE this file from the Google Apps Script project after running
 * 5. Update your code to use getSecret() instead of hardcoded values
 */

/**
 * Set up ALL secrets needed across BARS Google Apps Scripts
 * ⚠️  UPDATE ALL VALUES BELOW BEFORE RUNNING
 */
function setupSecrets() {
  console.log("🔐 Setting up unified secrets for BARS...");
  
  const secrets = {
    // === SHOPIFY CONFIGURATION ===
    'SHOPIFY_ACCESS_TOKEN': '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',  // Currently: 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
    'SHOPIFY_STORE': '09fe59-3.myshopify.com',
    'SHOPIFY_GRAPHQL_URL': 'https://09fe59-3.myshopify.com/admin/api/2025-01/graphql.json',
    'SHOPIFY_REST_URL': 'https://09fe59-3.myshopify.com/admin/api/2024-04',
    'SHOPIFY_LOCATION_GID': 'gid://shopify/Location/61802217566',
    'SHOPIFY_PUBLICATION_GID': 'gid://shopify/Publication/79253667934',
    'SHOPIFY_LOGIN_URL': 'https://shopify.com/55475535966/account',
    
    // === SLACK CONFIGURATION ===
    // Slack Bot Tokens (cleaned up - 4 unique tokens)
    // MAPPING: Use getSlackBotToken('purpose') in your code
    'SLACK_BOT_TOKEN_REFUNDS': 'xoxb-2602080084-8649458379120-vR5W3EeryK5T4lNeDHA3lNwh',          // For refunds bot
    'SLACK_BOT_TOKEN_LEADERSHIP': 'xoxb-2602080084-8610961250834-FPVrAJgSXAImytWSf2GKL0Zq',        // For leadership/joe_test
    'SLACK_BOT_TOKEN_PAYMENT': 'xoxb-2602080084-8601708038470-Z0eD6HhHG68MitN5xsfGstu5',           // For payment/exec_leadership  
    'SLACK_BOT_TOKEN_GENERAL': 'xoxb-2602080084-8610974674770-K6rtRGsLT6obQfluL1fPpdEs',           // For general/web purposes
    'SLACK_BOT_TOKEN_WAITLIST': 'xoxb-2602080084-8610974674770-K6rtRGsLT6obQfluL1fPpdEs',          // For waitlist validation alerts
    
    // Slack Channel IDs
    'SLACK_CHANNEL_REFUNDS_PROD': 'C08J1EN7SFR',      // #refunds (production)
    'SLACK_CHANNEL_JOE_TEST': 'C092RU7R6PL',      // #joe-test
    'SLACK_CHANNEL_PAYMENT_LEADERSHIP': 'C08J219EXN0', // Payment/Leadership notifications  
    'SLACK_CHANNEL_PAYMENT_GENERAL': 'C086GG1H9BK',   // General payment notifications
    'SLACK_CHANNEL_LEADERSHIP': 'C02KAENF6',          // Leadership channel
    
    // === BACKEND API CONFIGURATION ===
    'BACKEND_API_URL_PROD': 'https://bars-backend.onrender.com',
    'BACKEND_API_URL_LOCAL': 'http://127.0.0.1:8000',
    
    // === AWS LAMBDA ENDPOINTS ===
    'LAMBDA_SCHEDULE_CHANGES': 'https://6ltvg34u77der4ywcfk3zwr4fq0tcvvj.lambda-url.us-east-1.on.aws/',
    'LAMBDA_PAYMENT_ASSISTANCE': 'https://xdakvg6v3jf5su2ioquv3izt2u0jcupn.lambda-url.us-east-1.on.aws/',
    
    // === GOOGLE SHEETS CONFIGURATION ===
    'SHEET_ID_REFUNDS': '11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw',
    'SHEET_ID_PRODUCT_CREATION': '1w9Hj4JMmjTIQM5c8FbXuKnTMjVOLipgXaC6WqeSV_vc',
    'SHEET_ID_WAITLIST_RESPONSES': '1wFoayUoIx1PPOO0TtuS0Jnwb5hoIbgCd_kebMeYNzGQ',
    'WAITLIST_RESPONSES_URL': 'https://docs.google.com/spreadsheets/d/1wFoayUoIx1PPOO0TtuS0Jnwb5hoIbgCd_kebMeYNzGQ/edit?resourcekey=&gid=744639660#gid=744639660',
    
    // === GOOGLE APPS SCRIPT ENDPOINTS ===
    'GAS_WAITLIST_FORM_WEB_APP_URL': 'https://script.google.com/macros/s/AKfycby2GMTxZkXKg19k-su5Mp9hN0smyzdKRXfoXOOOVZ0MCoPFox8oIeEukxpWriPBF7nz/exec',
    'GAS_PAYMENT_APPROVAL_URL': 'https://script.google.com/a/macros/bigapplerecsports.com/s/AKfycbywEaTZ5tj5d-rfhalRysMGcon6Dv_blhqk2Dq8EKnf0lCIPy20e3oUFuSD7hK8Vuj64A/exec',
    'GAS_REFUNDS_WEBHOOK_URL': 'https://script.google.com/macros/s/AKfycbxuqCjZXZ5cxiqZBukccOpKW4FznLaHHU6VLjkl8lymd-bbItJHrxYiT5TuLXPN7GiA/exec',
    
    // === BRANDING ASSETS ===
    'BARS_LOGO_URL': 'https://cdn.shopify.com/s/files/1/0554/7553/5966/files/122824_BARS_Logo_Full-Black.png?v=1741951481',
    
    // === DEVELOPMENT/TESTING CONFIGURATION ===
    'API_DESTINATION': 'AWS',  // 'AWS' or 'LOCAL' for switching between environments
    'LOCAL_TUNNEL_URL': 'https://334e55c8b409.ngrok-free.app',  // Current ngrok URL from Utils.gs
    'LOCAL_LOCA_LT_URL': 'https://chubby-grapes-trade.loca.lt',
    'LOCAL_NGROK_ALT': 'https://0d06-70-187-151-213.ngrok-free.app',  // Alternative ngrok URL
    
    // === TAXONOMY/CATEGORIZATION ===
    'SHOPIFY_TAXONOMY_CATEGORY': 'gid://shopify/TaxonomyCategory/sg-4',
  };
  
  // Validate that critical secrets are present
  const criticalSecrets = [
    'SHOPIFY_ACCESS_TOKEN',
    'SLACK_BOT_TOKEN_REFUNDS',
    'SLACK_BOT_TOKEN_LEADERSHIP',
    'SLACK_BOT_TOKEN_PAYMENT',
    'SLACK_BOT_TOKEN_GENERAL'
  ];
  
  const missingSecrets = criticalSecrets.filter(key => !secrets[key]);
  
  if (missingSecrets.length > 0) {
    console.error("❌ CRITICAL: Missing required secrets:", missingSecrets);
    return;
  }
  
  console.log("✅ All critical secrets are present and ready to be stored");
  
  try {
    PropertiesService.getScriptProperties().setProperties(secrets);
    console.log("✅ All secrets successfully stored in PropertiesService");
    console.log(`📊 Stored ${Object.keys(secrets).length} secrets total`);
    
    // Show categories of secrets stored (but not values for security)
    console.log("\n📋 Secret categories stored:");
    console.log("   🛒 Shopify: API tokens, store config, URLs");  
    console.log("   💬 Slack: Bot tokens, channel IDs");
    console.log("   🌐 Backend: API endpoints, Lambda URLs");
    console.log("   📊 Google Sheets: Sheet IDs, URLs");
    console.log("   🎨 Assets: Logo URLs, branding");
    console.log("   🔧 Development: Testing endpoints, tunnel URLs");
    
    console.log("\n🎉 Setup complete! You can now:");
    console.log("   1. Delete this file from Google Apps Script");
    console.log("   2. Update your code to use getSecret('SECRET_NAME')");
    console.log("   3. Test with testSecrets() function below");
    
  } catch (error) {
    console.error("❌ Error storing secrets:", error);
  }
}

/**
 * Retrieve a secret from PropertiesService
 * Copy this function into your Google Apps Scripts
 */
function getSecret(key) {
  const value = PropertiesService.getScriptProperties().getProperty(key);
  if (!value) {
    throw new Error(`Secret '${key}' not found. Make sure setupSecrets() was run in this project.`);
  }
  return value;
}

/**
 * Get environment-aware backend URL
 * Copy this helper into your scripts that need backend connectivity
 */
function getBackendUrl() {
  const apiDestination = getSecret('API_DESTINATION');
  return apiDestination === 'LOCAL' ? getSecret('BACKEND_API_URL_LOCAL') : getSecret('BACKEND_API_URL_PROD');
}

/**
 * Get environment-aware Slack channel
 * Copy this helper into your scripts that need Slack connectivity
 */
function getSlackChannel(isProduction = true) {
  return isProduction ? getSecret('SLACK_CHANNEL_REFUNDS_PROD') : getSecret('SLACK_CHANNEL_REFUNDS_TEST');
}

/**
 * Get appropriate Slack bot token based on purpose
 * Copy this helper into your scripts that need Slack bot tokens
 */
function getSlackBotToken(purpose = 'general') {
  const tokenMap = {
    'refunds': 'SLACK_BOT_TOKEN_REFUNDS',
    'leadership': 'SLACK_BOT_TOKEN_LEADERSHIP', 
    'payment': 'SLACK_BOT_TOKEN_PAYMENT',
    'general': 'SLACK_BOT_TOKEN_GENERAL',
    // Legacy mappings for compatibility
    'joe_test': 'SLACK_BOT_TOKEN_LEADERSHIP',
    'exec_leadership': 'SLACK_BOT_TOKEN_PAYMENT',
    'web': 'SLACK_BOT_TOKEN_GENERAL'
  };
  
  const secretKey = tokenMap[purpose] || 'SLACK_BOT_TOKEN_GENERAL';
  return getSecret(secretKey);
}

/**
 * Test that secrets are properly configured
 */
function testSecrets() {
  console.log("🧪 Testing secret retrieval...");
  
  const testKeys = [
    'SHOPIFY_ACCESS_TOKEN',
    'SHOPIFY_STORE', 
    'SLACK_BOT_TOKEN_REFUNDS',
    'BACKEND_API_URL_PROD',
    'BARS_LOGO_URL'
  ];
  
  testKeys.forEach(key => {
    try {
      const value = getSecret(key);
      const preview = value.length > 20 ? value.substring(0, 20) + '...' : value;
      console.log(`✅ ${key}: ${preview} (${value.length} chars)`);
    } catch (error) {
      console.log(`❌ ${key}: ${error.message}`);
    }
  });
}

/**
 * List all stored secrets (keys only, not values)
 */
function listSecretKeys() {
  console.log("🔑 All stored secret keys:");
  const properties = PropertiesService.getScriptProperties().getProperties();
  const keys = Object.keys(properties).sort();
  
  if (keys.length === 0) {
    console.log("❌ No secrets found. Run setupSecrets() first.");
  } else {
    keys.forEach(key => console.log(`   • ${key}`));
    console.log(`\n📊 Total: ${keys.length} secrets stored`);
  }
}

/**
 * Clean up old/deprecated secret keys
 * Run this if you need to remove outdated secrets
 */
function cleanupOldSecrets() {
  const deprecatedKeys = [
    // Add any old secret keys here that should be removed
    'OLD_SHOPIFY_TOKEN',
    'DEPRECATED_SLACK_TOKEN'
  ];
  
  const properties = PropertiesService.getScriptProperties();
  let removedCount = 0;
  
  deprecatedKeys.forEach(key => {
    if (properties.getProperty(key)) {
      properties.deleteProperty(key);
      removedCount++;
      console.log(`🗑️  Removed deprecated secret: ${key}`);
    }
  });
  
  console.log(`✅ Cleanup complete. Removed ${removedCount} deprecated secrets.`);
}

// === EXAMPLE CODE MIGRATIONS ===

/**
 * BEFORE (hardcoded):
 * const SHOPIFY_ACCESS_TOKEN = "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";
 * 
 * AFTER (using secrets):
 * const SHOPIFY_ACCESS_TOKEN = getSecret('SHOPIFY_ACCESS_TOKEN');
 */

/**
 * BEFORE (hardcoded):
 * const slackChannel = 'C08J1EN7SFR';
 * const bearerToken = 'xoxb-2602080084-8649458379120-vR5W3EeryK5T4lNeDHA3lNwh';
 * 
 * AFTER (environment-aware):
 * const slackChannel = getSlackChannel(true); // true for production
 * const bearerToken = getSlackBotToken('refunds'); // purpose-based token
 */

/**
 * BEFORE (hardcoded):
 * const backendUrl = 'https://bars-backend.onrender.com';
 * 
 * AFTER (environment-aware):
 * const backendUrl = getBackendUrl();
 */
