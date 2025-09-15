/**
 * Season dates parsing functions
 * Handles parsing of season start/end dates with flexible formats
 *
 * @fileoverview Parse season dates from D/E columns with format flexibility
 * @requires ../config/constants.gs
 * @requires ../helpers/normalizers.gs
 * @requires ../helpers/DateParsers.gs
 */

// Import references for editor support
/// <reference path="../config/constants.gs" />
/// <reference path="../helpers/normalizers.gs" />
/// <reference path="../helpers/DateParsers.gs" />

/**
 * Parse season start and end dates with flexible format support
 * @param {string} startDateStr - Raw start date string from column D
 * @param {string} endDateStr - Raw end date string from column E
 * @param {Array<string>} unresolved - Array to track unresolved fields
 * @returns {{season: string, year: number, seasonStartDate: Date, seasonEndDate: Date, updatedUnresolved: Array<string>}} Parsed season information
 */
function parseSeasonDates_(startDateStr, endDateStr, unresolved) {
  const updatedUnresolved = [...unresolved];
  let season = null;
  let year = null;
  let seasonStartDate = null;
  let seasonEndDate = null;

  try {
    // Parse start date using DateParsers with UTC support
    seasonStartDate = DateParsers.parseFlexibleDate_(startDateStr?.trim(), true);
    if (seasonStartDate) {
      // Remove seasonStartDate from unresolved
      const startIndex = updatedUnresolved.indexOf("seasonStartDate");
      if (startIndex > -1) updatedUnresolved.splice(startIndex, 1);
    }

    // Parse end date using DateParsers with UTC support
    seasonEndDate = DateParsers.parseFlexibleDate_(endDateStr?.trim(), true);
    if (seasonEndDate) {
      // Remove seasonEndDate from unresolved
      const endIndex = updatedUnresolved.indexOf("seasonEndDate");
      if (endIndex > -1) updatedUnresolved.splice(endIndex, 1);
    }

    // Derive season and year from the start date
    if (seasonStartDate) {
      const derivedInfo = deriveSeasonYearFromDate_(seasonStartDate);
      season = derivedInfo.season;
      year = derivedInfo.year;

      if (season) {
        const seasonIndex = updatedUnresolved.indexOf("season");
        if (seasonIndex > -1) updatedUnresolved.splice(seasonIndex, 1);
      }

      if (year) {
        const yearIndex = updatedUnresolved.indexOf("year");
        if (yearIndex > -1) updatedUnresolved.splice(yearIndex, 1);
      }
    }
  } catch (error) {
    console.warn('Error parsing season dates:', error);
  }

  return {
    season,
    year,
    seasonStartDate,
    seasonEndDate,
    updatedUnresolved3
  };
}
