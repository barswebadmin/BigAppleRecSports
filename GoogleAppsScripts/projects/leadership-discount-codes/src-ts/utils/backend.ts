/**
 * Backend URL utility functions
 * This file provides the getBackendUrl function that's used throughout the application
 */

/**
 * Get the backend URL from PropertiesService
 * This function should be implemented to match your existing shared utilities
 * @returns The backend API URL
 */
function getBackendUrl(): string {
  // This is a placeholder - in the real implementation, this would come from
  // your shared utilities (secretsUtils.gs) or PropertiesService
  // For now, we'll provide a type-safe stub

  try {
    // Try to get from PropertiesService (typical GAS pattern)
    const properties = PropertiesService.getScriptProperties();
    const backendUrl = properties.getProperty('BACKEND_URL');

    if (backendUrl) {
      return backendUrl;
    }

    // Fallback to a default development URL
    Logger.log("⚠️ BACKEND_URL not found in PropertiesService, using default");
    return "http://localhost:8000"; // Default development URL

  } catch (error) {
    Logger.log("❌ Error getting backend URL:", error);
    throw new Error("Backend URL not configured. Please set BACKEND_URL in PropertiesService.");
  }
}
