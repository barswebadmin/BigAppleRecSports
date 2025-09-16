function setupSecrets() {
  console.log("🔐 Setting up secrets in PropertiesService...");

  const secrets = {
    // Update these with your actual values
    'SHOPIFY_TOKEN': 'REPLACE_WITH_YOUR_SHOPIFY_TOKEN',
    'SHOPIFY_STORE': 'REPLACE_WITH_YOUR_STORE_NAME',
    'SLACK_WEBHOOK_URL': 'REPLACE_WITH_YOUR_SLACK_WEBHOOK',
    'SLACK_BOT_TOKEN': 'REPLACE_WITH_YOUR_SLACK_BOT_TOKEN',
    'API_ENDPOINT': 'REPLACE_WITH_YOUR_API_ENDPOINT',
    'BACKEND_API_URL': 'REPLACE_WITH_YOUR_BACKEND_URL',

    // Add more secrets as needed
    // 'OTHER_SECRET': 'REPLACE_WITH_VALUE',
  };

  // Validate that secrets have been updated
  const hasPlaceholders = Object.values(secrets).some(value =>
    value.startsWith('REPLACE_WITH_')
  );

  if (hasPlaceholders) {
    console.error("❌ Please update the secrets object with your actual values before running this function!");
    console.log("Update the values in the setupSecrets() function, then run it again.");
    return;
  }

  try {
    PropertiesService.getScriptProperties().setProperties(secrets);
    console.log("✅ Secrets successfully stored in PropertiesService");
    console.log(`📊 Stored ${Object.keys(secrets).length} secrets`);

    // Don't log the actual values for security
    console.log("🔑 Secret keys stored:", Object.keys(secrets));

  } catch (error) {
    console.error("❌ Error storing secrets:", error);
  }
}

/**
 * Retrieve a secret from PropertiesService
 * Use this function in your code instead of hardcoded values
 *
 * @param {string} key - The secret key
 * @returns {string} The secret value
 */
function getSecret(key) {
  const value = PropertiesService.getScriptProperties().getProperty(key);
  if (!value) {
    throw new Error(`Secret '${key}' not found. Make sure it's set up in PropertiesService.`);
  }
  return value;
}

/**
 * List all stored secrets (keys only, not values)
 * Useful for debugging
 */
function listSecretKeys() {
  console.log("🔑 Currently stored secret keys:");
  const properties = PropertiesService.getScriptProperties().getProperties();
  const keys = Object.keys(properties);

  if (keys.length === 0) {
    console.log("No secrets found. Run setupSecrets() first.");
  } else {
    keys.forEach(key => console.log(`- ${key}`));
  }
}

/**
 * Example of how to update your code to use secrets
 */
function exampleUsage() {
  // OLD WAY (hardcoded):
  // const SHOPIFY_TOKEN = "shpat_abc123def456";

  // NEW WAY (using PropertiesService):
  const SHOPIFY_TOKEN = getSecret('SHOPIFY_TOKEN');

  // Use the token as normal
  console.log("Token length:", SHOPIFY_TOKEN.length);
}

/**
 * Development helper - quickly test if secrets are working
 */
function testSecrets() {
  console.log("🧪 Testing secret retrieval...");

  try {
    const testKeys = ['SHOPIFY_TOKEN', 'SLACK_WEBHOOK_URL', 'API_ENDPOINT'];

    testKeys.forEach(key => {
      try {
        const value = getSecret(key);
        console.log(`✅ ${key}: ${value.substring(0, 10)}... (${value.length} chars)`);
      } catch (error) {
        console.log(`❌ ${key}: ${error.message}`);
      }
    });

  } catch (error) {
    console.error("Error testing secrets:", error);
  }
}
