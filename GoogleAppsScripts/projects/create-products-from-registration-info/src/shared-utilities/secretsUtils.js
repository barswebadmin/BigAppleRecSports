/**
 * Secrets utility for this GAS project
 * Provides getSecret() backed by PropertiesService Script Properties
 */

/**
 * Retrieve a secret by key from PropertiesService Script Properties
 * @param {string} key
 * @returns {string}
 */
function getSecret(key) {
  const value = PropertiesService.getScriptProperties().getProperty(key);
  if (!value) {
    throw new Error(`Secret '${key}' not found. Ensure it's set in Script Properties.`);
  }
  return value;
}


