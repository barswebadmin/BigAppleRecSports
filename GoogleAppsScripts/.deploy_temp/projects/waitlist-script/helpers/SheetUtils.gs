const capitalize = str => {
  return str[0].toUpperCase() + str.slice(1)
}

function normalizePhone(rawPhone) {
  if (!rawPhone) return '';

  // Force to string in case a number is passed
  const digitsOnly = rawPhone.toString().replace(/\D/g, '');

  // Remove leading 1 if present (for US country code)
  const normalized = digitsOnly.length === 11 && digitsOnly.startsWith('1')
    ? digitsOnly.slice(1)
    : digitsOnly;

  // Ensure we have exactly 10 digits
  if (normalized.length !== 10) {
    Logger.log(`⚠️ Unexpected phone number format: "${rawPhone}" → "${normalized}"`);
    return null;
  }

  // Format as XXX-XXX-XXXX
  return `${normalized.slice(0, 3)}-${normalized.slice(3, 6)}-${normalized.slice(6)}`;
}

function getCurrentSeasonAndYearFromSpreadsheetTitle() {
  const spreadsheetName = SpreadsheetApp.getActiveSpreadsheet().getName();
  const lower = spreadsheetName.toLowerCase();
  const seasons = ['summer', 'spring', 'fall', 'winter'];

  // Remove the word "waitlist" if present
  const cleaned = lower.replace(/waitlist/i, '').trim();

  // Split by spaces and identify season + year
  const parts = cleaned.split(/\s+/);

  let season = null;
  let year = null;

  for (const part of parts) {
    if (seasons.includes(part)) {
      season = part;
    } else if (/^\d{4}$/.test(part)) {
      year = part;
    }
  }

  return { season, year };
}

const getLeagueInfo = (league,season, year) => {
  
  const barsProductUrl =
    `https://www.bigapplerecsports.com/products/${year}-${season.toLowerCase()}-` +
    league
      .toLowerCase()
      .replace(/\s+/g, '-')         // replace spaces with dash
      .replace(/-+/g, '-')          // remove duplicate dashes
      .replace(/[+]/g, '')          // remove plus signs if needed
      .replace('-division','div')

  let leadershipEmail
  switch (league) {
    case 'Bowling - Sunday - Open Division':
      leadershipEmail = 'bowling.sunday@bigapplerecsports.com'
      break;
    case 'Bowling - Monday - Open Division':
      leadershipEmail = 'bowling.monday@bigapplerecsports.com'
      break;
    case 'Bowling - Monday - WTNB+ Division':
      leadershipEmail = 'bowling.monday@bigapplerecsports.com'
      break;
    case 'Dodgeball - Sunday - WTNB+ Division':
      leadershipEmail = 'dodgeball.wtnb.draft@bigapplerecsports.com'
      break;
    case 'Dodgeball - Sunday - Open Division':
      leadershipEmail = 'dodgeball.draft.smallball@bigapplerecsports.com'
      break;
    case 'Dodgeball - Monday - Open Division':
      leadershipEmail = 'dodgeball.bigball@bigapplerecsports.com'
      break;
    case 'Dodgeball - Tuesday - Open Division':
      leadershipEmail = 'dodgeball.social.smallball@bigapplerecsports.com'
      break;
    case 'Dodgeball - Tuesday Advanced - Open Division':
      leadershipEmail = 'dodgeball.social.smallball@bigapplerecsports.com'
      break;
    case 'Dodgeball - Tuesday Social - Open Division':
      leadershipEmail = 'dodgeball.social.smallball@bigapplerecsports.com'
      break;
    case 'Dodgeball - Wednesday - WTNB+ Division':
      leadershipEmail = 'dodgeball.wtnb.social@bigapplerecsports.com'
      break;
    case 'Dodgeball - Thursday - Open Division':
      leadershipEmail = 'dodgeball.foamball@bigapplerecsports.com'
      break;
    case 'Kickball - Sunday - Open Division':
      leadershipEmail = 'kickball.sunday@bigapplerecsports.com'
      break;
    case 'Kickball - Monday - Open Division':
      leadershipEmail = 'kickball.monday@bigapplerecsports.com'
      break;
    case 'Kickball - Tuesday - Open Division':
      leadershipEmail = 'kickball.tuesday@bigapplerecsports.com'
      break;
    case 'Kickball - Wednesday - Open Division':
      leadershipEmail = 'kickball.wednesday@bigapplerecsports.com'
      break;
    case 'Kickball - Thursday - WTNB+ Division':
      leadershipEmail = 'kickball.wtnb@bigapplerecsports.com'
      break;
    case 'Kickball - Saturday - WTNB+ Division':
      leadershipEmail = 'kickball.wtnb@bigapplerecsports.com'
      break;
    case 'Kickball - Saturday - Open Division':
      leadershipEmail = 'kickball.saturday.open@bigapplerecsports.com'
      break;
    case 'Pickleball - Sunday - Open Division':
      leadershipEmail = 'pickleball.advanced@bigapplerecsports.com'
      break;
    case 'Pickleball - Sunday - WTNB+ Division':
      leadershipEmail = 'pickleball.wtnb@bigapplerecsports.com'
      break;
    case 'Pickleball - Tuesday - Open Division':
      leadershipEmail = 'pickleball.social@bigapplerecsports.com'
      break;
    default:
      leadershipEmail = 'executive-board@bigapplerecsports.com'
      break;
  }

  return {
    leadershipEmail, 
    barsProductUrl
    }
}