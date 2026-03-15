/**
 * Core row parsing functions for parse-registration-info
 * Main logic for converting spreadsheet rows to structured data
 *
 * @fileoverview Main row parsing orchestrator
 * @requires ../config/constants.gs
 * @requires ../helpers/normalizers.gs
 * @requires ../helpers/textUtils.gs
 * @requires parseLeagueBasicInfo.gs
 * @requires parseLeagueDetails.gs
 * @requires parseSeasonDates.gs
 * @requires timeParser.gs
 * @requires ../helpers/dateParsers.gs
 * @requires parsePrice.gs
 * @requires parseLocation.gs
 * @requires parseRegistrationDates.gs
 */

import { parseLeagueBasicInfo } from './parseLeagueBasicInfo.js';
import { parseLeagueDetails } from './parseLeagueDetails.js';
import { parseSeasonDates } from './parseSeasonDates.js';
import { parsePrice } from './parsePrice.js';
import { parseLeagueTimes } from './parseLeagueTimes.js';
import { parseLocation } from './parseLocation.js';
import { parseRegistrationDates } from './parseRegistrationDates.js';


/**
 * Parse a complete source row into structured data
 * Headers are expected on row 2, data starts on row 3
 * 
 * Column Headers (A-N):
 * A: DAY OF WEEK Type of Play/League
 * B: League Details
 * C: Season Start Date
 * D: Season End Date
 * E: Price
 * F: League Play Time(s)
 * G: Location (Field / Court / Lane)
 * H: League Contact Email(s)
 * I: How Vet Status is Determined
 * J: Additional Information?
 * K: Sport Wide-specific questions you want during registration:
 * L: Vet Register
 * M: WTNB/BIPOC/TNB Register
 * N: Open Register
 * 
 * @param {Object} v - Raw values object with columns A-N
 * @param {string} v.A - Day of Week and Type of Play/League
 * @param {string} v.B - League Details
 * @param {string} v.C - Season Start Date
 * @param {string} v.D - Season End Date
 * @param {string} v.E - Price
 * @param {string} v.F - League Play Time(s)
 * @param {string} v.G - Location (Field / Court / Lane)
 * @param {string} v.L - Vet Register
 * @param {string} v.M - WTNB/BIPOC/TNB Register
 * @param {string} v.N - Open Register
 * @returns {{parsed: Object, unresolved: Array<string>}} Parsed data object and unresolved fields array
 */
export function parseSourceRowEnhanced(v, sportNameOverride) {

  const productCreateData = {};

  // Sport name comes from the sheet tab name (passed in from parseRowDataForProductCreation)
  // Falls back to 'Kickball' if not provided
  const sportName = sportNameOverride || 'Kickball';
  productCreateData.sportName = sportName;

  const { dayOfPlay, division, levelOfPlay, teamAssignment, dodgeballBallType } =
  parseLeagueBasicInfo(v.A, sportName);

  productCreateData.dayOfPlay = dayOfPlay;
  productCreateData.division = division;
  productCreateData.levelOfPlay = levelOfPlay;
  productCreateData.teamAssignment = teamAssignment;
  productCreateData.dodgeballBallType = dodgeballBallType;

  // Column B parsing (league details, etc.)
  const { totalWeeks, newPlayerOrientationDateTime, scoutNightDateTime, openingPartyDate, rainDate, closingPartyDate, offDates, totalInventory, gameDuration } = parseLeagueDetails(v.B);


  // Season dates (C/D)
  const { season, year, seasonStartDate, seasonEndDate } =
    parseSeasonDates(v.C, v.D);
  productCreateData.season = season;
  productCreateData.year = year;
  productCreateData.seasonStartDate = seasonStartDate;
  productCreateData.seasonEndDate = seasonEndDate;

  // Price (E) numeric
  const { price } = parsePrice(v.E);
  productCreateData.price = price;

  // Time range (F)
  const { leagueStartTime, leagueEndTime, alternativeStartTime, alternativeEndTime } = parseLeagueTimes(v.F);
  productCreateData.leagueStartTime = leagueStartTime;
  productCreateData.leagueEndTime = leagueEndTime;
  productCreateData.alternativeStartTime = alternativeStartTime;
  productCreateData.alternativeEndTime = alternativeEndTime;



  // Location (G) parsed - returns {raw, formatted} object
  const locationResult = parseLocation(v.G, sportName);
  productCreateData.location = locationResult.location;

  // League Contact Email(s) (H) - raw email string
  const leagueContactEmail = v.H ? v.H.trim() : null;
  productCreateData.leagueContactEmail = leagueContactEmail;

  // How Vet Status is Determined (I) - string to use in vet registration description
  const vetStatusDeterminedBy = v.I ? v.I.trim() : 'most recent season';
  productCreateData.vetStatusDeterminedBy = vetStatusDeterminedBy;

  // Registration windows (L/M/N) -> Date objects with seconds

  const {vetRegistrationStartDateTime, tnbWtnbRegistrationStartDateTime, openRegistrationStartDateTime} = parseRegistrationDates(v.L, v.M, v.N, totalInventory);


  const parsed = {
    sportName: productCreateData.sportName,
    division: productCreateData.division,
    season: productCreateData.season,
    year: productCreateData.year,
    dayOfPlay: productCreateData.dayOfPlay,
    location: productCreateData.location,
    leagueContactEmail: productCreateData.leagueContactEmail,
    vetStatusDeterminedBy: productCreateData.vetStatusDeterminedBy,
    optionalLeagueInfo: {
      levelOfPlay: productCreateData.levelOfPlay,
      teamAssignment: productCreateData.teamAssignment,
      dodgeballBallType: productCreateData.dodgeballBallType
    },
    importantDates: {
      seasonStartDate: productCreateData.seasonStartDate,
      seasonEndDate: productCreateData.seasonEndDate,
      offDates,
      newPlayerOrientationDateTime,
      scoutNightDateTime,
      openingPartyDate,
      rainDate,
      closingPartyDate,
      vetRegistrationStartDateTime,
      tnbWtnbRegistrationStartDateTime,
      openRegistrationStartDateTime
    },
    leagueStartTime: productCreateData.leagueStartTime,
    leagueEndTime: productCreateData.leagueEndTime,
    alternativeStartTime: productCreateData.alternativeStartTime,
    alternativeEndTime: productCreateData.alternativeEndTime,
    gameDuration,
    inventoryInfo: {
      price: productCreateData.price,
      totalInventory,
      totalWeeks
    }
  };

  return parsed;
}
