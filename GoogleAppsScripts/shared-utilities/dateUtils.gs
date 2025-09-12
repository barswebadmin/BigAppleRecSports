/**
 * Date Helper Functions
 * Copy these functions into your Google Apps Script projects as needed
 */

/**
 * Format a date for Shopify API (ISO 8601 format)
 * @param {Date} date - The date to format
 * @returns {string} ISO 8601 formatted date string
 */
function formatDateForShopify(date) {
  if (!date || !(date instanceof Date)) {
    throw new Error('Invalid date provided');
  }
  return date.toISOString();
}

/**
 * Parse a date string in various formats
 * @param {string} dateString - Date string to parse
 * @returns {Date} Parsed date object
 */
function parseFlexibleDate(dateString) {
  if (!dateString) {
    throw new Error('Date string is required');
  }
  
  // Try standard Date parsing first
  let date = new Date(dateString);
  
  // If that fails, try some common formats
  if (isNaN(date.getTime())) {
    // Try MM/DD/YYYY format
    const mmddyyyy = dateString.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (mmddyyyy) {
      date = new Date(parseInt(mmddyyyy[3]), parseInt(mmddyyyy[1]) - 1, parseInt(mmddyyyy[2]));
    }
    
    // Try DD/MM/YYYY format
    const ddmmyyyy = dateString.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (ddmmyyyy && isNaN(date.getTime())) {
      date = new Date(parseInt(ddmmyyyy[3]), parseInt(ddmmyyyy[2]) - 1, parseInt(ddmmyyyy[1]));
    }
  }
  
  if (isNaN(date.getTime())) {
    throw new Error(`Unable to parse date: ${dateString}`);
  }
  
  return date;
}

/**
 * Get the start of the current season based on a date
 * @param {Date} date - Reference date
 * @returns {Date} Season start date
 */
function getSeasonStart(date = new Date()) {
  const year = date.getFullYear();
  const month = date.getMonth(); // 0-based
  
  // Spring: March - May
  if (month >= 2 && month <= 4) {
    return new Date(year, 2, 1); // March 1st
  }
  // Summer: June - August  
  else if (month >= 5 && month <= 7) {
    return new Date(year, 5, 1); // June 1st
  }
  // Fall: September - November
  else if (month >= 8 && month <= 10) {
    return new Date(year, 8, 1); // September 1st
  }
  // Winter: December - February
  else {
    if (month === 11) {
      return new Date(year, 11, 1); // December 1st
    } else {
      return new Date(year - 1, 11, 1); // Previous December 1st
    }
  }
}

/**
 * Format a date for display in Slack messages
 * @param {Date} date - Date to format
 * @returns {string} Formatted date string
 */
function formatDateForSlack(date) {
  if (!date || !(date instanceof Date)) {
    return 'Unknown Date';
  }
  
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

/**
 * Calculate business days between two dates
 * @param {Date} startDate - Start date
 * @param {Date} endDate - End date
 * @returns {number} Number of business days
 */
function getBusinessDaysBetween(startDate, endDate) {
  if (!startDate || !endDate || !(startDate instanceof Date) || !(endDate instanceof Date)) {
    throw new Error('Valid start and end dates are required');
  }
  
  let count = 0;
  const current = new Date(startDate);
  
  while (current <= endDate) {
    const dayOfWeek = current.getDay();
    if (dayOfWeek !== 0 && dayOfWeek !== 6) { // Not Sunday (0) or Saturday (6)
      count++;
    }
    current.setDate(current.getDate() + 1);
  }
  
  return count;
}

/**
 * Add business days to a date (excludes weekends)
 * @param {Date} date - Starting date
 * @param {number} businessDays - Number of business days to add
 * @returns {Date} New date with business days added
 */
function addBusinessDays(date, businessDays) {
  if (!date || !(date instanceof Date)) {
    throw new Error('Valid date is required');
  }
  
  const result = new Date(date);
  let daysAdded = 0;
  
  while (daysAdded < businessDays) {
    result.setDate(result.getDate() + 1);
    const dayOfWeek = result.getDay();
    
    // If it's not a weekend, count it
    if (dayOfWeek !== 0 && dayOfWeek !== 6) {
      daysAdded++;
    }
  }
  
  return result;
}

// =============================================================================
// ADDITIONAL DATE FORMATTING FUNCTIONS (moved from project-specific Utils)
// =============================================================================

/**
 * Format date only (US format, short year)
 * @param {Date|string} date - Date to format
 * @returns {string|null} Formatted date string or null if error
 */
const formatDateOnly = date => {
  try {
    return new Date(date).toLocaleDateString("en-US", { year: "2-digit", month: "numeric", day: "numeric" });
  } catch (e) {
    Logger.log(`❌ Error formatting date: ${e}`);
    return null;
  }
};

/**
 * Format date and time together
 * @param {Date|string} date - Date to format
 * @returns {string} Formatted date and time string if Date is valid, otherwise null
 */
const formatDateAndTime = date => {
  try {
    const d = new Date(date);
    const datePart = d.toLocaleDateString("en-US", { year: "2-digit", month: "numeric", day: "numeric" });
    const timePart = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
    return `${datePart} at ${timePart}`;
  } catch (e) {
    Logger.log(`❌ Error formatting date and time: ${e}`);
    return null;
  }
};

/**
 * Extract season dates from product description HTML
 * @param {string} descriptionHtml - HTML description text
 * @returns {Array} Array of [startDate, offDates] or [null, null] if not found
 */
function extractSeasonDates(descriptionHtml) {
  // Strip HTML tags and decode entities
  const text = descriptionHtml.replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ").replace(/\s+/g, " ").trim();
  Logger.log(`stripped descriptionHtml: ${text}`);

  const seasonDatesRegex =
    /Season Dates[^:\d]*[:\s]*?(\d{1,2}\/\d{1,2}\/\d{2,4})\s*[–—-]\s*(\d{1,2}\/\d{1,2}\/\d{2,4})(?:\s*\(\d+\s+weeks(?:,\s*off\s+([^)]+))?\))?/i;

  const match = text.match(seasonDatesRegex);
  Logger.log(`match: ${match}`);

  if (!match) return [null, null];

  const seasonStartDate = match[1];
  const offDatesStr = match[3] || null;
  if (!seasonStartDate?.includes('/') || (!!offDatesStr && !offDatesStr?.includes('/')) ) return [null, null];

  return [seasonStartDate, offDatesStr];
}

/**
 * Format time only (useful for events/schedules)
 * @param {Date|string} date - Date to format
 * @returns {string|null} Formatted time string or null if invalid
 */
const formatTimeOnly = date => {
  if (!date) return null;
  return new Date(date).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
};
