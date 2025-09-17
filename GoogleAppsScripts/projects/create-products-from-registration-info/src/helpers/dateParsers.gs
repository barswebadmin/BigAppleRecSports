/**
 * Date parsing utilities with standalone functions
 * Handles flexible date and datetime formats with various input types
 *
 * @fileoverview Central date parsing utilities for consistent date handling
 * @requires textUtils.gs
 */

// Import references for editor support
/// <reference path="textUtils.gs" />

/**
 * Calculate the appropriate year for a date if no year is provided
 * @param {string} dateStr - Date string to parse (e.g., "October 15", "10/15")
 * @returns {number} Current year or next year if the date has already passed this year
 */
function calculateYearIfNotProvided(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') {
    return new Date().getFullYear();
  }

  const cleanStr = dateStr.trim();
  if (!cleanStr) {
    return new Date().getFullYear();
  }

  let month = null;
  let day = null;

  // Try to extract month and day from the string
  // Handle numeric formats: M/d, M-d
  const numericMatch = cleanStr.match(/^(\d{1,2})[\/-](\d{1,2})/);
  if (numericMatch) {
    month = parseInt(numericMatch[1]);
    day = parseInt(numericMatch[2]);
  } else {
    // Handle text-based formats: "October 15", "Oct 15th"
    const textMatch = cleanStr.match(/^([a-zA-Z]+)\s+(\d{1,2})/);
    if (textMatch) {
      const [, monthName, dayStr] = textMatch;
      month = parseMonthName_(monthName);
      day = parseInt(dayStr);
    }
  }

  if (!month || !day || month < 1 || month > 12 || day < 1 || day > 31) {
    return new Date().getFullYear();
  }

  const now = new Date();
  let targetYear = now.getFullYear();

  // Create test date to see if it has passed this year
  const testDate = new Date(targetYear, month - 1, day);
  if (testDate < now) {
    // Date has passed this year, use next year
    targetYear++;
  }

  return targetYear;
}

/**
 * Parse flexible date format (date only, no time)
 * @param {string} s - Date string to parse
 * @param {Array<string>} unresolved - Array to track unresolved fields
 * @param {string} fieldName - Name of field being parsed (for unresolved tracking)
 * @returns {Date|string} Parsed Date object or empty string if invalid
 */
function parseDateFlexibleDateOnly_(s, unresolved, fieldName) {
  // Accepts "10-19-2025", "9/25/25", "October 12" (assume year = current; if passed already, next year)
  const d = parseFlexible_(s, { assumeDateOnly: true });
  if (!d) {
    // Date not found - leave fieldName in unresolved array (if provided)
    return '';
  }

  // Successfully found date - remove from unresolved (if fieldName provided)
  if (fieldName && unresolved) {
    const index = unresolved.indexOf(fieldName);
    if (index > -1) unresolved.splice(index, 1);
  }

  // Zero out time
  d.setHours(0,0,0,0);
  return d;
}

/**
 * Parse flexible datetime format
 * @param {string} s - DateTime string to parse
 * @param {Date} fallbackTimeDateOnly - Fallback time if only date is found
 * @param {Array<string>} unresolved - Array to track unresolved fields
 * @param {string} fieldName - Name of field being parsed
 * @returns {Date|string} Parsed Date object or empty string if invalid
 */
function parseDateFlexibleDateTime_(s, fallbackTimeDateOnly, unresolved, fieldName) {
  // Enhanced to handle formats like "Sept 16th 7PM", "Weds, Sept. 3rd, 6pm", "8/29/25 @ 7pm"
  if (!s || !s.trim()) return '';

  const cleanInput = s.trim();

  // Try enhanced parsing first for new formats
  const enhancedResult = parseEnhancedDateTime_(cleanInput);
  if (enhancedResult) {
    // Successfully found datetime - remove from unresolved (if fieldName provided)
    if (fieldName && unresolved) {
      const index = unresolved.indexOf(fieldName);
      if (index > -1) unresolved.splice(index, 1);
    }
    return enhancedResult;
  }

  // Fall back to original parsing logic
  const d = parseFlexible_(s, { assumeDateTime: true });
  if (!d) {
    // If it's only a date, use sport start time as the time-of-day
    const maybeDate = parseFlexible_(s, { assumeDateOnly: true });
    if (maybeDate && fallbackTimeDateOnly instanceof Date) {
      maybeDate.setHours(fallbackTimeDateOnly.getHours(), fallbackTimeDateOnly.getMinutes(), 0, 0);

      // Successfully found datetime - remove from unresolved (if fieldName provided)
      if (fieldName && unresolved) {
        const index = unresolved.indexOf(fieldName);
        if (index > -1) unresolved.splice(index, 1);
      }

      return maybeDate;
    }
    return '';
  }

  // Successfully found datetime - remove from unresolved (if fieldName provided)
  if (fieldName && unresolved) {
    const index = unresolved.indexOf(fieldName);
    if (index > -1) unresolved.splice(index, 1);
  }

  return d;
}

