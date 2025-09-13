/**
 * Core row parsing functions for parse-registration-info
 * Main logic for converting spreadsheet rows to structured data
 *
 * @fileoverview Main row parsing orchestrator
 * @requires ../config/constants.gs
 * @requires ../helpers/normalizers.gs
 * @requires ../helpers/textUtils.gs
 * @requires flagsParser.gs
 * @requires timeParser.gs
 * @requires dateParser.gs
 * @requires priceParser.gs
 * @requires notesParser.gs
 */

// Import references for editor support
/// <reference path="../config/constants.gs" />
/// <reference path="../helpers/normalizers.gs" />
/// <reference path="../helpers/textUtils.gs" />
/// <reference path="flagsParser.gs" />
/// <reference path="timeParser.gs" />
/// <reference path="dateParser.gs" />
/// <reference path="priceParser.gs" />
/// <reference path="notesParser.gs" />

/**
 * Parse a complete source row into structured data
 * @param {Object} v - Raw values object with columns A-O
 * @param {string} v.A - Sport name
 * @param {string} v.B - Day and flags
 * @param {string} v.C - Notes and details
 * @param {string} v.D - Season start date
 * @param {string} v.E - Season end date
 * @param {string} v.F - Price
 * @param {string} v.G - Times
 * @param {string} v.H - Location
 * @param {string} v.M - Veteran registration
 * @param {string} v.N - Early registration
 * @param {string} v.O - Open registration
 * @param {Array<string>} unresolved - Array to collect parsing issues
 * @returns {Object} Parsed and structured data object
 */
function parseSourceRowEnhanced_(v, unresolved) {
  // SPORT (A)
  const sport = normalizeSport_(toTitleCase_(v.A.trim()), unresolved);

  // B-lines (day, flags)
  const bLines = splitLines_(v.B);
  const day = normalizeDay_(bLines[0] || '');
  const { division, sportSubCategory, socialOrAdvanced, types } =
    parseBFlags_(bLines, unresolved, v.C || '');

  // Time range (G)
  const timeInfo = parseTimeRangeBothSessions_(v.G);
  const sportStartTime = timeInfo.primaryStartDateOnly;   // Date object with only time-of-day
  const sportEndTime   = timeInfo.primaryEndDateOnly;
  const alternativeStartTime = timeInfo.altStartDateOnly;
  const alternativeEndTime   = timeInfo.altEndDateOnly;

  // Dates (D/E)
  const seasonStartDate = parseDateFlexibleDateOnly_(v.D, unresolved); // Date object (00:00:00)
  const seasonEndDate   = parseDateFlexibleDateOnly_(v.E, unresolved);

  const { season, year } = deriveSeasonYearFromDate_(seasonStartDate);

  // Price (F) numeric
  const price = parsePriceNumber_(v.F, unresolved);

  // Location (H) canonicalized
  const location = canonicalizeLocation_(v.H, unresolved);

  // Registration windows (M/N/O) -> Date objects with seconds
  const earlyRegistrationStartDateTime = parseDateFlexibleDateTime_(v.M, sportStartTime, unresolved);
  const vetRegistrationStartDateTime   = parseDateFlexibleDateTime_(v.N, sportStartTime, unresolved);
  const openRegistrationStartDateTime  = parseDateFlexibleDateTime_(v.O, sportStartTime, unresolved);

  const notes = parseNotes_(v.C, sportStartTime, unresolved);
  const {
    orientationDate,
    scoutNightDate,
    openingPartyDate,
    rainDate,
    closingPartyDate,
    offDatesFromNotes,
    altTimesFromNotes
  } = notes;

  // Merge alternative times: notes can override if present
  const altStartFromNotes = altTimesFromNotes?.start || null;
  const altEndFromNotes   = altTimesFromNotes?.end || null;
  const altStartFinal = altStartFromNotes || alternativeStartTime || '';
  const altEndFinal   = altEndFromNotes   || alternativeEndTime   || '';

  const offDatesFromText = extractOffDatesFromFreeText_(v.C, unresolved);
  const offDatesCombined = dedupeCsv_([...offDatesFromNotes, ...offDatesFromText]);

  // Total inventory from details (# of Players: N)
  const totalInventory = extractPlayersFromDetails_(v.C);

  return {
    sport,
    day,
    sportSubCategory,
    division,
    season,
    year,
    socialOrAdvanced,
    types: dedupeCsv_([...types, ...(notes.typesFromNotes || [])]).join(', '),
    newPlayerOrientationDateTime: orientationDate || '',
    scoutNightDateTime: scoutNightDate || '',
    openingPartyDate: openingPartyDate || '',
    rainDate: rainDate || '',
    closingPartyDate: closingPartyDate || '',
    seasonStartDate,
    seasonEndDate,
    alternativeStartTime: altStartFinal,
    alternativeEndTime: altEndFinal,
    offDatesCommaSeparated: offDatesCombined.join(', '),
    sportStartTime,
    sportEndTime,
    location,
    price,
    vetRegistrationStartDateTime,
    earlyRegistrationStartDateTime,
    openRegistrationStartDateTime,
    totalInventory,
  };
}

/**
 * Deduplicate CSV values
 */
function dedupeCsv_(arr) {
  const seen = new Set();
  return arr.filter(item => {
    const key = (item || '').toString().trim().toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/**
 * Extract off dates from free text
 */
function extractOffDatesFromFreeText_(text, unresolved) {
  const offDates = [];
  const content = (text || '').toLowerCase();

  // Look for patterns like "no games 12/25, 1/1" or "off dates: 12/24, 12/31"
  const patterns = [
    /(?:no\s+games?|off\s+dates?|cancelled?)[\s:]*([0-9\/,\s-]+)/gi,
    /(?:skip|except)[\s:]*([0-9\/,\s-]+)/gi
  ];

  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(content)) !== null) {
      const dateStr = match[1];
      const dates = dateStr.split(/[,\s]+/).filter(Boolean);

      for (const date of dates) {
        if (/^\d{1,2}\/\d{1,2}(?:\/\d{2,4})?$/.test(date)) {
          offDates.push(date);
        }
      }
    }
  }

  return offDates;
}
