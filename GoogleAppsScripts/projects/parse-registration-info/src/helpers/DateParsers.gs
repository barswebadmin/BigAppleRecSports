/**
 * DateParsers class for comprehensive date parsing functionality
 * Handles flexible date and datetime formats with various input types
 *
 * @fileoverview Central date parsing utilities with class-based organization
 * @requires textUtils.gs
 */

// Import references for editor support
/// <reference path="textUtils.gs" />

/**
 * DateParsers class - centralized date parsing functionality
 * Consolidates all date parsing logic from dateParser.gs and parseSeasonDates.gs
 */
class DateParsers {

  /**
   * Parse flexible date format (date only, no time)
   * @param {string} s - Date string to parse
   * @param {Array<string>} unresolved - Array to track unresolved fields
   * @param {string} fieldName - Name of field being parsed (for unresolved tracking)
   * @returns {Date|string} Parsed Date object or empty string if invalid
   */
  static parseDateFlexibleDateOnly_(s, unresolved, fieldName) {
    // Accepts "10-19-2025", "9/25/25", "October 12" (assume year = current; if passed already, next year)
    const d = DateParsers.parseFlexible_(s, { assumeDateOnly: true });
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
  static parseDateFlexibleDateTime_(s, fallbackTimeDateOnly, unresolved, fieldName) {
    // Accepts "8/31/25 @ 7pm", "6/6/2025 18:00", etc.
    if (!s || !s.trim()) return '';
    const d = DateParsers.parseFlexible_(s, { assumeDateTime: true });
    if (!d) {
      // If it's only a date, use sport start time as the time-of-day
      const maybeDate = DateParsers.parseFlexible_(s, { assumeDateOnly: true });
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
  static parseFlexibleDate_(dateStr, useUTC = false) {
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
        const normalizedYear = DateParsers.normalizeYear_(parseInt(year));
        if (useUTC) {
          return DateParsers.createUTCDate_(parseInt(month), parseInt(day), normalizedYear);
        } else {
          return new Date(normalizedYear, parseInt(month) - 1, parseInt(day));
        }
      }

      // Handle text-based formats: "October 12", "Oct 14th", "October 12th"
      const textMatch = cleanStr.match(/^([a-zA-Z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\s*$/);
      if (textMatch) {
        const [, monthName, day] = textMatch;
        const month = DateParsers.parseMonthName_(monthName);
        if (month) {
          // Use current year as default for text-based dates
          const currentYear = new Date().getFullYear();
          if (useUTC) {
            return DateParsers.createUTCDate_(month, parseInt(day), currentYear);
          } else {
            return new Date(currentYear, month - 1, parseInt(day));
          }
        }
      }

      // Fallback: try JavaScript's Date parsing (less reliable but covers edge cases)
      const fallbackDate = new Date(cleanStr);
      if (!isNaN(fallbackDate.getTime())) {
        if (useUTC) {
          // Convert to UTC midnight on the next day (EST -> UTC conversion)
          return new Date(Date.UTC(
            fallbackDate.getFullYear(),
            fallbackDate.getMonth(),
            fallbackDate.getDate() + 1,
            4, 0, 0  // 4:00 AM UTC on next day for EST conversion
          ));
        } else {
          return fallbackDate;
        }
      }

    } catch (error) {
      console.warn('Error parsing date:', cleanStr, error);
    }

    return null;
  }

  /**
   * Strip weekday names from date strings
   * @param {string} s - Input string
   * @returns {string} String with weekdays removed
   */
  static stripWeekdays_(s) {
    return s.replace(/\b(mon|monday|tues|tuesday|wed|weds|wednesday|thu|thurs|thursday|fri|friday|sat|saturday|sun|sunday)\b\.?,?/gi, ' ');
  }

  /**
   * Flexible date parser that handles multiple formats (legacy implementation)
   * @param {string} raw - Raw date string
   * @param {Object} opts - Parsing options
   * @returns {Date|null} Parsed date or null
   */
  static parseFlexible_(raw, opts) {
    if (!raw) return null;
    const today = new Date();
    const currentYear = today.getFullYear();

    // Normalize: remove @/at, collapse whitespace/newlines, strip weekdays
    let input = (raw || '').toString()
      .replace(/@|at\s+/gi, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    input = DateParsers.stripWeekdays_(input);

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
      let year = parseInt(m[3]);
      if (year < 100) year += 2000; // Convert 2-digit year

      const date = new Date(year, parseInt(m[1]) - 1, parseInt(m[2]));

      // If there's time component, parse it
      if (m[4] && opts?.assumeDateTime) {
        const timeStr = m[4];
        const timeMatch = timeStr.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
        if (timeMatch) {
          let hour = parseInt(timeMatch[1]);
          const minute = parseInt(timeMatch[2] || '0');
          const isPM = timeMatch[3] && timeMatch[3].toLowerCase() === 'pm';

          // Handle 12-hour format
          if (isPM && hour !== 12) hour += 12;
          if (!isPM && hour === 12) hour = 0;

          date.setHours(hour, minute);
        }
      }

      return date;
    }

    // 3. Month name formats: "January 15", "Jan 15 2025", etc.
    m = input.match(/^(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+(\d{1,2})(?:\s*,?\s*(\d{4}))?(?:\s+(.+))?$/i);
    if (m) {
      const monthName = m[1].toLowerCase();
      const day = parseInt(m[2]);
      const year = m[3] ? parseInt(m[3]) : currentYear;

      const monthNum = DateParsers.parseMonthName_(monthName);
      if (monthNum) {
        const date = new Date(year, monthNum - 1, day);

        // Handle time component if present
        if (m[4] && opts?.assumeDateTime) {
          const timeStr = m[4];
          const timeMatch = timeStr.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
          if (timeMatch) {
            let hour = parseInt(timeMatch[1]);
            const minute = parseInt(timeMatch[2] || '0');
            const isPM = timeMatch[3] && timeMatch[3].toLowerCase() === 'pm';

            if (isPM && hour !== 12) hour += 12;
            if (!isPM && hour === 12) hour = 0;

            date.setHours(hour, minute);
          }
        }

        return date;
      }
    }

    // 4. Try browser's Date constructor as fallback
    try {
      const fallback = new Date(input);
      if (!isNaN(fallback.getTime())) {
        return fallback;
      }
    } catch (e) {
      // Ignore fallback errors
    }

    return null;
  }

  /**
   * Create a UTC Date object for the given month/day/year
   * @param {number} month - Month (1-12)
   * @param {number} day - Day (1-31)
   * @param {number} year - Full year (e.g., 2025)
   * @returns {Date} UTC Date object at 4:00 AM UTC (next day for EST conversion)
   */
  static createUTCDate_(month, day, year) {
    // Create date at 4:00 AM UTC on the next day
    // This converts local EST date to UTC: Oct 12 EST -> Oct 13 4:00 AM UTC
    return new Date(Date.UTC(year, month - 1, day + 1, 4, 0, 0));
  }

  /**
   * Normalize 2-digit year to 4-digit year
   * @param {number} year - 2 or 4 digit year
   * @returns {number} 4-digit year
   */
  static normalizeYear_(year) {
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
  static parseMonthName_(monthName) {
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
}

// Legacy function wrappers for backwards compatibility
function parseDateFlexibleDateOnly_(s, unresolved, fieldName) {
  return DateParsers.parseDateFlexibleDateOnly_(s, unresolved, fieldName);
}

function parseDateFlexibleDateTime_(s, fallbackTimeDateOnly, unresolved, fieldName) {
  return DateParsers.parseDateFlexibleDateTime_(s, fallbackTimeDateOnly, unresolved, fieldName);
}

function stripWeekdays_(s) {
  return DateParsers.stripWeekdays_(s);
}

function parseFlexible_(raw, opts) {
  return DateParsers.parseFlexible_(raw, opts);
}
