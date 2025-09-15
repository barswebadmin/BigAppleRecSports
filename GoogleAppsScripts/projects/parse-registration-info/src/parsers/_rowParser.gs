/**
 * Core row parsing functions for parse-registration-info
 * Main logic for converting spreadsheet rows to structured data
 *
 * @fileoverview Main row parsing orchestrator
 * @requires ../config/constants.gs
 * @requires ../helpers/normalizers.gs
 * @requires ../helpers/textUtils.gs
 * @requires parseColBLeagueDetails.gs
 * @requires parseRowC.gs
 * @requires parseSeasonDates.gs
 * @requires timeParser.gs
 * @requires ../helpers/dateParsers.gs
 * @requires parseColFPrice_.gs
 * @requires parseColHLocation_.gs
 * @requires notesParser.gs
 */

// Import references for editor support
/// <reference path="../config/constants.gs" />
/// <reference path="../helpers/normalizers.gs" />
/// <reference path="../helpers/textUtils.gs" />
/// <reference path="parseColBLeagueDetails.gs" />
/// <reference path="parseRowC.gs" />
/// <reference path="parseSeasonDates.gs" />
/// <reference path="timeParser.gs" />
/// <reference path="../helpers/dateParsers.gs" />
/// <reference path="parseColFPrice_.gs" />
/// <reference path="parseColHLocation_.gs" />
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
 * @returns {{parsed: Object, unresolved: Array<string>}} Parsed data object and unresolved fields array
 */
function parseSourceRowEnhanced_(v) {
  // Initialize empty product data object
  const productCreateData = {};

  const sportName = normalizeSport_(capitalize(v.A.trim(), true));
  const unresolved = initializeUnresolvedFields(sportName);

  // Set sportName on productCreateData
  productCreateData.sportName = sportName;

  const { dayOfPlay, division, sportSubCategory, socialOrAdvanced, types, updatedUnresolved1 } =
    parseColBLeagueDetails_(v.B, unresolved, sportName);

  // Set fields returned by parseColBLeagueDetails on productCreateData
  productCreateData.dayOfPlay = dayOfPlay;
  productCreateData.division = division;
  productCreateData.sportSubCategory = sportSubCategory;
  productCreateData.socialOrAdvanced = socialOrAdvanced;
  productCreateData.types = types;

  // Column C parsing (notes, details, etc.)
  const { updatedUnresolved2 } = parseColC_(v.C, updatedUnresolved1);

  // Season dates (D/E)
  const { season, year, seasonStartDate, seasonEndDate, updatedUnresolved3 } =
    parseSeasonDates_(v.D, v.E, updatedUnresolved2);
  productCreateData.season = season;
  productCreateData.year = year;
  productCreateData.seasonStartDate = seasonStartDate;
  productCreateData.seasonEndDate = seasonEndDate;

  // Price (F) numeric
  const { price, updatedUnresolved4 } = parseColFPrice_(v.F, updatedUnresolved3);
  productCreateData.price = price;

  // Time range (G)
  // const timeInfo = parseTimeRangeBothSessions_(v.G, updatedUnresolved4);
  // const sportStartTime = timeInfo.primaryStartDateOnly;   // Date object with only time-of-day
  // const sportEndTime   = timeInfo.primaryEndDateOnly;
  // const alternativeStartTime = timeInfo.altStartDateOnly;
  // const alternativeEndTime   = timeInfo.altEndDateOnly;
  const { leagueStartTime, leagueEndTime, alternativeStartTime, alternativeEndTime, updatedUnresolved5 } = parseColGLeagueTimes_(v.G, updatedUnresolved4);
  productCreateData.leagueStartTime = leagueStartTime;
  productCreateData.leagueEndTime = leagueEndTime;
  productCreateData.alternativeStartTime = alternativeStartTime;
  productCreateData.alternativeEndTime = alternativeEndTime;



  // Location (H) parsed
  const { location, updatedUnresolved6 } = parseColHLocation_(v.H, sportName, updatedUnresolved5);
  productCreateData.location = location;

  // Registration windows (M/N/O) -> Date objects with seconds
  const earlyRegistrationStartDateTime = parseDateFlexibleDateTime_(v.M, sportStartTime, updatedUnresolved4, "earlyRegistrationStartDateTime");
  const vetRegistrationStartDateTime   = parseDateFlexibleDateTime_(v.N, sportStartTime, updatedUnresolved4, "vetRegistrationStartDateTime");
  const openRegistrationStartDateTime  = parseDateFlexibleDateTime_(v.O, sportStartTime, updatedUnresolved4, "openRegistrationStartDateTime");

  const {earlyRegistrationStartDateTime, vetRegistrationStartDateTime, openRegistrationStartDateTime, updatedUnresolved7} = parseColMNORegistrationDates_(v.M, v.N, v.O, updatedUnresolved6);
  const { updatedUnresolved7 } = parseColMNORegistrationDates_(v.C, updatedUnresolved6);
  const notes = parseNotes_(v.C, sportStartTime, updatedUnresolved4);
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

  // Remove alternative time fields from unresolved if found
  if (altStartFinal) {
    const startIndex = updatedUnresolved3.indexOf("alternativeStartTime");
    if (startIndex > -1) updatedUnresolved3.splice(startIndex, 1);
  }
  if (altEndFinal) {
    const endIndex = updatedUnresolved3.indexOf("alternativeEndTime");
    if (endIndex > -1) updatedUnresolved3.splice(endIndex, 1);
  }

  const offDatesFromText = extractOffDatesFromFreeText_(v.C, updatedUnresolved3);
  const offDatesCombined = dedupeCsv_([...offDatesFromNotes, ...offDatesFromText]);

  // Total inventory from details (# of Players: N)
  const totalInventory = extractPlayersFromDetails_(v.C, updatedUnresolved3);

  const parsed = {
    sportName,
    division,
    season,
    year,
    dayOfPlay,
    location,
    optionalLeagueInfo: {
      socialOrAdvanced,
      sportSubCategory,
      types: dedupeCsv_([...types, ...(notes.typesFromNotes || [])]).join(', ')
    },
    importantDates: {
      seasonStartDate,
      seasonEndDate,
      offDates: offDatesCombined, // Will be array of Date objects instead of comma-separated string
      newPlayerOrientationDateTime: orientationDate || '',
      scoutNightDateTime: scoutNightDate || '',
      openingPartyDate: openingPartyDate || '',
      rainDate: rainDate || '',
      closingPartyDate: closingPartyDate || '',
      vetRegistrationStartDateTime,
      earlyRegistrationStartDateTime,
      openRegistrationStartDateTime
    },
    leagueStartTime: sportStartTime,
    leagueEndTime: sportEndTime,
    alternativeStartTime: altStartFinal,
    alternativeEndTime: altEndFinal,
    inventoryInfo: {
      price,
      totalInventory,
      numberVetSpotsToReleaseAtGoLive: null // Will be extracted from parsing logic later
    }
  };

  return { parsed, unresolved: updatedUnresolved4 };
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