/**
 * Parse a date string with UTC support and flexible formats
 * Handles: M/d/yy, M/d/yyyy, M-d-yy, M-d-yyyy, "October 12", "Oct 14th"
 * @param {string} dateStr - Date string to parse
 * @param {boolean} useUTC - Whether to return UTC timestamp at 4:00 AM
 * @returns {Date|null} Parsed Date object or null if invalid
 */
function parseFlexibleDate_(dateStr, useUTC = false) {
  if (!dateStr || typeof dateStr !== 'string') {
    return null;
  }

  const cleanStr = dateStr.trim();
  if (!cleanStr) {
    return null;
  }

  Logger.log(`parseFlexibleDate_ input: "${dateStr}" (type: ${typeof dateStr}), cleanStr: "${cleanStr}", useUTC: ${useUTC}`);

  // Handle various date formats
  try {
    // Try numeric formats first: M/d/yy, M/d/yyyy, M-d-yy, M-d-yyyy
    const numericMatch = cleanStr.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{2,4})$/);
    if (numericMatch) {
      const [, month, day, year] = numericMatch;
      const normalizedYear = normalizeYear_(parseInt(year));
      Logger.log(`numericMatch found: month=${month}, day=${day}, year=${year}, normalizedYear=${normalizedYear}`);
      if (useUTC) {
        const result = createUTCDate_(parseInt(month), parseInt(day), normalizedYear);
        Logger.log(`createUTCDate_ result: ${result}, toISOString: ${result.toISOString()}`);
        return result;
      } else {
        const result = new Date(normalizedYear, parseInt(month) - 1, parseInt(day));
        Logger.log(`new Date result: ${result}, toISOString: ${result.toISOString()}`);
        return result;
      }
    }

    // Try MM/DD format (no year) - infer year based on current context
    const mmddMatch = cleanStr.match(/^(\d{1,2})[\/-](\d{1,2})$/);
    if (mmddMatch) {
      const [, month, day] = mmddMatch;
      const currentYear = new Date().getFullYear();
      const testDate = new Date(currentYear, parseInt(month) - 1, parseInt(day));
      const now = new Date();
      
      let targetYear = currentYear;
      if (testDate < now) {
        targetYear = currentYear + 1;
      }
      
      Logger.log(`mmddMatch found: month=${month}, day=${day}, targetYear=${targetYear}`);
      if (useUTC) {
        const result = createUTCDate_(parseInt(month), parseInt(day), targetYear);
        Logger.log(`createUTCDate_ (MM/DD) result: ${result}, toISOString: ${result.toISOString()}`);
        return result;
      } else {
        const result = new Date(targetYear, parseInt(month) - 1, parseInt(day));
        Logger.log(`new Date (MM/DD) result: ${result}, toISOString: ${result.toISOString()}`);
        return result;
      }
    }

    // Handle text-based formats: "October 12", "Oct 14th", "October 12th"
    const textMatch = cleanStr.match(/^([a-zA-Z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\s*$/);
    if (textMatch) {
      const [, monthName, day] = textMatch;
      const month = parseMonthName_(monthName);
      if (month) {
        // Use calculateYearIfNotProvided for consistent year logic
        const targetYear = calculateYearIfNotProvided(cleanStr);

        if (useUTC) {
          return createUTCDate_(month, parseInt(day), targetYear);
        } else {
          return new Date(targetYear, month - 1, parseInt(day));
        }
      }
    }

    // Fallback: try JavaScript's Date parsing (less reliable but covers edge cases)
    const fallbackDate = new Date(cleanStr);
    if (!isNaN(fallbackDate.getTime())) {
      if (useUTC) {
        // Convert to UTC 04:00 of the same local date (represents 00:00 ET during DST)
        return new Date(Date.UTC(
          fallbackDate.getFullYear(),
          fallbackDate.getMonth(),
          fallbackDate.getDate(),
          4, 0, 0
        ));
      } else {
        return fallbackDate;
      }
    }
  } catch (error) {
    console.warn('Error parsing date:', error);
  }

  return null;
}

/**
 * Core flexible parsing function that handles various date/datetime formats
 * @param {string} raw - Raw date string
 * @param {Object} opts - Options object
 * @returns {Date|null} Parsed date or null
 */
