/**
 * Date parsing functions for parse-registration-info
 * Handle flexible date and datetime formats
 * 
 * @fileoverview Flexible date and datetime parsing
 * @requires ../helpers/textUtils.gs
 */

// Import references for editor support
/// <reference path="../helpers/textUtils.gs" />

/**
 * Parse flexible date format (date only, no time)
 */
function parseDateFlexibleDateOnly_(s, unresolved) {
  // Accepts "10-19-2025", "9/25/25", "October 12" (assume year = current; if passed already, next year)
  const d = parseFlexible_(s, { assumeDateOnly: true });
  if (!d) {
    if (s && s.trim()) unresolved.push(`Unrecognized date: "${s}"`);
    return '';
  }
  // Zero out time
  d.setHours(0,0,0,0);
  return d;
}

/**
 * Parse flexible datetime format
 */
function parseDateFlexibleDateTime_(s, fallbackTimeDateOnly, unresolved) {
  // Accepts "8/31/25 @ 7pm", "6/6/2025 18:00", etc.
  if (!s || !s.trim()) return '';
  const d = parseFlexible_(s, { assumeDateTime: true });
  if (!d) {
    // If it's only a date, use sport start time as the time-of-day
    const maybeDate = parseFlexible_(s, { assumeDateOnly: true });
    if (maybeDate && fallbackTimeDateOnly instanceof Date) {
      maybeDate.setHours(fallbackTimeDateOnly.getHours(), fallbackTimeDateOnly.getMinutes(), 0, 0);
      return maybeDate;
    }
    unresolved.push(`Unrecognized date/time: "${s}"`);
    return '';
  }
  return d;
}

/**
 * Strip weekday tokens from date strings
 */
function stripWeekdays_(s) {
  return s.replace(/\b(mon|monday|tues|tuesday|wed|weds|wednesday|thu|thurs|thursday|fri|friday|sat|saturday|sun|sunday)\b\.?,?/gi, ' ');
}

/**
 * Flexible date parser that handles multiple formats
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
        const meridiem = (timeMatch[3] || '').toLowerCase();
        
        if (meridiem === 'pm' && hour !== 12) hour += 12;
        if (meridiem === 'am' && hour === 12) hour = 0;
        
        date.setHours(hour, minute, 0, 0);
      }
    }
    
    return date;
  }

  // 3. Month name formats: "October 12", "Oct 12, 2025"
  const monthNames = {
    jan: 0, january: 0, feb: 1, february: 1, mar: 2, march: 2,
    apr: 3, april: 3, may: 4, jun: 5, june: 5, jul: 6, july: 6,
    aug: 7, august: 7, sep: 8, september: 8, oct: 9, october: 9,
    nov: 10, november: 10, dec: 11, december: 11
  };
  
  m = input.match(/^(\w+)\s+(\d{1,2})(?:,?\s*(\d{4}))?/i);
  if (m) {
    const monthName = m[1].toLowerCase();
    const day = parseInt(m[2]);
    const year = m[3] ? parseInt(m[3]) : currentYear;
    
    if (monthNames.hasOwnProperty(monthName)) {
      const month = monthNames[monthName];
      const date = new Date(year, month, day);
      
      // If date is in the past and no year specified, assume next year
      if (!m[3] && date < today) {
        date.setFullYear(currentYear + 1);
      }
      
      return date;
    }
  }

  // 4. Try native Date parsing as fallback
  const nativeDate = new Date(input);
  if (!isNaN(nativeDate.getTime())) {
    return nativeDate;
  }

  return null;
}
