/**
 * League time parsing functions for parse-registration-info
 * Extract and format league start/end times and alternative times
 *
 * @fileoverview Time parsing and formatting for league schedules
 */

/**
 * Parse league times from text, handling single and double time ranges
 * @param {string} s - Time input string (e.g., "4-7:30PM", "Times: 12:45-2:45PM & 3:00-5:00PM")
 * @returns {{leagueStartTime: string|null, leagueEndTime: string|null, alternativeStartTime: string|null, alternativeEndTime: string|null}} Parsed times
 */
function parseColGLeagueTimes_(s) {

  // Initialize all return values as null
  let leagueStartTime = null;
  let leagueEndTime = null;
  let alternativeStartTime = null;
  let alternativeEndTime = null;

  // Handle null, undefined, or empty string
  if (!s || typeof s !== 'string' || !s.trim()) {
    return { leagueStartTime, leagueEndTime, alternativeStartTime, alternativeEndTime };
  }

  const inputStr = s.trim();

  try {
    // Remove common prefixes like "Time:", "Times:", etc.
    const cleanedInput = inputStr.replace(/^(time|times):\s*/i, '');

    // Check for double time ranges first (contains & or "and")
    const doubleTimeMatch = cleanedInput.match(/(.+?)\s*[&]\s*(.+)/i);
    if (doubleTimeMatch) {
      const firstRange = doubleTimeMatch[1].trim();
      const secondRange = doubleTimeMatch[2].trim();

      const firstTimes = parseTimeRange_(firstRange);
      const secondTimes = parseTimeRange_(secondRange);

      if (firstTimes && secondTimes) {
        leagueStartTime = firstTimes.start;
        leagueEndTime = firstTimes.end;
        alternativeStartTime = secondTimes.start;
        alternativeEndTime = secondTimes.end;

      }
    } else {
      // Try to parse as single time range
      const singleTimes = parseTimeRange_(cleanedInput);
      if (singleTimes) {
        leagueStartTime = singleTimes.start;
        leagueEndTime = singleTimes.end;

      }
    }
  } catch (error) {
    console.warn('Error parsing league times:', inputStr, error);
  }

  return { leagueStartTime, leagueEndTime, alternativeStartTime, alternativeEndTime,  };
}

/**
 * Parse a single time range string into start and end times
 * @param {string} timeRange - Time range string (e.g., "4-7:30PM", "6:30-10")
 * @returns {{start: string, end: string}|null} Parsed start and end times or null if invalid
 */
function parseTimeRange_(timeRange) {
  if (!timeRange || typeof timeRange !== 'string') {
    return null;
  }

  // Clean the input - remove common prefixes and normalize
  let cleanRange = timeRange.trim()
    .replace(/^(time|times):\s*/i, '')  // Remove "Time:" or "Times:"
    .replace(/\b(time|times)\b\s*/gi, '') // Remove standalone "time" or "times"
    .trim();

  // Split on hyphen, "to", or "until" (case insensitive)
  const splitPattern = /\s*[-–]\s*|\s+(?:to|until)\s+/i;
  const parts = cleanRange.split(splitPattern);

  if (parts.length !== 2) {
    return null;
  }

  let rawStartTime = parts[0].trim();
  let rawEndTime = parts[1].trim();

  // Parse start and end times
  const startTime = parseSimpleTime_(rawStartTime);
  const endTime = parseSimpleTime_(rawEndTime);

  if (!startTime || !endTime) {
    return null;
  }

  // Apply meridiem logic
  // Check if rawStartTime starts with 9, 10, or 11 - if so, that's AM, otherwise PM
  if (startTime.hour === 9 || startTime.hour === 10 || startTime.hour === 11) {
    startTime.meridiem = 'AM';
  } else {
    startTime.meridiem = 'PM';
  }

  // End time is always PM
  endTime.meridiem = 'PM';

  return {
    start: formatTime_(startTime),
    end: formatTime_(endTime)
  };
}

/**
 * Parse a simple time string (just digits and optional colon)
 * @param {string} timeStr - Time string (e.g., "4", "7:30", "12")
 * @returns {{hour: number, minute: number}|null} Parsed time components or null if invalid
 */
function parseSimpleTime_(timeStr) {
  if (!timeStr) return null;

  // Strip out any AM/PM markers or letters (a, p, am, pm)
  const cleanTimeStr = timeStr.replace(/[ap]m?/gi, '').trim();

  // Match time patterns: 1-2 digits, optionally followed by colon and 2 digits
  const timeMatch = cleanTimeStr.match(/^(\d{1,2})(?::(\d{2}))?$/);
  if (!timeMatch) return null;

  const hour = parseInt(timeMatch[1]);
  const minute = parseInt(timeMatch[2] || '0');

  if (hour < 1 || hour > 12 || minute < 0 || minute > 59) {
    return null;
  }

  return { hour, minute };
}

/**
 * Format time components into a readable string
 * @param {{hour: number, minute: number, meridiem: string}} timeObj - Time components
 * @returns {string} Formatted time string (e.g., "4:00 PM", "7:30 AM")
 */
function formatTime_(timeObj) {
  if (!timeObj) return null;

  const { hour, minute, meridiem } = timeObj;
  const minuteStr = minute === 0 ? '00' : minute.toString().padStart(2, '0');

  return `${hour}:${minuteStr} ${meridiem}`;
}
