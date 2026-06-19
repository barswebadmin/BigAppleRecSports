import { googleAuth } from "./auth/google_auth.ts";

/**
 * Google API client for all Google services (Sheets, Gmail, Drive, Calendar)
 * Import this when you need any Google API functionality
 */
export class GoogleClient {
  private googleAuth = googleAuth;

  /**
   * Get authenticated Google Sheets API client
   */
  async sheets(userEmail?: string) {
    return await this.googleAuth.getSheetsClient(userEmail);
  }

  /**
   * Get authenticated Gmail API client
   */
  async gmail(userEmail: string) {
    return await this.googleAuth.getGmailClient(userEmail);
  }

  /**
   * Get authenticated Drive API client
   */
  async drive(userEmail?: string) {
    return await this.googleAuth.getDriveClient(userEmail);
  }

  /**
   * Get authenticated Calendar API client
   */
  async calendar(userEmail?: string) {
    return await this.googleAuth.getCalendarClient(userEmail);
  }
}

// Singleton instance
export const googleClient = new GoogleClient();