function parseFlexible_(raw, opts) {
  if (!raw) return null;
  const today = new Date();
  const currentYear = today.getFullYear();

  // Normalize: remove @/at, collapse whitespace/newlines, strip weekdays
  let input = (raw || '').toString()
    .replace(/@|at\s+/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  input = stripWeekdays_(input);

  // Remove periods after month abbreviations and extra commas
  input = input.replace(/\b(january|february|march|april|may|june|july|august|september|october|november|december|sept|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\.?\s*,?\s*/gi, '$1 ');

  // Try various date patterns

  // 1. ISO-ish: YYYY-MM-DD or MM-DD-YYYY
  let m = input.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (m) {
    return new Date(parseInt(m[1]), parseInt(m[2]) - 1, parseInt(m[3]));
  }

  m = input.match(/^(\d{1,2})-(\d{1,2})-(\d{4})$/);
  if (m) {
    return new Date(parseInt(m[3]), parseInt(m[1]) - 1, parseInt(m[2]));
  }

  // 2. Slash formats: MM/DD/YY or MM/DD/YYYY
  m = input.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})(?:\s+(.+))?$/);
  if (m) {
    const month = parseInt(m[1]);
    const day = parseInt(m[2]);
    let year = parseInt(m[3]);
    const timeStr = m[4];

    year = normalizeYear_(year);

    if (timeStr && opts.assumeDateTime) {
      // Parse time component
      const timeMatch = timeStr.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
      if (timeMatch) {
        let hour = parseInt(timeMatch[1]);
        const minute = parseInt(timeMatch[2] || '0');
        const ampm = (timeMatch[3] || '').toLowerCase();

        if (ampm === 'pm' && hour !== 12) hour += 12;
        else if (ampm === 'am' && hour === 12) hour = 0;

        return new Date(year, month - 1, day, hour, minute);
      }
    }

    return new Date(year, month - 1, day);
  }

  // 3. Text month formats: "October 12", "Jan 5, 2025"
  m = input.match(/^([a-zA-Z]+)\s+(\d{1,2})(?:,?\s*(\d{4}))?(?:\s+(.+))?$/);
  if (m) {
    const monthName = m[1];
    const day = parseInt(m[2]);
    let year = m[3] ? parseInt(m[3]) : calculateYearIfNotProvided(input);
    const timeStr = m[4];

    const month = parseMonthName_(monthName);
    if (!month) return null;

    if (timeStr && opts.assumeDateTime) {
      // Parse time component
      const timeMatch = timeStr.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
      if (timeMatch) {
        let hour = parseInt(timeMatch[1]);
        const minute = parseInt(timeMatch[2] || '0');
        const ampm = (timeMatch[3] || '').toLowerCase();

        if (ampm === 'pm' && hour !== 12) hour += 12;
        else if (ampm === 'am' && hour === 12) hour = 0;

        return new Date(year, month - 1, day, hour, minute);
      }
    }

    return new Date(year, month - 1, day);
  }

  return null;
}

/**
 * Strip weekday names from input string
 * @param {string} input - Input string
 * @returns {string} String with weekdays removed
 */
