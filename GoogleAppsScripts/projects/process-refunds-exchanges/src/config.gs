// =============================================================================
// PROJECT-SPECIFIC CONFIGURATION AND UTILITIES
// process-refunds-exchanges specific constants and functions
// =============================================================================

// =============================================================================
// PROJECT-SPECIFIC CONSTANTS
// =============================================================================

const SHEET_ID = "11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw";
const SHEET_GID = "1435845892";
const WAITLIST_RESPONSES_URL = 'https://docs.google.com/spreadsheets/d/1wFoayUoIx1PPOO0TtuS0Jnwb5hoIbgCd_kebMeYNzGQ/edit?resourcekey=&gid=744639660#gid=744639660';
const SHOPIFY_LOGIN_URL = 'https://shopify.com/55475535966/account';
const BARS_LOGO_URL = "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/122824_BARS_Logo_Full-Black.png?v=1741951481";

const MODE = 'PROD'; // Options: 'DEVELOPMENT', 'PROD-TEST', 'PROD'

const NGROK_URL = 'https://db88b7c69780.ngrok-free.app';
const PROD_URL = 'https://bars-backend.onrender.com';

const DEBUG_EMAIL = 'web@bigapplerecsports.com';

// =============================================================================
// DYNAMIC CONFIGURATION
// =============================================================================

/**
 * Get API URL based on MODE
 * @returns {string} API URL to use
 */
function getApiUrl() {
  if (MODE === 'DEVELOPMENT') {
    return NGROK_URL;
  } else {
    return PROD_URL;
  }
}
