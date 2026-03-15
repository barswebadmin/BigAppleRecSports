/**
 * Main request processor for waitlist management
 * Thin wrappers that defer to separate handlers
 */

import { CONFIG } from '../config.js';
import { SheetsClient } from '../integrations/SheetsClient.js';
import { sendToSlack } from '../integrations/slackNotifications.js';
import { handleDoGet } from './handleDoGet.js';
import { handleDoPost } from './handleDoPost.js';

// Global SheetsClient instance (initialized once per execution)
let sheetsClient = null;

/**
 * Get or create the SheetsClient instance
 * @returns {SheetsClient} Configured SheetsClient instance
 */
export function getSheetsClient() {
  if (!sheetsClient) {
    sheetsClient = new SheetsClient(
      CONFIG.SPREADSHEET_ID,
      CONFIG.COLUMNS,
      CONFIG.HEADER_ROW
    );
  }
  return sheetsClient;
}

/**
 * Process GET request (view waitlist positions)
 * @param {Object} e - Google Apps Script event object
 * @returns {GoogleAppsScript.HTML.HtmlOutput} HTML response
 */
export function doGet(e) {
  sendToSlack(`🚀 **DoGet Request Started**\nParameters: ${JSON.stringify(e?.parameter || {})}\nTimestamp: ${new Date().toISOString()}`);

  try {
    const params = e.parameter || {};
    const {
      action,
      productId,
      email,
      customerId,
      source,
      league
    } = params;

    sendToSlack(`📊 **DoGet Parameters**\nAction: ${action || 'None'}\nProduct ID: ${productId}\nEmail: ${email ? '[REDACTED]' : 'None'}\nCustomer ID: ${customerId || 'None'}\nSource: ${source || 'None'}\nLeague: ${league || 'None'}`);

    const sheets = getSheetsClient();

    sendToSlack(`✅ **SheetsClient Initialized**\nSpreadsheet ID: ${sheets.spreadsheetId}`);

    // Pass action as the source parameter to handleDoGet for API routing
    const result = handleDoGet(sheets, productId, email, customerId, action || source, league);

    sendToSlack(`✅ **DoGet Request Completed Successfully**\nAction: ${action || 'normal'}\nProduct ID: ${productId}\nSource: ${source}\nResult Generated: ${!!result}`);

    return result;

  } catch (error) {
    sendToSlack(`❌ **DoGet Request Failed**\nError: ${error.message}\nParameters: ${JSON.stringify(e?.parameter || {})}`);

    // Return basic error page if imports fail
    const errorHtml = `
      <html>
        <body>
          <h2>System Error</h2>
          <p>Unable to process your request. Please try again later.</p>
          <p>Error: ${error.message}</p>
        </body>
      </html>
    `;

    return HtmlService
      .createHtml(errorHtml)
      .setTitle('Waitlist Error');
  }
}

/**
 * Process POST request (waitlist signup)
 * @param {Object} e - Google Apps Script event object
 * @returns {GoogleAppsScript.HTML.HtmlOutput} HTML response
 */
export function doPost(e) {
  sendToSlack(`🚀 **DoPost Request Started (Signup)**\nParameters: ${JSON.stringify(e?.parameter || {})}\nTimestamp: ${new Date().toISOString()}`);

  try {
    const params = e?.parameter || {};
    const {
      firstName,
      lastName,
      email,
      phone,
      customerId,
      productId,
      league,
      source
    } = params;

    sendToSlack(`📊 **Signup Parameters**\nName: ${firstName} ${lastName}\nEmail: ${email ? '[REDACTED]' : 'None'}\nPhone: ${phone ? '[REDACTED]' : 'None'}\nProduct ID: ${productId}\nLeague: ${league}\nSource: ${source}`);

    const sheets = getSheetsClient();

    sendToSlack(`✅ **SheetsClient Initialized for Signup**\nSpreadsheet ID: ${sheets.spreadsheetId}`);

    const result = handleDoPost(sheets, firstName, lastName, email, phone, customerId, productId, league, source);

    sendToSlack(`✅ **Signup Request Completed Successfully**\nName: ${firstName} ${lastName}\nProduct ID: ${productId}\nLeague: ${league}\nResult Generated: ${!!result}`);

    return result;

  } catch (error) {
    sendToSlack(`❌ **Signup Request Failed**\nError: ${error.message}\nParameters: ${JSON.stringify(e?.parameter || {})}`);

    // Return basic error page if imports fail
    const errorHtml = `
      <html>
        <body>
          <h2>Signup Error</h2>
          <p>Unable to process your signup. Please try again later.</p>
          <p>Error: ${error.message}</p>
        </body>
      </html>
    `;

    return HtmlService
      .createHtml(errorHtml)
      .setTitle('Signup Error');
  }
}