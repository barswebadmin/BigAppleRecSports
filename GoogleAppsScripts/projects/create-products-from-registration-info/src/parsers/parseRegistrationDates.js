/**
 * Parses registration dates and calculates veteran spots to release.
 * Handles both Date objects and string formats (M/D/YY hA)
 *
 * @fileoverview Registration dates parsing
 * @requires ../helpers/dateParsers.gs
 */

import { parseDateFlexibleDateTime } from '../helpers/dateParsers.js';

/**
 * Parses the registration start dates.
 * Accepts Date objects or strings in format M/D/YY hA (e.g., "3/15/26 6PM")
 * Assumes input dates are in ET timezone, converts to UTC for storage
 *
 * @param {string|Date} vetRegInput - Vet registration date/time
 * @param {string|Date} tnbWtnbRegInput - WTNB/BIPOC/TNB registration date/time
 * @param {string|Date} openRegInput - Open registration date/time
 * @param {number} totalInventory - Total inventory count (not used, kept for compatibility)
 * @returns {{ vetRegistrationStartDateTime: Date|null, tnbWtnbRegistrationStartDateTime: Date|null, openRegistrationStartDateTime: Date|null }}
 *   Parsed registration dates in UTC, if found.
 */
export function parseRegistrationDates(vetRegInput, tnbWtnbRegInput, openRegInput, totalInventory) {
  let vetRegistrationStartDateTime = null;
  let tnbWtnbRegistrationStartDateTime = null;
  let openRegistrationStartDateTime = null;

  // Parse vet registration (L)
  vetRegistrationStartDateTime = parseRegistrationDateTime(vetRegInput);

  // Parse WTNB/BIPOC/TNB registration (M)
  tnbWtnbRegistrationStartDateTime = parseRegistrationDateTime(tnbWtnbRegInput);

  // Parse open registration (N)
  openRegistrationStartDateTime = parseRegistrationDateTime(openRegInput);

  return {
    vetRegistrationStartDateTime,
    tnbWtnbRegistrationStartDateTime,
    openRegistrationStartDateTime
  };
}

/**
 * Parse a registration date/time input (Date object or string)
 * @param {string|Date} input - Registration date/time input
 * @returns {Date|null} Parsed Date object or null
 */
export function parseRegistrationDateTime(input) {
  // Handle null, undefined, or empty
  if (!input) {
    return null;
  }

  // If already a Date object, return it
  if (input instanceof Date) {
    return input;
  }

  // If string, parse it
  if (typeof input === 'string') {
    const trimmed = input.trim();
    if (!trimmed) {
      return null;
    }

    // Clean the string - remove any "registration" prefix and "through"/"until" suffixes
    const cleaned = cleanRegistrationString(trimmed);
    
    // Parse using flexible date/time parser
    return parseDateFlexibleDateTime(cleaned, null, "registrationDateTime");
  }

  return null;
}

/**
 * Cleans registration string by removing 'registration' prefix and 'through'/'until' suffixes.
 * @param {string} rawString - The raw registration string.
 * @returns {string} Cleaned string ready for date parsing.
 */
export function cleanRegistrationString(rawString) {
  let cleaned = rawString.trim();

  // Remove 'registration' (case-insensitive) and any string before it
  const registrationMatch = cleaned.match(/^.*?registration\s*/i);
  if (registrationMatch) {
    cleaned = cleaned.substring(registrationMatch[0].length);
  }

  // Remove 'through' or 'until' and everything after it, including potential leading non-alphanumeric
  const throughUntilMatch = cleaned.match(/[^a-zA-Z0-9]*(?:through|until).*$/i);
  if (throughUntilMatch) {
    cleaned = cleaned.substring(0, throughUntilMatch.index);
  }

  return cleaned.trim();
}
