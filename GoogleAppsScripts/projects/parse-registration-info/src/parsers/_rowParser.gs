/**
 * Core row parsing functions for parse-registration-info
 * Main logic for converting spreadsheet rows to structured data
 *
 * @fileoverview Main row parsing orchestrator
 * @requires ../config/constants.gs
 * @requires ../helpers/normalizers.gs
 * @requires ../helpers/textUtils.gs
 * @requires parseColBLeagueBasicInfo_.gs
 * @requires parseColCLeagueDetails_.gs
 * @requires parseColDESeasonDates_.gs
 * @requires timeParser.gs
 * @requires ../helpers/dateParsers.gs
 * @requires parseColFPrice_.gs
 * @requires parseColHLocation_.gs
 * @requires parseColMNORegistrationDates_.gs
 */

// Import references for editor support
/// <reference path="../config/constants.gs" />
/// <reference path="../helpers/normalizers.gs" />
/// <reference path="../helpers/textUtils.gs" />
/// <reference path="parseColBLeagueBasicInfo_.gs" />
/// <reference path="parseColCLeagueDetails_.gs" />
/// <reference path="parseColDESeasonDates.gs" />
/// <reference path="../helpers/dateParsers.gs" />
/// <reference path="parseColFPrice_.gs" />
/// <reference path="parseColGLeagueTimes_.gs" />
/// <reference path="parseColHLocation_.gs" />
/// <reference path="parseColMNORegistrationDates_.gs" />


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

  const productCreateData = {};

  const sportName = normalizeSport_(capitalize(v.A.trim(), true));
  productCreateData.sportName = sportName;

  const { dayOfPlay, division, sportSubCategory, socialOrAdvanced, types } =
  parseColBLeagueBasicInfo_(v.B, sportName);

  productCreateData.dayOfPlay = dayOfPlay;
  productCreateData.division = division;
  productCreateData.sportSubCategory = sportSubCategory;
  productCreateData.socialOrAdvanced = socialOrAdvanced;
  productCreateData.types = types;

  // Column C parsing (league details, etc.)
  const { closingPartyDate, offDates, tournamentDate, totalInventory } = parseColCLeagueDetails_(v.C);

  // Set additional variables for the parsed structure
  const newPlayerOrientationDateTime = null; // TODO: Implement orientation parsing
  const scoutNightDateTime = null; // TODO: Implement scout night parsing
  const openingPartyDate = null; // TODO: Implement opening party parsing
  const rainDate = null; // TODO: Implement rain date parsing


  // Season dates (D/E)
  const { season, year, seasonStartDate, seasonEndDate } =
    parseColDESeasonDates_(v.D, v.E);
  productCreateData.season = season;
  productCreateData.year = year;
  productCreateData.seasonStartDate = seasonStartDate;
  productCreateData.seasonEndDate = seasonEndDate;

  // Price (F) numeric
  const { price } = parseColFPrice_(v.F);
  productCreateData.price = price;

  // Time range (G)
  const { leagueStartTime, leagueEndTime, alternativeStartTime, alternativeEndTime } = parseColGLeagueTimes_(v.G);
  productCreateData.leagueStartTime = leagueStartTime;
  productCreateData.leagueEndTime = leagueEndTime;
  productCreateData.alternativeStartTime = alternativeStartTime;
  productCreateData.alternativeEndTime = alternativeEndTime;



  // Location (H) parsed
  const { location } = parseColHLocation_(v.H, sportName);
  productCreateData.location = location;

  // Registration windows (M/N/O) -> Date objects with seconds

  const {earlyRegistrationStartDateTime, vetRegistrationStartDateTime, openRegistrationStartDateTime, numberVetSpotsToReleaseAtGoLive} = parseColMNORegistrationDates_(v.M, v.N, v.O, totalInventory);


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
      types
    },
    importantDates: {
      seasonStartDate,
      seasonEndDate,
      offDates,
      newPlayerOrientationDateTime,
      scoutNightDateTime,
      openingPartyDate,
      rainDate,
      closingPartyDate,
      vetRegistrationStartDateTime,
      earlyRegistrationStartDateTime,
      openRegistrationStartDateTime
    },
    leagueStartTime,
    leagueEndTime,
    alternativeStartTime,
    alternativeEndTime,
    inventoryInfo: {
      price,
      totalInventory,
      numberVetSpotsToReleaseAtGoLive
    }
  };

  return parsed;
}
