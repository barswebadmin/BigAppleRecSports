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

const MODE = 'debug'; // Options: 'prodApi', 'debugApi'

// Note: BACKEND_API_URL removed per user request - now stored in secrets
const LOCAL_TUNNEL_URL = 'https://b683e45137ad.ngrok-free.app';

const DEBUG_EMAIL = 'web@bigapplerecsports.com';

// =============================================================================
// DYNAMIC CONFIGURATION
// =============================================================================

/**
 * Get API URL based on MODE and secrets
 * @returns {string} API URL to use
 */
function getApiUrl() {
  if (MODE.includes('prod')) {
    try {
      return getSecret('BACKEND_API_URL');
    } catch (error) {
      Logger.log(`⚠️ Could not get BACKEND_API_URL from secrets, using fallback`);
      return 'https://bars-backend.onrender.com'; // Fallback
    }
  } else {
    return LOCAL_TUNNEL_URL;
  }
}

// Legacy API_URL constant for backward compatibility
const API_URL = getApiUrl();
