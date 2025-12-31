/**
 * Unified Waitlist System Configuration
 * All constants, URLs, and configuration in one place
 */

// =============================================================================
// EXTERNAL URLS
// =============================================================================

export const WAITLIST_SPREADSHEET_ID = '15YSo-Z6e3DP6drASxJ1nykvco0n_5la8yOiq2yuVPzk';
export const BARS_LOGO_URL = "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/122824_BARS_Logo_Full-Black.png?v=1741951481";
export const WAITLIST_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxdYCtG7OpL-teVYVsK8kTtb5wWmPc9miOYO5Whs59zRa66oTCWT_XyDO7EIzZax7eK/exec";
export const SHOPIFY_ADMIN_URL = "https://admin.shopify.com/store/09fe59-3";
export const SHOPIFY_STORE_URL = "https://www.bigapplerecsports.com";

// =============================================================================
// EMAIL CONFIGURATION
// =============================================================================

export const DEBUG_EMAIL = 'jdazz87@gmail.com';

export const SPORT_EMAIL_MAP = {
  'kickball': 'kickball@bigapplerecsports.com',
  'dodgeball': 'dodgeball@bigapplerecsports.com',
  'bowling': 'bowling@bigapplerecsports.com',
  'pickleball': 'pickleball@bigapplerecsports.com',
  'default': 'info@bigapplerecsports.com'
};

// =============================================================================
// FORM CONFIGURATION
// =============================================================================

export const QUESTION_TITLE = 'Please select the league you want to sign up for (leagues will be added as they sell out):';
export const NO_WAITLISTS_SENTINEL = 'No waitlists currently available - registrations have not yet gone live / sold out';

// =============================================================================
// SORTING CONFIGURATION
// =============================================================================

export const DAYS_OF_WEEK = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
export const DIVISIONS = ['Open', 'WTNB+', 'WTNB', 'wtnb'];
export const SPORTS = ['Dodgeball', 'Kickball', 'Pickleball', 'Bowling', 'Basketball', 'Volleyball', 'Soccer', 'Softball'];

// =============================================================================
// SHOPIFY WEBHOOK CONFIGURATION
// =============================================================================

export const SHOPIFY_WEBHOOK_TOPICS = {
  PRODUCT_UPDATE: 'products/update',
  PRODUCT_CREATE: 'products/create',
  INVENTORY_UPDATE: 'inventory_levels/update'
};

