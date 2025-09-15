/**
 * Season dates parsing functions
 * Handles parsing of season start/end dates with flexible formats
 *
 * @fileoverview Parse season dates from D/E columns with format flexibility
 * @requires ../config/constants.gs
 * @requires ../helpers/normalizers.gs
 * @requires ../helpers/textUtils.gs
 */

// Import references for editor support
/// <reference path="../config/constants.gs" />
/// <reference path="../helpers/normalizers.gs" />
/// <reference path="../helpers/textUtils.gs" />

/**
 * Parse season start and end dates with flexible format support
 * @param {string} startDateStr - Raw start date string from column D
 * @param {string} endDateStr - Raw end date string from column E
 * @param {Array<string>} unresolved - Array to track unresolved fields
 * @returns {{season: string, year: number, seasonStartDate: Date, seasonEndDate: Date, updatedUnresolved: Array<string>}} Parsed season information
 */
function parseSeasonDates_(startDateStr, endDateStr, unresolved) {
  const updatedUnresolved = [...unresolved];
  let season = null;
  let year = null;
  let seasonStartDate = null;
  let seasonEndDate = null;

  try {
    // Parse start date
    seasonStartDate = parseFlexibleDate_(startDateStr?.trim());
    if (seasonStartDate) {
      // Remove seasonStartDate from unresolved
      const startIndex = updatedUnresolved.indexOf("seasonStartDate");
      if (startIndex > -1) updatedUnresolved.splice(startIndex, 1);
    }

    // Parse end date
    seasonEndDate = parseFlexibleDate_(endDateStr?.trim());
    if (seasonEndDate) {
      // Remove seasonEndDate from unresolved
      const endIndex = updatedUnresolved.indexOf("seasonEndDate");
      if (endIndex > -1) updatedUnresolved.splice(endIndex, 1);
    }

    // Derive season and year from the start date
    if (seasonStartDate) {
      const derivedInfo = deriveSeasonYearFromDate_(seasonStartDate);
      season = derivedInfo.season;
      year = derivedInfo.year;

      if (season) {
        const seasonIndex = updatedUnresolved.indexOf("season");
        if (seasonIndex > -1) updatedUnresolved.splice(seasonIndex, 1);
      }

      if (year) {
        const yearIndex = updatedUnresolved.indexOf("year");
        if (yearIndex > -1) updatedUnresolved.splice(yearIndex, 1);
      }
    }
  } catch (error) {
    console.warn('Error parsing season dates:', error);
  }

  return {
    season,
    year,
    seasonStartDate,
    seasonEndDate,
    updatedUnresolved3
  };
}

/**
 * Parse a date string with flexible format support
 * Handles: M/d/yy, M/d/yyyy, M-d-yy, M-d-yyyy, "October 12", "Oct 14th"
 * @param {string} dateStr - Date string to parse
 * @returns {Date|null} Parsed Date object in UTC or null if invalid
 */
function parseFlexibleDate_(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') {
    return null;
  }

  const cleanStr = dateStr.trim();
  if (!cleanStr) {
    return null;
  }

  // Handle various date formats
  try {
    // Try numeric formats first: M/d/yy, M/d/yyyy, M-d-yy, M-d-yyyy
    const numericMatch = cleanStr.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{2,4})$/);
    if (numericMatch) {
      const [, month, day, year] = numericMatch;
      return createUTCDate_(parseInt(month), parseInt(day), normalizeYear_(parseInt(year)));
    }

    // Handle text-based formats: "October 12", "Oct 14th", "October 12th"
    const textMatch = cleanStr.match(/^([a-zA-Z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\s*$/);
    if (textMatch) {
      const [, monthName, day] = textMatch;
      const month = parseMonthName_(monthName);
      if (month) {
        // Use current year as default for text-based dates
        const currentYear = new Date().getFullYear();
        return createUTCDate_(month, parseInt(day), currentYear);
      }
    }

    // Fallback: try JavaScript's Date parsing (less reliable but covers edge cases)
    const fallbackDate = new Date(cleanStr);
    if (!isNaN(fallbackDate.getTime())) {
      // Convert to UTC midnight
      return new Date(Date.UTC(
        fallbackDate.getFullYear(),
        fallbackDate.getMonth(),
        fallbackDate.getDate()
      ));
    }

  } catch (error) {
    console.warn('Error parsing date:', cleanStr, error);
  }

  return null;
}

/**
 * Create a UTC Date object for the given month/day/year
 * @param {number} month - Month (1-12)
 * @param {number} day - Day (1-31)
 * @param {number} year - Full year (e.g., 2025)
 * @returns {Date} UTC Date object at 4:00 AM UTC (midnight EST)
 */
function createUTCDate_(month, day, year) {
  // Create date at 4:00 AM UTC (which is midnight EST/EDT)
  // This handles the timezone conversion for Eastern timezone
  return new Date(Date.UTC(year, month - 1, day, 4, 0, 0));
}

/**
 * Normalize 2-digit year to 4-digit year
 * @param {number} year - 2 or 4 digit year
 * @returns {number} 4-digit year
 */
function normalizeYear_(year) {
  if (year < 100) {
    // Assume years 00-30 are 2000s, 31-99 are 1900s
    return year <= 30 ? 2000 + year : 1900 + year;
  }
  return year;
}

/**
 * Parse month name to month number
 * @param {string} monthName - Month name (full or abbreviated)
 * @returns {number|null} Month number (1-12) or null if invalid
 */
function parseMonthName_(monthName) {
  const monthNames = {
    // Full month names
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,

    // Abbreviated month names
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
  };

  const normalizedName = monthName.toLowerCase().trim();
  return monthNames[normalizedName] || null;
}
