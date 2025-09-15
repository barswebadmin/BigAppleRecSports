/**
 * Data normalization functions for parse-registration-info
 * Canonicalize sports, locations, and other text data
 *
 * @fileoverview Data normalization and canonicalization
 * @requires ../config/constants.gs
 * @requires textUtils.gs
 */

// Import references for editor support
/// <reference path="../config/constants.gs" />
/// <reference path="textUtils.gs" />


/**
 * Initialize unresolved tracking with all fields, then remove sport-specific irrelevant fields
 * @param {string} sportName - The identified sport name (e.g., "Pickleball")
 * @returns {Array<string>} List of fields to track for this specific sport
 */

// biome-ignore lint/correctness/noUnusedVariables: <this is called in the flow from menu item click>
function initializeUnresolvedFields(sportName) {
  // Start with all comprehensive fields except sportName (since we already know it)
  const unresolved = comprehensiveProductCreateFields.filter(field => field !== 'sportName');

  // Remove sport-specific irrelevant fields
  if (sportName && irrelevantFieldsForSport[sportName]) {
    const irrelevantFields = irrelevantFieldsForSport[sportName];
    for (const field of irrelevantFields) {
      const fieldIndex = unresolved.indexOf(field);
      if (fieldIndex > -1) unresolved.splice(fieldIndex, 1);
    }
  }

  return unresolved;
}

/**
 * Normalize sport name to canonical form
 */

// biome-ignore lint/correctness/noUnusedVariables: <this is called in the flow from menu item click>
function normalizeSport_(s) {
  const IN = (s || '').trim();
  if (!IN) return '';

  const validSports = productFieldEnums.sportName || [];

  for (const cand of validSports) {
    if (cand.toLowerCase() === IN.toLowerCase()) {
      return cand; // Return the properly capitalized version from enum
    }
  }

  // Sport not found
  return '';
}

/**
 * Normalize day of week
 */

// biome-ignore lint/correctness/noUnusedVariables: <this is called in the flow from menu item click>
function  normalizeDay_(dayRaw) {
  const day = (dayRaw || '').trim();
  if (!day) return '';

  const dayMap = {
    'mon': 'Monday', 'monday': 'Monday',
    'tue': 'Tuesday', 'tues': 'Tuesday', 'tuesday': 'Tuesday',
    'wed': 'Wednesday', 'wednesday': 'Wednesday',
    'thu': 'Thursday', 'thur': 'Thursday', 'thurs': 'Thursday', 'thursday': 'Thursday',
    'fri': 'Friday', 'friday': 'Friday',
    'sat': 'Saturday', 'saturday': 'Saturday',
    'sun': 'Sunday', 'sunday': 'Sunday'
  };

  const normalized = dayMap[day.toLowerCase()];
  return normalized || capitalize(day, true);
}

/**
 * Derive season and year from a date
 */

// biome-ignore lint/correctness/noUnusedVariables: <this is called in the flow from menu item click>
function  deriveSeasonYearFromDate_(d) {
  if (!(d instanceof Date) || Number.isNaN(d)) return { season: '', year: '' };
  const month = d.getMonth()+1;
  const year = d.getFullYear();
  let season = '';
  if ([3,4,5].includes(month)) season = 'Spring';
  else if ([6,7,8].includes(month)) season = 'Summer';
  else if ([9,10,11].includes(month)) season = 'Fall';
  else season = 'Winter';
  return { season, year: String(year) };
}
