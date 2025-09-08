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

// === OPTIONAL: fuzzy map sport names ===
const CANONICAL_SPORTS = ['Bowling','Kickball','Dodgeball','Pickleball'];

/**
 * Normalize sport name to canonical form
 */
function normalizeSport_(s, unresolved) {
  const IN = (s || '').trim();
  if (!IN) return '';
  
  // Exact case-insensitive hit?
  for (const cand of CANONICAL_SPORTS) {
    if (cand.toLowerCase() === IN.toLowerCase()) return cand;
  }
  
  // Fuzzy matching
  let best = '', bestScore = 0;
  for (const cand of CANONICAL_SPORTS) {
    const sc = _simpleSimilarity(IN, cand);
    if (sc > bestScore) { bestScore = sc; best = cand; }
  }
  
  if (bestScore >= 0.7) {
    unresolved.push(`Sport might be "${best}" (from "${IN}", similarity ${bestScore.toFixed(2)}) → populated in target`);
    return best;
  }
  
  unresolved.push(`Sport unrecognized: "${IN}" → omitted (left blank)`);
  return '';
}

/**
 * Normalize day of week
 */
function normalizeDay_(dayRaw) {
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
  return normalized || toTitleCase_(day);
}

/**
 * Canonicalize location to allowed list
 */
function canonicalizeLocation_(s, unresolved) {
  const inStr = (s || '').trim();
  if (!inStr) {
    unresolved.push('Location missing → omitted (left blank)');
    return '';
  }
  const lc = inStr.toLowerCase();

  // Try direct contains/shortcut rules
  let best = '';
  for (const cand of CANONICAL_LOCATIONS) {
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
    if (/john jay/i.test(lc) && cand.startsWith('John Jay College')) {
      best = cand;
      // For John Jay, we know this is a good match, so mark high confidence
      if (lc.includes('john jay')) {
        return cand; // Return immediately with high confidence, no warning needed
      }
    }
    if (/pickle1/i.test(lc) && cand.endsWith('1')) best = cand;
    if (/frames/i.test(lc) && cand.startsWith('Frames Bowling')) best = cand;
    if (/bowlero/i.test(lc) && cand.startsWith('Bowlero')) best = cand;
  }
  
  if (best) {
    const sim = _simpleSimilarity(inStr, best);
    if (sim < 0.9) {
      unresolved.push(
        `Location might be "${best}" (from "${inStr}", similarity ${sim.toFixed(2)}) → populated in target`
      );
    }
    return best;
  }

  // Fallback: pick the most similar canonical entry and flag it
  let bestCand = '', bestScore = 0;
  for (const cand of CANONICAL_LOCATIONS) {
    const sc = _simpleSimilarity(inStr, cand);
    if (sc > bestScore) { bestScore = sc; bestCand = cand; }
  }
  
  if (bestScore >= 0.6) {
    unresolved.push(
      `Location might be "${bestCand}" (from "${inStr}", similarity ${bestScore.toFixed(2)}) → populated in target`
    );
    return bestCand;
  }

  unresolved.push(`Location not in allowed list: "${inStr}" → omitted (left blank)`);
  return '';
}

/**
 * Derive season and year from a date
 */
function deriveSeasonYearFromDate_(d) {
  if (!(d instanceof Date) || isNaN(d)) return { season: '', year: '' };
  const month = d.getMonth()+1;
  const year = d.getFullYear();
  let season = '';
  if ([3,4,5].includes(month)) season = 'Spring';
  else if ([6,7,8].includes(month)) season = 'Summer';
  else if ([9,10,11].includes(month)) season = 'Fall';
  else season = 'Winter';
  return { season, year: String(year) };
}
