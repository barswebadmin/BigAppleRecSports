/**
 * General Utility Functions
 * Phone normalization, string manipulation, etc.
 */

/**
 * Normalize phone number to XXX-XXX-XXXX format
 * @param {string} rawPhone - Raw phone number
 * @returns {string|null} - Normalized phone or null
 */
function normalizePhone(rawPhone) {
  if (!rawPhone) return null;

  const digitsOnly = rawPhone.toString().replace(/\D/g, '');

  const normalized = digitsOnly.length === 11 && digitsOnly.startsWith('1')
    ? digitsOnly.slice(1)
    : digitsOnly;

  if (normalized.length !== 10) {
    Logger.log(`⚠️ Unexpected phone format: "${rawPhone}" → "${normalized}"`);
    return null;
  }

  return `${normalized.slice(0, 3)}-${normalized.slice(3, 6)}-${normalized.slice(6)}`;
}

/**
 * Capitalize first letter of string
 * @param {string} str - String to capitalize
 * @returns {string} - Capitalized string
 */
function capitalize(str) {
  if (!str || typeof str !== 'string') return str;
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

/**
 * Get league info (leadership email and product URL)
 * @param {string} league - League name
 * @param {string} season - Season
 * @param {string} year - Year
 * @returns {Object} - {leadershipEmail, barsProductUrl}
 */
function getLeagueInfo(league, season, year) {
  const barsProductUrl =
    `${SHOPIFY_STORE_URL}/products/${year}-${season.toLowerCase()}-` +
    league
      .toLowerCase()
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .replace(/[+]/g, '')
      .replace('-division', 'div');

  const leadershipEmail = getLeadershipEmailForLeague(league);

  return {
    leadershipEmail,
    barsProductUrl
  };
}

/**
 * Get leadership email for specific league
 * @param {string} league - Full league name
 * @returns {string} - Leadership email
 */
function getLeadershipEmailForLeague(league) {
  let leadershipEmail;
  
  switch (league) {
    case 'Bowling - Sunday - Open Division':
      leadershipEmail = 'bowling.sunday@bigapplerecsports.com';
      break;
    case 'Bowling - Monday - Open Division':
      leadershipEmail = 'bowling.monday@bigapplerecsports.com';
      break;
    case 'Bowling - Monday - WTNB+ Division':
      leadershipEmail = 'bowling.monday@bigapplerecsports.com';
      break;
    case 'Dodgeball - Sunday - WTNB+ Division':
      leadershipEmail = 'dodgeball.wtnb.draft@bigapplerecsports.com';
      break;
    case 'Dodgeball - Sunday - Open Division':
      leadershipEmail = 'dodgeball.draft.smallball@bigapplerecsports.com';
      break;
    case 'Dodgeball - Monday - Open Division':
      leadershipEmail = 'dodgeball.bigball@bigapplerecsports.com';
      break;
    case 'Dodgeball - Tuesday - Open Division':
      leadershipEmail = 'dodgeball.social.smallball@bigapplerecsports.com';
      break;
    case 'Dodgeball - Tuesday Advanced - Open Division':
      leadershipEmail = 'dodgeball.social.smallball@bigapplerecsports.com';
      break;
    case 'Dodgeball - Tuesday Social - Open Division':
      leadershipEmail = 'dodgeball.social.smallball@bigapplerecsports.com';
      break;
    case 'Dodgeball - Wednesday - WTNB+ Division':
      leadershipEmail = 'dodgeball.wtnb.social@bigapplerecsports.com';
      break;
    case 'Dodgeball - Thursday - Open Division':
      leadershipEmail = 'dodgeball.foamball@bigapplerecsports.com';
      break;
    case 'Kickball - Sunday - Open Division':
      leadershipEmail = 'kickball.sunday@bigapplerecsports.com';
      break;
    case 'Kickball - Monday - Open Division':
      leadershipEmail = 'kickball.monday@bigapplerecsports.com';
      break;
    case 'Kickball - Tuesday - Open Division':
      leadershipEmail = 'kickball.tuesday@bigapplerecsports.com';
      break;
    case 'Kickball - Wednesday - Open Division':
      leadershipEmail = 'kickball.wednesday@bigapplerecsports.com';
      break;
    case 'Kickball - Thursday - WTNB+ Division':
      leadershipEmail = 'kickball.wtnb@bigapplerecsports.com';
      break;
    case 'Kickball - Saturday - WTNB+ Division':
      leadershipEmail = 'kickball.wtnb@bigapplerecsports.com';
      break;
    case 'Kickball - Saturday - Open Division':
      leadershipEmail = 'kickball.saturday.open@bigapplerecsports.com';
      break;
    case 'Pickleball - Sunday - Open Division':
      leadershipEmail = 'pickleball.advanced@bigapplerecsports.com';
      break;
    case 'Pickleball - Sunday - WTNB+ Division':
      leadershipEmail = 'pickleball.wtnb@bigapplerecsports.com';
      break;
    case 'Pickleball - Tuesday - Open Division':
      leadershipEmail = 'pickleball.social@bigapplerecsports.com';
      break;
    default:
      leadershipEmail = 'executive-board@bigapplerecsports.com';
      break;
  }
  
  return leadershipEmail;
}

/**
 * Check if two dates are the same minute
 * @param {Date} date1 - First date
 * @param {Date} date2 - Second date
 * @returns {boolean} - True if same minute
 */
function isSameMinute(date1, date2) {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate() &&
    date1.getHours() === date2.getHours() &&
    date1.getMinutes() === date2.getMinutes()
  );
}

