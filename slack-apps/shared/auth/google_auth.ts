import { JWT } from "google-auth-library";
import { google } from "googleapis";

interface ServiceAccountCredentials {
  type: string;
  project_id: string;
  private_key_id: string;
  private_key: string;
  client_email: string;
  client_id: string;
  auth_uri: string;
  token_uri: string;
  auth_provider_x509_cert_url: string;
  client_x509_cert_url: string;
}

/**
 * Shared Google API authentication with domain-wide delegation
 * Used by all BARS Slack bots (registrations, marketing, etc.)
 */
export class GoogleAuth {
  private credentials: ServiceAccountCredentials;
  private scopes: string[];

  constructor() {
    // Get credentials from environment variable
    const credsJson = Deno.env.get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS");
    if (!credsJson) {
      throw new Error("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS environment variable not set");
    }

    this.credentials = JSON.parse(credsJson);

    // Default scopes for domain-wide delegation
    this.scopes = [
      'https://www.googleapis.com/auth/spreadsheets',
      'https://www.googleapis.com/auth/drive',
      'https://www.googleapis.com/auth/admin.directory.user',
      'https://www.googleapis.com/auth/gmail.send',
      'https://www.googleapis.com/auth/calendar'
    ];
  }

  /**
   * Create JWT client for domain-wide delegation
   * @param userEmail Email of user to impersonate (optional)
   * @returns Authenticated JWT client
   */
  createJWTClient(userEmail?: string): JWT {
    const jwtClient = new JWT({
      email: this.credentials.client_email,
      key: this.credentials.private_key,
      scopes: this.scopes,
      subject: userEmail, // User to impersonate for domain-wide delegation
    });

    return jwtClient;
  }

  /**
   * Get authenticated Google API client
   * @param userEmail Email of user to impersonate
   * @returns Google API client instance
   */
  async getGoogleClient(userEmail?: string) {
    const auth = this.createJWTClient(userEmail);
    await auth.authorize();

    return google.auth.fromJSON({
      ...this.credentials,
      scopes: this.scopes,
      subject: userEmail
    });
  }

  /**
   * Get authenticated Sheets API client
   * @param userEmail Email of user to impersonate
   */
  async getSheetsClient(userEmail?: string) {
    const auth = this.createJWTClient(userEmail);
    await auth.authorize();

    return google.sheets({
      version: 'v4',
      auth
    });
  }

  /**
   * Get authenticated Drive API client
   * @param userEmail Email of user to impersonate
   */
  async getDriveClient(userEmail?: string) {
    const auth = this.createJWTClient(userEmail);
    await auth.authorize();

    return google.drive({
      version: 'v3',
      auth
    });
  }

  /**
   * Get authenticated Gmail API client
   * @param userEmail Email of user to impersonate (required for Gmail)
   */
  async getGmailClient(userEmail: string) {
    if (!userEmail) {
      throw new Error("User email required for Gmail API access");
    }

    const auth = this.createJWTClient(userEmail);
    await auth.authorize();

    return google.gmail({
      version: 'v1',
      auth
    });
  }

  /**
   * Get authenticated Calendar API client
   * @param userEmail Email of user to impersonate
   */
  async getCalendarClient(userEmail?: string) {
    const auth = this.createJWTClient(userEmail);
    await auth.authorize();

    return google.calendar({
      version: 'v3',
      auth
    });
  }
}

// Singleton instance
export const googleAuth = new GoogleAuth();