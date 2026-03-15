/**
 * League time parsing functions for parse-registration-info
 * Extract and format league start/end times from a single time range
 *
 * @fileoverview Time parsing and formatting for league schedules
 */

/**
 * Parse league times from a single time range string
 * Format: "h:mm-h:mm AM/PM" or "h:mm AM/PM-h:mm PM"
 * If first time has no AM/PM marker, assumes PM
 * Strips whitespace from each element
 * 
 * @param {string} leagueTimesInput - Time input string (e.g., "6:30-8:30 PM", "1:00-3:00 PM")
 * @returns {{leagueStartTime: string|null, leagueEndTime: string|null, alternativeStartTime: string|null, alternativeEndTime: string|null}} Parsed times
 */
export function parseLeagueTimes(leagueTimesInput) {
  // Initialize all return values as null
  let leagueStartTime = null;
  let leagueEndTime = null;
  let alternativeStartTime = null;
  let alternativeEndTime = null;

  // Handle null, undefined, or empty string
  if (!leagueTimesInput || typeof leagueTimesInput !== 'string' || !leagueTimesInput.trim()) {
    return { leagueStartTime, leagueEndTime, alternativeStartTime, alternativeEndTime };
  }

  const inputStr = leagueTimesInput.trim();

  try {
    // Split on hyphen
    const parts = inputStr.split('-').map(p => p.trim());
    
    if (parts.length !== 2) {
      console.warn('Invalid time format - expected single hyphen:', inputStr);
      return { leagueStartTime, leagueEndTime, alternativeStartTime, alternativeEndTime };
    }

    const firstPart = parts[0];
    const secondPart = parts[1];

    // Parse second part first (it should have AM/PM marker)
    const endTimeResult = parseTimeWithMeridiem(secondPart);
    if (!endTimeResult) {
      console.warn('Could not parse end time:', secondPart);
      return { leagueStartTime, leagueEndTime, alternativeStartTime, alternativeEndTime };
    }

    leagueEndTime = endTimeResult.formatted;

    // Parse first part
    const startTimeResult = parseTimeWithMeridiem(firstPart);
    if (!startTimeResult) {
      console.warn('Could not parse start time:', firstPart);
      return { leagueStartTime, leagueEndTime, alternativeStartTime, alternativeEndTime };
    }

    // If first part has no meridiem, assume PM
    if (!startTimeResult.hasMeridiem) {
      const timeParts = firstPart.match(/(\d{1,2}):(\d{2})/);
      if (timeParts) {
        const hour = timeParts[1];
        const minute = timeParts[2];
        leagueStartTime = `${hour}:${minute} PM`;
      }
    } else {
      leagueStartTime = startTimeResult.formatted;
    }

  } catch (error) {
    console.warn('Error parsing league times:', inputStr, error);
  }

  return { leagueStartTime, leagueEndTime, alternativeStartTime, alternativeEndTime };
}

/**
 * Parse a time string and extract time with meridiem
 * @param {string} timeStr - Time string (e.g., "6:30 PM", "1:00", "8:30PM")
 * @returns {{formatted: string, hasMeridiem: boolean}|null} Parsed time with meridiem info or null
 */
export function parseTimeWithMeridiem(timeStr) {
  if (!timeStr || typeof timeStr !== 'string') {
    return null;
  }

  const cleaned = timeStr.trim();

  // Match time pattern: h:mm with optional AM/PM (case insensitive, with or without space)
  const timeMatch = cleaned.match(/(\d{1,2}):(\d{2})\s*(am|pm)?/i);
  
  if (!timeMatch) {
    return null;
  }

  const hour = timeMatch[1];
  const minute = timeMatch[2];
  const meridiem = timeMatch[3];

  if (meridiem) {
    // Has AM/PM marker
    const meridiemUpper = meridiem.toUpperCase();
    return {
      formatted: `${hour}:${minute} ${meridiemUpper}`,
      hasMeridiem: true
    };
  } else {
    // No AM/PM marker
    return {
      formatted: `${hour}:${minute}`,
      hasMeridiem: false
    };
  }
}
