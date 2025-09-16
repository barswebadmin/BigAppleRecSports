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

/**
 * Ensure parsed product data retains canonical nested structure expected by backend
 * - If keys for nested objects are missing, create them
 * - If some fields were placed at top-level for display, move them into nested objects
 */

// biome-ignore lint/correctness/noUnusedVariables: <used in createShopifyProduct flow>
function validProductCreateRequest_(data) {
  const IN = data || {};
  const out = JSON.parse(JSON.stringify(IN)); // shallow clone for GAS

  // Initialize nested containers if missing
  out.regularSeasonBasicDetails = out.regularSeasonBasicDetails || {};
  out.optionalLeagueInfo = out.optionalLeagueInfo || {};
  out.importantDates = out.importantDates || {};
  out.inventoryInfo = out.inventoryInfo || {};

  // Move likely top-level fields into their canonical nested homes
  // RegularSeasonBasicDetails
  if (out.year != null && out.regularSeasonBasicDetails.year == null) out.regularSeasonBasicDetails.year = out.year;
  if (out.season != null && out.regularSeasonBasicDetails.season == null) out.regularSeasonBasicDetails.season = out.season;
  if (out.dayOfPlay != null && out.regularSeasonBasicDetails.dayOfPlay == null) out.regularSeasonBasicDetails.dayOfPlay = out.dayOfPlay;
  if (out.division != null && out.regularSeasonBasicDetails.division == null) out.regularSeasonBasicDetails.division = out.division;
  if (out.location != null && out.regularSeasonBasicDetails.location == null) out.regularSeasonBasicDetails.location = out.location;
  if (out.leagueStartTime != null && out.regularSeasonBasicDetails.leagueStartTime == null) out.regularSeasonBasicDetails.leagueStartTime = out.leagueStartTime;
  if (out.leagueEndTime != null && out.regularSeasonBasicDetails.leagueEndTime == null) out.regularSeasonBasicDetails.leagueEndTime = out.leagueEndTime;
  if (out.alternativeStartTime != null && out.regularSeasonBasicDetails.alternativeStartTime == null) out.regularSeasonBasicDetails.alternativeStartTime = out.alternativeStartTime;
  if (out.alternativeEndTime != null && out.regularSeasonBasicDetails.alternativeEndTime == null) out.regularSeasonBasicDetails.alternativeEndTime = out.alternativeEndTime;

  // OptionalLeagueInfo
  if (out.socialOrAdvanced != null && out.optionalLeagueInfo.socialOrAdvanced == null) out.optionalLeagueInfo.socialOrAdvanced = out.socialOrAdvanced;
  if (out.sportSubCategory != null && out.optionalLeagueInfo.sportSubCategory == null) out.optionalLeagueInfo.sportSubCategory = out.sportSubCategory;
  if (out.types != null && out.optionalLeagueInfo.types == null) out.optionalLeagueInfo.types = out.types;

  // ImportantDates
  const dateKeys = [
    'seasonStartDate','seasonEndDate','vetRegistrationStartDateTime','earlyRegistrationStartDateTime','openRegistrationStartDateTime',
    'newPlayerOrientationDateTime','scoutNightDateTime','openingPartyDate','rainDate','closingPartyDate','offDates'
  ];
  for (var i=0;i<dateKeys.length;i++) {
    var k = dateKeys[i];
    if (out[k] != null && out.importantDates[k] == null) out.importantDates[k] = out[k];
  }

  // InventoryInfo
  if (out.price != null && out.inventoryInfo.price == null) out.inventoryInfo.price = out.price;
  if (out.totalInventory != null && out.inventoryInfo.totalInventory == null) out.inventoryInfo.totalInventory = out.totalInventory;
  if (out.numberVetSpotsToReleaseAtGoLive != null && out.inventoryInfo.numberVetSpotsToReleaseAtGoLive == null) out.inventoryInfo.numberVetSpotsToReleaseAtGoLive = out.numberVetSpotsToReleaseAtGoLive;

  // Minimal shape validation (frontend preflight)
  var missing = [];
  function req(val, label){ if (val == null || val === '' || (typeof val==='string' && val.trim()==='')) missing.push(label); }
  req(out.sportName, 'sportName');
  var r = out.regularSeasonBasicDetails || {};
  req(r.year, 'regularSeasonBasicDetails.year');
  req(r.season, 'regularSeasonBasicDetails.season');
  req(r.dayOfPlay, 'regularSeasonBasicDetails.dayOfPlay');
  req(r.division, 'regularSeasonBasicDetails.division');
  req(r.location, 'regularSeasonBasicDetails.location');
  req(r.leagueStartTime, 'regularSeasonBasicDetails.leagueStartTime');
  req(r.leagueEndTime, 'regularSeasonBasicDetails.leagueEndTime');
  var d = out.importantDates || {};
  req(d.seasonStartDate, 'importantDates.seasonStartDate');
  req(d.seasonEndDate, 'importantDates.seasonEndDate');
  req(d.openRegistrationStartDateTime, 'importantDates.openRegistrationStartDateTime');
  var inv = out.inventoryInfo || {};
  req(inv.price, 'inventoryInfo.price');
  req(inv.totalInventory, 'inventoryInfo.totalInventory');

  if (missing.length) {
    SpreadsheetApp.getUi().alert('Missing required fields before send to backend:\n\n' + missing.join('\n'));
    throw new Error('Invalid product request: missing ' + missing.join(', '));
  }

  return out; // canonical nested, validated
}

