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
 * Canonicalize location to allowed list
 */

// biome-ignore lint/correctness/noUnusedVariables: <this is called in the flow from menu item click>
function  canonicalizeLocation_(s, sportName, unresolved) {
  const inStr = (s || '').trim();
  if (!inStr) {
    // Location missing - leave "location" in unresolved array
    return '';
  }
  const lc = inStr.toLowerCase();

  // Get sport-specific locations from productFieldEnums
  const validLocations = productFieldEnums.location?.[sportName]
    ? productFieldEnums.location[sportName]
    : [];

  if (validLocations.length === 0) {
    // No valid locations for this sport - return as-is
    return inStr;
  }

  // Try direct contains/shortcut rules for sport-specific locations
  let best = '';
  for (const cand of validLocations) {
    // Check John Jay first (before general includes check to avoid similarity warning)
    if (/john jay/i.test(lc) && cand.startsWith('John Jay College')) {
      best = cand;
      break;
    }

    if (lc.includes(cand.toLowerCase().split(' (')[0])) { best = cand; break; }
    if (/dewitt/i.test(lc) && cand.startsWith('Dewitt Clinton Park')) best = cand;
    if (/gansevoort/i.test(lc) && cand.startsWith('Gansevoort Peninsula')) best = cand;
    if (/elliott/i.test(lc) && cand.startsWith('Elliott Center')) best = cand;
    if (/ps3|charrette/i.test(lc) && cand.startsWith('PS3')) best = cand;
    if ( (/\bv(?:\.?\s*)c(?:\.?\s*)s\b/i.test(lc) || /village community/i.test(lc))
        && cand.startsWith('Village Community') ) {
      best = cand;
    }
    if (/hartley/i.test(lc) && cand.startsWith('Hartley House')) best = cand;
    if (/chelsea park/i.test(lc) && cand.startsWith('Chelsea Park')) best = cand;
    if (/gotham pickle/i.test(lc) && cand.startsWith('Gotham Pickleball')) best = cand;
    if (/pickle1/i.test(lc) && cand.endsWith('1')) best = cand;
    if (/frames/i.test(lc) && cand.startsWith('Frames Bowling')) best = cand;
    if (/bowlero/i.test(lc) && cand.startsWith('Bowlero')) best = cand;
  }

  if (best) {
    // Successfully found location - remove from unresolved
    const index = unresolved.indexOf("location");
    if (index > -1) unresolved.splice(index, 1);
    return best;
  }

  // Fallback: pick the most similar location from sport-specific list
  let bestCand = '', bestScore = 0;
  for (const cand of validLocations) {
    const sc = _simpleSimilarity(inStr, cand);
    if (sc > bestScore) { bestScore = sc; bestCand = cand; }
  }

  if (bestScore >= 0.6) {
    // Successfully found similar location - remove from unresolved
    const index = unresolved.indexOf("location");
    if (index > -1) unresolved.splice(index, 1);
    return bestCand;
  }

  // Location not recognized - leave "location" in unresolved array
  return '';
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
