/**
 * Season dates parsing functions
 * Handles parsing of season start/end dates with flexible formats
 * Accepts both string formats (M/D/YY) and datetime objects from Google Sheets
 *
 * @fileoverview Parse season dates with format flexibility
 * @requires ../config/constants.gs
 * @requires ../helpers/normalizers.gs
 * @requires ../helpers/dateParsers.gs
 */

import { parseFlexibleDate } from '../helpers/dateParsers.js';
import { deriveSeasonYearFromDate } from '../helpers/normalizers.js';

/**
 * Parse season start and end dates with flexible format support
 * Handles both string formats (M/D/YY) and Date objects from Google Sheets
 * Assumes input dates are in ET timezone, converts to UTC for storage
 * 
 * @param {string|Date} startDateInput - Raw start date (string like "M/D/YY" or Date object)
 * @param {string|Date} endDateInput - Raw end date (string like "M/D/YY" or Date object)
 * @returns {{season: string, year: number, seasonStartDate: Date, seasonEndDate: Date}} Parsed season information with UTC dates
 */
export function parseSeasonDates(startDateInput, endDateInput) {
  let season = null;
  let year = null;
  let seasonStartDate = null;
  let seasonEndDate = null;

  try {
    // Handle start date - check if it's already a Date object
    if (startDateInput instanceof Date) {
      seasonStartDate = startDateInput;
    } else if (startDateInput && typeof startDateInput === 'string' && startDateInput.trim()) {
      // Parse string using dateParsers with UTC support
      seasonStartDate = parseFlexibleDate(startDateInput.trim(), true);
    }

    // Handle end date - check if it's already a Date object
    if (endDateInput instanceof Date) {
      seasonEndDate = endDateInput;
    } else if (endDateInput && typeof endDateInput === 'string' && endDateInput.trim()) {
      // Parse string using dateParsers with UTC support
      seasonEndDate = parseFlexibleDate(endDateInput.trim(), true);
    }

    // Derive season and year from the start date
    if (seasonStartDate) {
      const derivedInfo = deriveSeasonYearFromDate(seasonStartDate);
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
