/**
 * Parses registration dates from columns M, N, O and calculates veteran spots to release.
 * Handles cleaning of registration prefixes and calculates veteran spots based on available data.
 *
 * @fileoverview Registration dates parsing for columns M, N, O
 * @requires ../helpers/dateParsers.gs
 */

// Import references for editor support
/// <reference path="../helpers/dateParsers.gs" />

/**
 * Parses the registration start dates from columns M, N, O.
 *
 * @param {string} mColumnData - The raw string content from column M (early registration).
 * @param {string} nColumnData - The raw string content from column N (veteran registration).
 * @param {string} oColumnData - The raw string content from column O (open registration).
 * @param {number} totalInventory - Total inventory count for calculating veteran spots.
 * @param {Array<string>} unresolved - The array of unresolved fields.
 * @returns {{earlyRegistrationStartDateTime: Date|null, vetRegistrationStartDateTime: Date|null, openRegistrationStartDateTime: Date|null, numberVetSpotsToReleaseAtGoLive: number, updatedUnresolved7: Array<string>}}
 *   Parsed registration dates and updated unresolved array.
 */
function parseColMNORegistrationDates_(mColumnData, nColumnData, oColumnData, totalInventory, unresolved) {
  const updatedUnresolved7 = [...unresolved];
  let earlyRegistrationStartDateTime = null;
  let vetRegistrationStartDateTime = null;
  let openRegistrationStartDateTime = null;
  let numberVetSpotsToReleaseAtGoLive = totalInventory; // Default to total inventory

  // Parse early registration (M)
  if (mColumnData && typeof mColumnData === 'string' && mColumnData.trim()) {
    const cleanedM = cleanRegistrationString_(mColumnData);
    earlyRegistrationStartDateTime = parseDateFlexibleDateTime_(cleanedM, null, updatedUnresolved7, "earlyRegistrationStartDateTime");
  }

  // Parse veteran registration (N)
  if (nColumnData && typeof nColumnData === 'string' && nColumnData.trim()) {
    const cleanedN = cleanRegistrationString_(nColumnData);
    vetRegistrationStartDateTime = parseDateFlexibleDateTime_(cleanedN, null, updatedUnresolved7, "vetRegistrationStartDateTime");
  }

  // Parse open registration (O)
  if (oColumnData && typeof oColumnData === 'string' && oColumnData.trim()) {
    const cleanedO = cleanRegistrationString_(oColumnData);
    openRegistrationStartDateTime = parseDateFlexibleDateTime_(cleanedO, null, updatedUnresolved7, "openRegistrationStartDateTime");
  }

  // Try to calculate numberVetSpotsToReleaseAtGoLive from the veteran registration string
  if (nColumnData && typeof nColumnData === 'string' && nColumnData.trim()) {
    const extractedNumber = extractVetSpots_(nColumnData);
    if (extractedNumber !== null) {
      numberVetSpotsToReleaseAtGoLive = extractedNumber;
    }
  }

  return {
    earlyRegistrationStartDateTime,
    vetRegistrationStartDateTime,
    openRegistrationStartDateTime,
    numberVetSpotsToReleaseAtGoLive,
    updatedUnresolved7
  };
}

/**
 * Cleans registration string by removing 'registration' prefix and 'through'/'until' suffixes.
 * @param {string} rawString - The raw registration string.
 * @returns {string} Cleaned string ready for date parsing.
 */
function cleanRegistrationString_(rawString) {
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

/**
 * Extracts veteran spots number from registration string.
 * @param {string} rawString - The raw registration string.
 * @returns {number|null} Extracted number or null if not found.
 */
function extractVetSpots_(rawString) {
  // Look for patterns like "20 spots", "15 through", etc.
  const numberMatch = rawString.match(/(\d+)\s*(?:spots?|through|until)/i);
  if (numberMatch) {
    return parseInt(numberMatch[1]);
  }
  return null;
}
