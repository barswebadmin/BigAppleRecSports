/**
 * Shared environment configuration and validation for all BARS Slack bots
 */

interface EnvironmentConfig {
  // Google/Firebase Service Account
  serviceAccountCredentials: string;

  // Slack Configuration
  slackBotToken?: string;
  slackSigningSecret?: string;

  // BigApple Domain Configuration
  defaultUserDomain: string;
  adminUserEmail: string;

  // Google Workspace Configuration
  masterSpreadsheetId?: string;

  // Development/Production Mode
  isDevelopment: boolean;
}

/**
 * Load and validate environment configuration
 */
export function loadEnvironment(): EnvironmentConfig {
  const serviceAccountCredentials =
    Deno.env.get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS") ||
    Deno.env.get("FIREBASE_SERVICE_ACCOUNT_CREDENTIALS");

  if (!serviceAccountCredentials) {
    throw new Error(
      "Required environment variable missing: GOOGLE_SERVICE_ACCOUNT_CREDENTIALS or FIREBASE_SERVICE_ACCOUNT_CREDENTIALS"
    );
  }

  // Validate JSON format
  try {
    JSON.parse(serviceAccountCredentials);
  } catch (error) {
    throw new Error("Service account credentials must be valid JSON");
  }

  const defaultUserDomain = Deno.env.get("DEFAULT_USER_DOMAIN") || "bigapplerecsports.com";
  const adminUserEmail = Deno.env.get("ADMIN_USER_EMAIL");

  if (!adminUserEmail) {
    throw new Error("ADMIN_USER_EMAIL environment variable required for domain-wide delegation");
  }

  return {
    serviceAccountCredentials,
    slackBotToken: Deno.env.get("SLACK_BOT_TOKEN"),
    slackSigningSecret: Deno.env.get("SLACK_SIGNING_SECRET"),
    defaultUserDomain,
    adminUserEmail,
    masterSpreadsheetId: Deno.env.get("MASTER_SPREADSHEET_ID"),
    isDevelopment: Deno.env.get("DENO_ENV") !== "production",
  };
}

/**
 * Get admin user email for service operations
 */
export function getAdminUserEmail(): string {
  const config = loadEnvironment();
  return config.adminUserEmail;
}

/**
 * Get default domain for user email construction
 */
export function getDefaultDomain(): string {
  const config = loadEnvironment();
  return config.defaultUserDomain;
}

/**
 * Construct user email from username
 */
export function constructUserEmail(username: string, domain?: string): string {
  const userDomain = domain || getDefaultDomain();

  // If already contains @, assume it's a full email
  if (username.includes("@")) {
    return username;
  }

  return `${username}@${userDomain}`;
}

/**
 * Environment validation on module load
 */
export const environment = loadEnvironment();