/**
 * Canonicalize product data into backend-like nested shape for display only.
 * Same field moves as validProductCreateRequest_ but without validation/throws.
 */
// biome-ignore lint/correctness/noUnusedVariables: <used for display before confirm>
function canonicalizeForDisplay_(data) {
  const IN = data || {};
  const out = JSON.parse(JSON.stringify(IN));

  out.regularSeasonBasicDetails = out.regularSeasonBasicDetails || {};
  out.optionalLeagueInfo = out.optionalLeagueInfo || {};
  out.importantDates = out.importantDates || {};
  out.inventoryInfo = out.inventoryInfo || {};

  if (out.year != null && out.regularSeasonBasicDetails.year == null) out.regularSeasonBasicDetails.year = out.year;
  if (out.season != null && out.regularSeasonBasicDetails.season == null) out.regularSeasonBasicDetails.season = out.season;
  if (out.dayOfPlay != null && out.regularSeasonBasicDetails.dayOfPlay == null) out.regularSeasonBasicDetails.dayOfPlay = out.dayOfPlay;
  if (out.division != null && out.regularSeasonBasicDetails.division == null) out.regularSeasonBasicDetails.division = out.division;
  if (out.location != null && out.regularSeasonBasicDetails.location == null) out.regularSeasonBasicDetails.location = out.location;
  if (out.leagueStartTime != null && out.regularSeasonBasicDetails.leagueStartTime == null) out.regularSeasonBasicDetails.leagueStartTime = out.leagueStartTime;
  if (out.leagueEndTime != null && out.regularSeasonBasicDetails.leagueEndTime == null) out.regularSeasonBasicDetails.leagueEndTime = out.leagueEndTime;
  if (out.alternativeStartTime != null && out.regularSeasonBasicDetails.alternativeStartTime == null) out.regularSeasonBasicDetails.alternativeStartTime = out.alternativeStartTime;
  if (out.alternativeEndTime != null && out.regularSeasonBasicDetails.alternativeEndTime == null) out.regularSeasonBasicDetails.alternativeEndTime = out.alternativeEndTime;

  if (out.socialOrAdvanced != null && out.optionalLeagueInfo.socialOrAdvanced == null) out.optionalLeagueInfo.socialOrAdvanced = out.socialOrAdvanced;
  if (out.sportSubCategory != null && out.optionalLeagueInfo.sportSubCategory == null) out.optionalLeagueInfo.sportSubCategory = out.sportSubCategory;
  if (out.types != null && out.optionalLeagueInfo.types == null) out.optionalLeagueInfo.types = out.types;

  const dateKeys = [
    'seasonStartDate','seasonEndDate','vetRegistrationStartDateTime','earlyRegistrationStartDateTime','openRegistrationStartDateTime',
    'newPlayerOrientationDateTime','scoutNightDateTime','openingPartyDate','rainDate','closingPartyDate','offDates'
  ];
  for (var i=0;i<dateKeys.length;i++) {
    var k = dateKeys[i];
    if (out[k] != null && out.importantDates[k] == null) out.importantDates[k] = out[k];
  }

  if (out.price != null && out.inventoryInfo.price == null) out.inventoryInfo.price = out.price;
  if (out.totalInventory != null && out.inventoryInfo.totalInventory == null) out.inventoryInfo.totalInventory = out.totalInventory;
  if (out.numberVetSpotsToReleaseAtGoLive != null && out.inventoryInfo.numberVetSpotsToReleaseAtGoLive == null) out.inventoryInfo.numberVetSpotsToReleaseAtGoLive = out.numberVetSpotsToReleaseAtGoLive;

  return out;
}
