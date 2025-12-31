/**
 * Unified Waitlist System Configuration
 * All constants, URLs, and configuration in one place
 */

// =============================================================================
// EXTERNAL URLS
// =============================================================================

const BARS_LOGO_URL = "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/122824_BARS_Logo_Full-Black.png?v=1741951481";
const WAITLIST_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxdYCtG7OpL-teVYVsK8kTtb5wWmPc9miOYO5Whs59zRa66oTCWT_XyDO7EIzZax7eK/exec";
const SHOPIFY_ADMIN_URL = "https://admin.shopify.com/store/09fe59-3";
const SHOPIFY_STORE_URL = "https://www.bigapplerecsports.com";

// =============================================================================
// EMAIL CONFIGURATION
// =============================================================================

const DEBUG_EMAIL = 'jdazz87@gmail.com';
const WAITLIST_SPREADSHEET_ID = '15YSo-Z6e3DP6drASxJ1nykvco0n_5la8yOiq2yuVPzk';

const SPORT_EMAIL_MAP = {
  'basketball': 'basketball@bigapplerecsports.com',
  'volleyball': 'volleyball@bigapplerecsports.com',
  'soccer': 'soccer@bigapplerecsports.com',
  'football': 'soccer@bigapplerecsports.com',
  'softball': 'softball@bigapplerecsports.com',
  'kickball': 'kickball@bigapplerecsports.com',
  'dodgeball': 'dodgeball@bigapplerecsports.com',
  'bowling': 'bowling@bigapplerecsports.com',
  'tennis': 'tennis@bigapplerecsports.com',
  'pickleball': 'pickleball@bigapplerecsports.com',
  'cornhole': 'cornhole@bigapplerecsports.com',
  'spikeball': 'spikeball@bigapplerecsports.com',
  'default': 'info@bigapplerecsports.com'
};

// =============================================================================
// FORM CONFIGURATION
// =============================================================================

const QUESTION_TITLE = 'Please select the league you want to sign up for (leagues will be added as they sell out):';
const NO_WAITLISTS_SENTINEL = 'No waitlists currently available - registrations have not yet gone live / sold out';

// =============================================================================
// SORTING CONFIGURATION
// =============================================================================

const DAYS_OF_WEEK = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const DIVISIONS = ['Open', 'WTNB+', 'WTNB', 'wtnb'];
const SPORTS = ['Dodgeball', 'Kickball', 'Pickleball', 'Bowling', 'Basketball', 'Volleyball', 'Soccer', 'Softball'];

// =============================================================================
// SHOPIFY WEBHOOK CONFIGURATION
// =============================================================================

const SHOPIFY_WEBHOOK_TOPICS = {
  PRODUCT_UPDATE: 'products/update',
  PRODUCT_CREATE: 'products/create',
  INVENTORY_UPDATE: 'inventory_levels/update'
};

// =============================================================================
// HELPER FUNCTIONS TO GET SPORT EMAIL
// =============================================================================

/**
 * Get sport-specific email alias from league name
 * @param {string} league - League name (e.g., "Kickball - Sunday - Open Division")
 * @returns {string} - Email alias (e.g., "kickball@bigapplerecsports.com")
 */
function getSportEmailAlias(league) {
  const lowerLeague = league.toLowerCase();

  for (const sport in SPORT_EMAIL_MAP) {
    if (lowerLeague.includes(sport)) {
      return SPORT_EMAIL_MAP[sport];
    }
  }

  return SPORT_EMAIL_MAP['default'];
}

/**
 * Get sport email from league parts
 * @param {string} sport - Sport name
 * @returns {string} - Email address
 */
function getSportEmail(sport) {
  const lowerSport = sport.toLowerCase();
  return SPORT_EMAIL_MAP[lowerSport] || SPORT_EMAIL_MAP['default'];
}


// Deploy_ID: 20251230120725_3510
