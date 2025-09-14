/**
 * Custom type definitions for GAS-specific functionality
 * These extend the base @types/google-apps-script definitions
 */

// Backend API Response Types
interface BackendResponse {
  success: boolean;
  message: string;
  display_text: string;
  data?: any;
}

interface LeadershipPayload {
  csv_data: any[][];
  spreadsheet_title: string;
  header_row?: number;
}

interface HealthCheckResponse {
  status: string;
  service: string;
}

// GAS UI Types (for better type safety)
interface UIAlert {
  getSelectedButton(): GoogleAppsScript.Base.Button;
  getResponseText(): string;
}

// Utility function types
type BackendUrlFunction = () => string;

// Note: Global function declarations are handled by GAS runtime
// These functions will be available globally when deployed to GAS
