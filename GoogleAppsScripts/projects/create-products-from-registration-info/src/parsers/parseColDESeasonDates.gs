/**
 * Season dates parsing functions
 * Handles parsing of season start/end dates with flexible formats
 *
 * @fileoverview Parse season dates from D/E columns with format flexibility
 * @requires ../config/constants.gs
 * @requires ../helpers/normalizers.gs
 * @requires ../helpers/dateParsers.gs
 */

// Import references for editor support
/// <reference path="../config/constants.gs" />
/// <reference path="../helpers/normalizers.gs" />
/// <reference path="../helpers/dateParsers.gs" />

/**
 * Parse season start and end dates with flexible format support
 * @param {string} startDateStr - Raw start date string from column D
 * @param {string} endDateStr - Raw end date string from column E
 * @returns {{season: string, year: number, seasonStartDate: Date, seasonEndDate: Date}} Parsed season information
 */
function parseColDESeasonDates_(startDateStr, endDateStr) {
  let season = null;
  let year = null;
  let seasonStartDate = null;
  let seasonEndDate = null;

  try {
    // Parse start date using dateParsers with UTC support
    seasonStartDate = parseFlexibleDate_(startDateStr?.trim(), true);

    // Parse end date using dateParsers with UTC support
    seasonEndDate = parseFlexibleDate_(endDateStr?.trim(), true);

    // Derive season and year from the start date
    if (seasonStartDate) {
      const derivedInfo = deriveSeasonYearFromDate_(seasonStartDate);
      season = derivedInfo.season;
      year = derivedInfo.year;

    }
  } catch (error) {
    console.warn('Error parsing season dates:', error);
  }

  return {
    season,
    year,
    seasonStartDate,
    seasonEndDate
  };
}
