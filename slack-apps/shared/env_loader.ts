/**
 * Environment loader that reads .env files directly (like working Node.js approach)
 * Avoids shell environment variable corruption issues
 */

interface EnvVars {
  [key: string]: string;
}

/**
 * Load environment variables directly from .env file
 * Uses the same parsing logic that works in Python and Node.js
 */
export function loadEnvFile(filePath: string = '../.env'): EnvVars {
  try {
    const content = Deno.readTextFileSync(filePath);
    const envVars: EnvVars = {};

    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
        const [key, ...valueParts] = trimmed.split('=');
        let value = valueParts.join('=').trim();

        // Handle both single and double quotes
        if ((value.startsWith('"') && value.endsWith('"')) ||
            (value.startsWith("'") && value.endsWith("'"))) {
          value = value.slice(1, -1);
        }

        envVars[key.trim()] = value;
      }
    }

    return envVars;
  } catch (error) {
    throw new Error(`Failed to load .env file: ${error.message}`);
  }
}

/**
 * Get Google service account credentials using direct file loading
 * Avoids the shell environment corruption issue
 */
export function getGoogleCredentials(): any {
  // Try environment variable first (for production)
  let credsJson = Deno.env.get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS") ||
                  Deno.env.get("GOOGLE__SERVICE_ACCOUNT");

  // If not found, load from .env file directly
  if (!credsJson) {
    const envVars = loadEnvFile();
    credsJson = envVars['GOOGLE__SERVICE_ACCOUNT'] || envVars['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'];
  }

  if (!credsJson) {
    throw new Error("Google service account credentials not found");
  }

  try {
    return JSON.parse(credsJson);
  } catch (error) {
    throw new Error(`Failed to parse Google credentials JSON: ${error.message}`);
  }
}