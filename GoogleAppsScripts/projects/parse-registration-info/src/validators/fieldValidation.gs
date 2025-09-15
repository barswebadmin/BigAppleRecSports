/**
 * Field validation functions for parse-registration-info
 * Check required fields and data integrity
 *
 * @fileoverview Field validation and header mapping
 * @requires ../config/constants.gs
 * @requires ../helpers/textUtils.gs
 */

// Import references for editor support
/// <reference path="../config/constants.gs" />
/// <reference path="../helpers/textUtils.gs" />

/**
 * Check that all required fields are present and valid
 */
function checkRequiredFields_(parsed, targetHeadersRaw) {
  const missing = [];
  const targetHeadersNorm = targetHeadersRaw.map(normalizeHeader_);

  for (const reqHeader of REQUIRED_TARGET_HEADERS) {
    const reqIdx = targetHeadersNorm.indexOf(normalizeHeader_(reqHeader));
    // Find the object key we intend to write for this header
    // (reverse lookup using headerMapping)
    const objKey = headerMapping[reqHeader];
    if (reqIdx === -1) continue; // header not present in the target sheet

    const val = parsed[objKey];
    const isBlank =
      val === '' ||
      val == null ||
      (val instanceof Date && isNaN(val.valueOf())); // invalid date

    if (isBlank) missing.push(reqHeader);
  }

  return { missing };
}

/**
 * Calculate unresolved fields for parsed data
 * Compares comprehensive fields against actual parsed data, filtering out sport-specific irrelevant fields
 *
 * @param {Object} parsedData - The parsed product creation data object
 * @returns {Array<string>} Array of field names that are missing/unresolved in the parsed data
 */
function calculateUnresolvedFieldsForParsedData(parsedData) {
  if (!parsedData || typeof parsedData !== 'object') {
    console.warn('calculateUnresolvedFieldsForParsedData: Invalid parsedData provided');
    return [...comprehensiveProductCreateFields]; // All fields unresolved if no data
  }

  const sportName = parsedData.sportName;
  if (!sportName) {
    console.warn('calculateUnresolvedFieldsForParsedData: No sportName found in parsedData');
    return [...comprehensiveProductCreateFields]; // All fields unresolved if no sport
  }

  // Get sport-specific irrelevant fields to exclude
  const irrelevantFields = irrelevantFieldsForSport[sportName] || [];

  // Start with all comprehensive fields, then remove irrelevant ones for this sport
  const relevantFields = comprehensiveProductCreateFields.filter(field =>
    !irrelevantFields.includes(field)
  );

  // Find fields that are missing or have falsy values in the parsed data
  const unresolvedFields = [];

  for (const fieldName of relevantFields) {
    const value = getNestedFieldValue(parsedData, fieldName);

    // Consider a field unresolved if:
    // - It's null or undefined
    // - It's an empty string
    // - It's an empty array
    // - It's NaN (for numbers)
    if (isFieldValueEmpty(value)) {
      unresolvedFields.push(fieldName);
    }
  }

  return unresolvedFields;
}

/**
 * Get nested field value from parsed data object
 * Handles both flat fields and nested object fields
 *
 * @param {Object} parsedData - The parsed data object
 * @param {string} fieldName - The field name to retrieve
 * @returns {*} The field value, or undefined if not found
 */
function getNestedFieldValue(parsedData, fieldName) {
  // Check flat fields first
  if (parsedData.hasOwnProperty(fieldName)) {
    return parsedData[fieldName];
  }

  // Check nested fields in common locations
  const nestedLocations = [
    'optionalLeagueInfo',
    'importantDates',
    'inventoryInfo'
  ];

  for (const location of nestedLocations) {
    if (parsedData[location] && parsedData[location].hasOwnProperty(fieldName)) {
      return parsedData[location][fieldName];
    }
  }

  return undefined;
}

/**
 * Check if a field value should be considered empty/unresolved
 *
 * @param {*} value - The value to check
 * @returns {boolean} True if the value should be considered empty/unresolved
 */
function isFieldValueEmpty(value) {
  // Null or undefined
  if (value == null) {
    return true;
  }

  // Empty string
  if (typeof value === 'string' && value.trim() === '') {
    return true;
  }

  // Empty array
  if (Array.isArray(value) && value.length === 0) {
    return true;
  }

  // NaN for numbers
  if (typeof value === 'number' && isNaN(value)) {
    return true;
  }

  // Invalid dates
  if (value instanceof Date && isNaN(value.valueOf())) {
    return true;
  }

  return false;
}