function stripWeekdays_(input) {
  return input.replace(/^(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun),?\s+/i, '');
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
 * Enhanced datetime parser for specific formats like "Sept 16th 7PM", "Weds, Sept. 3rd, 6pm", "8/29/25 @ 7pm"
 * @param {string} input - Input string to parse
 * @returns {Date|null} Parsed Date object in UTC or null if parsing failed
 */
function parseEnhancedDateTime_(input) {
  if (!input || typeof input !== 'string') return null;

  // Clean input: remove weekday names, extra punctuation, normalize spacing
  let cleaned = input.trim()
    .replace(/^(monday|tuesday|wednesday|thursday|friday|saturday|sunday|weds|tues|thurs),?\s*/i, '')
    .replace(/^(mon|tue|wed|thu|fri|sat|sun),?\s*/i, '')
    .replace(/[@,]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  // Extract time part - look for time with AM/PM or isolated hour
  const timeMatch = cleaned.match(/\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|AM|PM)\b/) ||
                   cleaned.match(/(?<![/\d])(\d{1,2})(?::(\d{2}))?(?=\s|$)(?![/\d])/);
  let hour = null;
  let minute = 0;

  if (timeMatch) {
    hour = parseInt(timeMatch[1]);
    minute = parseInt(timeMatch[2] || '0');
    const meridiem = (timeMatch[3] || '').toLowerCase();

    // Convert to 24-hour format (keep as ET time for now)
    if (meridiem === 'pm' && hour !== 12) {
      hour += 12;
    } else if (meridiem === 'am' && hour === 12) {
      hour = 0;
    } else if (!meridiem) {
      // Default assumption: if no AM/PM, assume PM for most events
      if (hour < 12 && hour >= 6) {
        hour += 12; // 6-11 becomes 18-23 (6PM-11PM)
      }
    }

    // Remove time part from cleaned string to extract date
    cleaned = cleaned.replace(timeMatch[0], '').trim();
  }

  // Now extract date components
  let month = null;
  let day = null;
  let year = null;

  // Try MM/DD/YY or MM/DD/YYYY format first
  const slashMatch = cleaned.match(/(\d{1,2})\/(\d{1,2})\/(\d{2,4})/);
  if (slashMatch) {
    month = parseInt(slashMatch[1]);
    day = parseInt(slashMatch[2]);
    year = normalizeYear_(parseInt(slashMatch[3]));
  } else {
    // Try month name formats: "Sept 16th", "September 16", etc.
    const monthNames = {
      'january': 1, 'jan': 1,
      'february': 2, 'feb': 2,
      'march': 3, 'mar': 3,
      'april': 4, 'apr': 4,
      'may': 5,
      'june': 6, 'jun': 6,
      'july': 7, 'jul': 7,
      'august': 8, 'aug': 8,
      'september': 9, 'sept': 9, 'sep': 9,
      'october': 10, 'oct': 10,
      'november': 11, 'nov': 11,
      'december': 12, 'dec': 12
    };

    // Look for month name
    for (const [monthName, monthNum] of Object.entries(monthNames)) {
      const monthRegex = new RegExp(`\\b${monthName}\\b`, 'i');
      if (monthRegex.test(cleaned)) {
        month = monthNum;
        // Remove month name and extract day number
        const afterMonth = cleaned.replace(monthRegex, '').trim();
        const dayMatch = afterMonth.match(/(\d{1,2})(?:st|nd|rd|th)?/);
        if (dayMatch) {
          day = parseInt(dayMatch[1]);
        }
        break;
      }
    }

    // If no year found, use calculateYearIfNotProvided
    if (month && day && !year) {
      year = calculateYearIfNotProvided(cleaned);
    }
  }

  // Validate components
  if (!month || !day || !year || month < 1 || month > 12 || day < 1 || day > 31) {
    return null;
  }

  // If no time was found, return null (this function is for datetime parsing)
  if (hour === null) {
    return null;
  }

  // Create UTC date directly from ET time
  // ET is UTC-4 during daylight saving time (March-November), UTC-5 in winter
  const isDST = month >= 3 && month <= 11;
  const utcOffset = isDST ? 4 : 5; // Hours to add to ET to get UTC

  // Create date in UTC by adding the offset to the ET hour
  const utcHour = hour + utcOffset;
  let finalDay = day;
  let finalMonth = month;
  let finalYear = year;
  let finalHour = utcHour;

  // Handle day overflow
  if (utcHour >= 24) {
    finalHour = utcHour - 24;
    finalDay = day + 1;

    // Handle month overflow (simplified)
    const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if (finalYear % 4 === 0) daysInMonth[1] = 29; // Leap year

    if (finalDay > daysInMonth[month - 1]) {
      finalDay = 1;
      finalMonth = month + 1;
      if (finalMonth > 12) {
        finalMonth = 1;
        finalYear = year + 1;
      }
    }
  }

  // Create UTC date
  const utcDate = new Date(Date.UTC(finalYear, finalMonth - 1, finalDay, finalHour, minute, 0, 0));

  return utcDate;
}

/**
 * Parse month name to month number
 * @param {string} monthName - Month name (full or abbreviated)
 * @returns {number|null} Month number (1-12) or null if invalid
 */
function parseMonthName_(monthName) {
  const months = {
    'january': 1, 'jan': 1,
    'february': 2, 'feb': 2,
    'march': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'may': 5,
    'june': 6, 'jun': 6,
    'july': 7, 'jul': 7,
    'august': 8, 'aug': 8,
    'september': 9, 'sept': 9, 'sep': 9,
    'october': 10, 'oct': 10,
    'november': 11, 'nov': 11,
    'december': 12, 'dec': 12
  };

  const normalized = monthName.toLowerCase().trim();
  return months[normalized] || null;
}

/**
 * Create UTC date at 4:00 AM (for EST to UTC conversion)
 * @param {number} month - Month (1-12)
 * @param {number} day - Day of month
 * @param {number} year - Full year
 * @returns {Date} UTC Date object
 */
function createUTCDate_(month, day, year) {
  // Create date at 4:00 AM UTC on the same calendar day
  // During DST this represents 00:00 ET for that date; in winter it's 23:00 previous day ET
  return new Date(Date.UTC(year, month - 1, day, 4, 0, 0));
}
