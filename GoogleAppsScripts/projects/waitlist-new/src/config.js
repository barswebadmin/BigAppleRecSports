/**
 * Centralized configuration for waitlist management
 * Pre-defined column indexes for maximum performance
 */

export const CONFIG = {
  // Main waitlist spreadsheet ID
  SPREADSHEET_ID: '1EatkTwZHJ28dPUH2YrTIN_fYi9m1h7s2zKCPbCMTgHo',

  // Header row index (0-based, row 1 = index 0)
  HEADER_ROW: 0,

  // Pre-defined column mapping with indexes (0-based)
  // IMPORTANT: These must match the actual sheet column layout exactly
  COLUMNS: {
    'ID': { dataField: 'id', index: 0 },
    'Submitted At': { dataField: 'submittedAt', index: 1 },
    'Shopify Product ID': { dataField: 'productId', index: 2 },
    'Product Title': { dataField: 'productName', index: 3 },
    'Shopify Customer ID': { dataField: 'customerId', index: 4 },
    'First Name': { dataField: 'firstName', index: 5 },
    'Last Name': { dataField: 'lastName', index: 6 },
    'Email': { dataField: 'email', index: 7 },
    'Phone Number': { dataField: 'phone', index: 8 },
    'Status': { dataField: 'status', index: 9 }
  },

  // Pre-defined product to tab mapping for direct lookup
  // Maps Shopify Product ID to Google Sheet tab name
  PRODUCT_TAB_MAPPING: {
    '7590193332318': 'Kickball - Saturday - Open',    // Big Apple Kickball - Saturday - Open Division - Spring 2026
    '7590021300318': 'Kickball - Tuesday - Open',     // Big Apple Kickball - Tuesday - Open Division - Spring 2026
    '7587513565278': 'Kickball - Monday - Open',      // Big Apple Kickball - Monday - Open Division - Spring 2026
    '7587512582238': 'Kickball - Saturday - WTNB',   // Big Apple Kickball - Saturday - WTNB+ Division - Spring 2026
    '7581465968734': 'Kickball - Sunday - Open',      // Big Apple Kickball - Sunday - Open Division - Spring 2026
    '7590021365854': 'Kickball - Thursday - WTNB',    // Big Apple Kickball - Thursday - WTNB+ Division - Spring 2026
    '7590021333086': 'Kickball - Wednesday - Open',   // Big Apple Kickball - Wednesday - Open Division - Spring 2026
    '7590248874078': 'Bowling - Monday - Open',       // Big Apple Bowling - Monday - Open Division - Spring 2026
    '7590249070686': 'Bowling - Sunday - Open'        // Big Apple Bowling - Sunday - Open Division - Spring 2026
  }
};

/**
 * Get column index for a given data field
 * @param {string} field - The data field name (e.g., 'email', 'productId')
 * @returns {number} Column index, or -1 if not found
 */
export function getFieldIndex(field) {
  const entry = Object.values(CONFIG.COLUMNS).find(col => col.dataField === field);
  return entry ? entry.index : -1;
}

/**
 * Get Slack configuration for notifications
 * @returns {Object} Slack config object
 */
export function getSlackConfig() {
  return {
    webhookUrl: PropertiesService.getScriptProperties().getProperty('SLACK_WEBHOOK_URL'),
    enabled: true
  };
}