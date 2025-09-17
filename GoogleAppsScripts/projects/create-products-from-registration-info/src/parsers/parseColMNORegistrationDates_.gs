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
 * @returns {{ earlyRegistrationStartDateTime: Date|null, vetRegistrationStartDateTime: Date|null, openRegistrationStartDateTime: Date|null, numberVetSpotsToReleaseAtGoLive: number }}
 *   Parsed registration dates, if found.
 */
function parseColMNORegistrationDates_(mColumnData, nColumnData, oColumnData, totalInventory) {
  let earlyRegistrationStartDateTime = null;
  let vetRegistrationStartDateTime = null;
  let openRegistrationStartDateTime = null;
  let numberVetSpotsToReleaseAtGoLive = totalInventory; // Default to total inventory

  // Parse early registration (M)
  if (mColumnData && typeof mColumnData === 'string' && mColumnData.trim()) {
    const cleanedM = cleanRegistrationString_(mColumnData);
    earlyRegistrationStartDateTime = parseDateFlexibleDateTime_(cleanedM, null, "earlyRegistrationStartDateTime");
  }

  // Parse veteran registration (N)
  if (nColumnData && typeof nColumnData === 'string' && nColumnData.trim()) {
    const cleanedN = cleanRegistrationString_(nColumnData);
    vetRegistrationStartDateTime = parseDateFlexibleDateTime_(cleanedN, null, "vetRegistrationStartDateTime");
  }

  // Parse open registration (O)
  if (oColumnData && typeof oColumnData === 'string' && oColumnData.trim()) {
    const cleanedO = cleanRegistrationString_(oColumnData);
    openRegistrationStartDateTime = parseDateFlexibleDateTime_(cleanedO, null, "openRegistrationStartDateTime");
  }

  // Try to calculate numberVetSpotsToReleaseAtGoLive from the veteran registration string
  if (nColumnData && typeof nColumnData === 'string' && nColumnData.trim()) {
    const extractedNumber = extractVetSpots_(nColumnData);
    if (extractedNumber !== null) {
      numberVetSpotsToReleaseAtGoLive = extractedNumber;
    }
  }

  // Coerce invalid "" results to null to ensure these are either Date or null
  if (earlyRegistrationStartDateTime === '') earlyRegistrationStartDateTime = null;
  if (vetRegistrationStartDateTime === '') vetRegistrationStartDateTime = null;
  if (openRegistrationStartDateTime === '') openRegistrationStartDateTime = null;

  return {
    earlyRegistrationStartDateTime,
    vetRegistrationStartDateTime,
    openRegistrationStartDateTime,
    numberVetSpotsToReleaseAtGoLive
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
 * Looks for lines containing 'spot', 'inventory', or 'vet' keywords.
 * @param {string} rawString - The raw registration string.
 * @returns {number|null} Extracted number or null if not found.
 */
function extractVetSpots_(rawString) {
  if (!rawString || typeof rawString !== 'string') {
    return null;
  }

  // Split into lines and look for lines with the specified keywords
  const lines = rawString.split('\n').map(line => line.trim()).filter(line => line.length > 0);

  for (const line of lines) {
    const lowerLine = line.toLowerCase();

    // Check if line contains any of the keywords: spot, inventory, vet
    if (lowerLine.includes('spot') || lowerLine.includes('inventory') || lowerLine.includes('vet')) {
      // Extract number from this line
      const numberMatch = line.match(/(\d+)/);
      if (numberMatch) {
        return Number.parseInt(numberMatch[1]);
      }
    }
  }

  // Fallback: Look for original patterns like "20 spots", "15 through", etc.
  const numberMatch = rawString.match(/(\d+)\s*(?:spots?|through|until)/i);
  if (numberMatch) {
    return parseInt(numberMatch[1]);
  }

  return null;
}
