/**
 * Secrets Management Utilities
 * Wrapper around PropertiesService for consistent secret access
 */

function getSecret(key) {
  try {
    const value = PropertiesService.getScriptProperties().getProperty(key);
    if (!value) {
      Logger.log(`⚠️ Secret '${key}' not found in PropertiesService`);
      return null;
    }
    return value;
  } catch (error) {
    Logger.log(`💥 Error getting secret '${key}': ${error.message}`);
    return null;
  }
}

function setSecret(key, value) {
  try {
    PropertiesService.getScriptProperties().setProperty(key, value);
    Logger.log(`✅ Secret '${key}' set successfully`);
    return true;
  } catch (error) {
    Logger.log(`💥 Error setting secret '${key}': ${error.message}`);
    return false;
  }
}

function deleteSecret(key) {
  try {
    PropertiesService.getScriptProperties().deleteProperty(key);
    Logger.log(`✅ Secret '${key}' deleted successfully`);
    return true;
  } catch (error) {
    Logger.log(`💥 Error deleting secret '${key}': ${error.message}`);
    return false;
  }
}

function listSecrets() {
  try {
    const properties = PropertiesService.getScriptProperties().getProperties();
    const keys = Object.keys(properties);
    Logger.log(`📋 Found ${keys.length} secrets: ${keys.join(', ')}`);
    return keys;
  } catch (error) {
    Logger.log(`💥 Error listing secrets: ${error.message}`);
    return [];
  }
}

