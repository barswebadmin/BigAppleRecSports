/**
 * Secret Migration Helper for Google Apps Scripts
 *
 * This script helps identify hardcoded secrets and provides code to migrate them
 * to Google Apps Script's PropertiesService.
 *
 * INSTRUCTIONS:
 * 1. Copy this code into the Apps Script editor
 * 2. Run identifySecrets() to find potential hardcoded secrets
 * 3. Run setupSecrets() to set up the secret properties
 * 4. Update your code to use getSecret() instead of hardcoded values
 */

// Common secret patterns to look for
const SECRET_PATTERNS = [
  /token['"]\s*:\s*['"][^'"]+['"]/gi,
  /api[_-]?key['"]\s*:\s*['"][^'"]+['"]/gi,
  /secret['"]\s*:\s*['"][^'"]+['"]/gi,
  /password['"]\s*:\s*['"][^'"]+['"]/gi,
  /bearer['"]\s*:\s*['"][^'"]+['"]/gi,
  /webhook['"]\s*:\s*['"]https?:\/\/[^'"]+['"]/gi,
  /'[a-zA-Z0-9]{32,}'/g,  // Long strings that might be tokens
  /"[a-zA-Z0-9]{32,}"/g   // Long strings that might be tokens
];

/**
 * Scan your code for potential secrets
 * Run this function to identify hardcoded secrets in your scripts
 */
function identifySecrets() {
  console.log("🔍 Scanning for potential hardcoded secrets...");

  // You'll need to manually paste your code here or check each file
  const codeSamples = [
    // Add your code strings here to scan
    // Example: 'const API_TOKEN = "abc123def456";'
  ];

  const findings = [];

  codeSamples.forEach((code, index) => {
    SECRET_PATTERNS.forEach(pattern => {
      const matches = code.match(pattern);
      if (matches) {
        matches.forEach(match => {
          findings.push({
            file: `Code sample ${index + 1}`,
            match: match,
            line: 'Unknown'
          });
        });
      }
    });
  });

  if (findings.length > 0) {
    console.log("⚠️  Potential secrets found:");
    findings.forEach(finding => {
      console.log(`- File: ${finding.file}, Match: ${finding.match}`);
    });
  } else {
    console.log("✅ No obvious secrets found in provided code samples");
  }

  console.log("\n📋 Next steps:");
  console.log("1. Review the findings above");
  console.log("2. Update setupSecrets() with your actual secret values");
  console.log("3. Run setupSecrets() to store them securely");
  console.log("4. Update your code to use getSecret() function");
}

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
