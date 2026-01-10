/**
 * ========================================================================
 * GOOGLE SHEETS MENU SYSTEM
 * ========================================================================
 *
 * Creates custom menu items for manual operations and testing
 * This function runs automatically when the spreadsheet is opened
 */

/**
 * Create custom menu in Google Sheets for manual operations
 * This function runs when the spreadsheet is opened
 */

// biome-ignore lint/correctness/noUnusedVariables: <it's triggered when the GS is opened>
function  onOpen() {
  const ui = SpreadsheetApp.getUi();

  ui.createMenu('💰 BARS Refunds & Exchanges')
    .addItem('🧪 Test Backend Connection', 'testBackendConnection')
    .addSeparator()
    .addItem('📖 View API Documentation', 'showAPIDocumentation')
    .addToUi();
}

/**
 * Get order details from the backend API (for testing only)
 * @param {string} orderNumber - The order number to look up
 * @param {string} email - Optional email for fallback lookup
 * @returns {Object} Order details or error
 */
function getOrderDetails(orderNumber, email = null) {
  try {
    let url = `${getApiUrl()}/orders/${encodeURIComponent(orderNumber)}`;
    if (email) {
      url += `?email=${encodeURIComponent(email)}`;
    }

    const response = UrlFetchApp.fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    const responseData = JSON.parse(response.getContentText());

    if (response.getResponseCode() === 200 && responseData.success) {
      return {
        success: true,
        data: responseData.data
      };
    } else {
      return {
        success: false,
        message: responseData.detail || 'Failed to fetch order details'
      };
    }

  } catch (error) {
    Logger.log(`Error fetching order details: ${error.toString()}`);
    return {
      success: false,
      message: `Error fetching order details: ${error.toString()}`
    };
  }
}

/**
 * Test function to verify the backend API connection
 * Called from the Google Sheets menu: BARS Refunds > Test Backend Connection
 */

// biome-ignore lint/correctness/noUnusedVariables: <it's called in a menu item>
function  testBackendConnection() {
  try {
    // Test with a sample order number
    const testOrderNumber = '#1001'; // Replace with a real order number for testing
    const result = getOrderDetails(testOrderNumber);

    Logger.log(`Backend connection test result: ${JSON.stringify(result, null, 2)}`);

    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: 'BARS Backend API Connection Test',
      htmlBody: `
        <h3>Backend API Connection Test</h3>
        <p><strong>API URL:</strong> ${getApiUrl()}</p>
        <p><strong>Test Order:</strong> ${testOrderNumber}</p>
        <p><strong>Result:</strong> ${result.success ? 'SUCCESS' : 'FAILED'}</p>
        <p><strong>Details:</strong> <pre>${JSON.stringify(result, null, 2)}</pre></p>
      `
    });

    return result;

  } catch (error) {
    const errorMessage = `Backend connection test failed: ${error.toString()}`;
    Logger.log(errorMessage);

    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: '❌ BARS Backend API Connection Test Failed',
      htmlBody: `
        <h3>Backend API Connection Test Failed</h3>
        <p><strong>API URL:</strong> ${getApiUrl()}</p>
        <p><strong>Error:</strong> ${errorMessage}</p>
        <p><strong>Stack:</strong> <pre>${error.stack || 'No stack trace available'}</pre></p>
      `
    });

    return { success: false, message: errorMessage };
  }
}

/**
 * Show API documentation in a dialog
 */

// biome-ignore lint/correctness/noUnusedVariables: <it's called in a menu item>
function  showAPIDocumentation() {
  const html = `
    <div style="font-family: Arial, sans-serif; padding: 20px;">
      <h2>🎯 BARS Refunds System Architecture</h2>

      <h3>🔄 High-Level Flow</h3>
      <ol>
        <li><strong>Form Submission:</strong> Customer fills out refund form</li>
        <li><strong>GAS Processing:</strong> This script processes form data and calls backend API</li>
        <li><strong>Backend Validation:</strong> Backend validates order/email and calculates refund amount</li>
        <li><strong>Slack Notification:</strong> Backend sends rich message to #registration-refunds channel with action buttons</li>
        <li><strong>User Interaction:</strong> Staff clicks Slack buttons to approve/deny/modify refund</li>
        <li><strong>Shopify Integration:</strong> Backend handles order cancellation, refund processing, and inventory restocking via Shopify API</li>
        <li><strong>Email Callbacks:</strong> Backend calls back to this GAS script to send denial emails when appropriate (until Mailchimp integration)</li>
      </ol>

      <h3>🏗️ System Components</h3>
      <ul>
        <li><strong>Google Apps Script:</strong> Form processing, email sending (current role)</li>
        <li><strong>Backend API:</strong> Business logic, Slack integration, Shopify operations</li>
        <li><strong>Slack:</strong> User interface for staff to process refunds</li>
        <li><strong>Shopify:</strong> Order management, refund processing, inventory updates</li>
        <li><strong>Future: Mailchimp:</strong> Will replace GAS for email sending</li>
      </ul>

      <h3>📊 Refund Tiers</h3>
      <p><strong>Refunds:</strong> 95%, 90%, 80%, 70%, 60%, 50% (based on timing)</p>
      <p><strong>Credits:</strong> 100%, 95%, 85%, 75%, 65%, 55% (higher amounts)</p>

      <h3>🔧 Current Configuration</h3>
      <p><strong>Backend URL:</strong> ${getApiUrl()}</p>
      <p><strong>Debug Email:</strong> ${DEBUG_EMAIL}</p>
      <p><strong>Mode:</strong> ${MODE}</p>
      <p><strong>Slack Channel:</strong> #registration-refunds</p>

      <h3>🆘 Troubleshooting</h3>
      <p>If refunds are not processing:</p>
      <ol>
        <li>Test backend connection using the menu above</li>
        <li>Check that backend server is running (${getApiUrl()}/health)</li>
        <li>Verify API URL is correct in core/Utils.gs</li>
        <li>Check email notifications for error details</li>
        <li>Ensure Slack app webhook points to backend /slack/interactions</li>
      </ol>
    </div>
  `;

  const htmlOutput = HtmlService.createHtmlOutput(html)
    .setWidth(700)
    .setHeight(650);

  SpreadsheetApp.getUi().showModalDialog(htmlOutput, 'BARS Refunds System Architecture');
}
