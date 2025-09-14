"use strict";
function getBackendUrl() {
    try {
        var properties = PropertiesService.getScriptProperties();
        var backendUrl = properties.getProperty('BACKEND_URL');
        if (backendUrl) {
            return backendUrl;
        }
        Logger.log("⚠️ BACKEND_URL not found in PropertiesService, using default");
        return "http://localhost:8000";
    }
    catch (error) {
        Logger.log("❌ Error getting backend URL:", error);
        throw new Error("Backend URL not configured. Please set BACKEND_URL in PropertiesService.");
    }
}
