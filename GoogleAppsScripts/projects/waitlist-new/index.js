/**
 * Unified Entry Point for Google Apps Script - Waitlist Management
 * All trigger functions and dependencies imported in dependency order
 */

// Tier 1: Core configuration
import * as config from './src/config.js';

// Tier 2: Integrations
import * as sheetsClient from './src/integrations/SheetsClient.js';
import * as slackNotifications from './src/integrations/slackNotifications.js';
import * as emailUtils from './src/integrations/emailUtils.js';

// Tier 3: Services
import * as calculateWaitlistPositions from './src/services/calculateWaitlistPositions.js';
import * as handleSignups from './src/services/handleSignups.js';
import * as validateInputs from './src/services/validateInputs.js';

// Tier 4: UI
import * as generateStyles from './src/ui/generateStyles.js';
import * as renderPages from './src/ui/renderPages.js';

// Tier 5: Controllers (entry points with trigger functions)
import * as processRequest from './src/controllers/processRequest.js';
import * as handleDoGet from './src/controllers/handleDoGet.js';
import * as handleDoPost from './src/controllers/handleDoPost.js';

// Force esbuild to include all modules by referencing them
// This creates a side effect that prevents tree-shaking
globalThis.__WAITLIST_MODULES__ = {
  config,
  sheetsClient,
  slackNotifications,
  emailUtils,
  calculateWaitlistPositions,
  handleSignups,
  validateInputs,
  generateStyles,
  renderPages,
  processRequest,
  handleDoGet,
  handleDoPost
};

// Note: All trigger functions (doGet, doPost) are declared in their respective files
// and will be available in global scope after esbuild removes the import/export statements

/**
 * Test function to verify Slack configuration
 * Run this function in Google Apps Script to check if script properties are set
 */
function testSlackConfig() {
  console.log('🧪 Testing Slack Configuration...');

  const properties = PropertiesService.getScriptProperties();
  const webhookUrl = properties.getProperty('SLACK_WEBHOOK_URL');

  console.log('Webhook URL exists:', !!webhookUrl);
  console.log('Webhook URL (first 50 chars):', webhookUrl ? `${webhookUrl.substring(0, 50)}...` : 'NOT SET');

  if (!webhookUrl) {
    console.error('❌ Missing SLACK_WEBHOOK_URL script property!');
    console.log('\n📝 To set script property:');
    console.log('1. Go to Project Settings (gear icon)');
    console.log('2. Add Script Property:');
    console.log('   - SLACK_WEBHOOK_URL: [YOUR_SLACK_WEBHOOK_URL]');
    return false;
  }

  // Test sending a message using webhook
  try {
    console.log('🚀 Attempting to send test message via webhook...');

    const payload = {
      text: `🧪 **Slack Webhook Test**\n\nThis is a test message from the waitlist-new Google Apps Script using webhook.\n\n*Timestamp:* ${new Date().toISOString()}`
    };

    const response = UrlFetchApp.fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });

    const responseText = response.getContentText();
    const responseCode = response.getResponseCode();

    console.log('Response code:', responseCode);
    console.log('Response text:', responseText);

    if (responseText === 'ok') {
      console.log('✅ Slack webhook message sent successfully!');
      return true;
    } else {
      console.error('❌ Slack webhook error:', responseText);
      return false;
    }

  } catch (error) {
    console.error('❌ Error sending Slack message:', error);
    return false;
  }
}

/**
 * STEP 1: Run this to trigger OAuth authorization dialog
 * This function is designed to force Google Apps Script to show the authorization prompt
 */
function triggerOAuthDialog() {
  console.log('🔐 Attempting to trigger OAuth authorization dialog...');

  // This should trigger the OAuth dialog automatically
  // The function will fail until you authorize it, which is expected
  UrlFetchApp.fetch('https://httpbin.org/get');

  console.log('✅ If you see this message, authorization was successful!');
}

/**
 * STEP 2: Run this after authorization to set Slack webhook
 */
function setSlackProperties() {
  console.log('⚙️ Setting Slack webhook property...');

  const properties = PropertiesService.getScriptProperties();

  // Set the webhook URL (replace with your actual webhook URL)
  const SLACK_WEBHOOK_URL = 'YOUR_SLACK_WEBHOOK_URL_HERE';

  properties.setProperties({
    'SLACK_WEBHOOK_URL': SLACK_WEBHOOK_URL
  });

  console.log('✅ Slack webhook property set!');
  console.log('Now run testSlackConfig() to verify');
}

/**
 * Force OAuth authorization by making a simple external request
 * This should trigger the authorization dialog
 */
function forceAuthorization() {
  console.log('🔐 Forcing OAuth authorization...');

  try {
    // Make a simple external request to trigger OAuth dialog
    const response = UrlFetchApp.fetch('https://httpbin.org/get', {
      method: 'GET',
      muteHttpExceptions: true
    });

    console.log('✅ Authorization successful! External requests are working.');
    console.log(`Response status: ${response.getResponseCode()}`);

    // Now test Slack webhook
    console.log('🧪 Testing Slack webhook after authorization...');
    return testSlackConfig();

  } catch (error) {
    console.error(`❌ Authorization failed: ${error.message}`);
    return false;
  }
}