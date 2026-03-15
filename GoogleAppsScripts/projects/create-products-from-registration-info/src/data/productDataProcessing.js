/**
 * Product data processing and validation functions
 * Handles data parsing, validation, field management, and data transformation
 *
 * @fileoverview Product data processing and validation
 * @requires ../parsers/_rowParser.gs
 * @requires ../helpers/normalizers.gs
 * @requires ../config/constants.gs
 * @requires ../helpers/formatValidators.gs
 */

import { parseSourceRowEnhanced } from '../parsers/_rowParser.js';
import { createCellMapping } from '../sheet/cellMapping.js';
import { formatDateMdYY, formatDateTimeMdYYhm, isTime12h, isDateTimeAllowed, isDateMMDDYYYY } from '../helpers/formatValidators.js';
import { formatTimeForDisplay } from '../utils/formatting.js';
import { productFieldEnums, irrelevantFieldsForSport } from '../config/constants.js';
import { normalizeSport } from '../helpers/normalizers.js';

/**
 * Parse row data for product creation
 */
export function parseRowDataForProductCreation(sourceSheet, rowNumber) {
  try {
    // Read source row columns A..N
    const rowValues = sourceSheet.getRange(rowNumber, 1, 1, 14).getDisplayValues()[0]; // Read A to N columns
    const vals = {
      A: (rowValues[0] || '').toString(), // Day of Week Type of Play/League
      B: (rowValues[1] || '').toString(), // League Details
      C: (rowValues[2] || '').toString(), // Season Start Date
      D: (rowValues[3] || '').toString(), // Season End Date
      E: (rowValues[4] || '').toString(), // Price
      F: (rowValues[5] || '').toString(), // League Play Time(s)
      G: (rowValues[6] || '').toString(), // Location (Field / Court / Lane)
      H: (rowValues[7] || '').toString(), // League Contact Email(s)
      I: (rowValues[8] || '').toString(), // How Vet Status is Determined
      L: (rowValues[11] || '').toString(), // Vet Register
      M: (rowValues[12] || '').toString(), // WTNB/BIPOC/TNB Register
      N: (rowValues[13] || '').toString(), // Open Register
    };

    // Derive sport name from the sheet tab name, normalized to canonical form (e.g. "KICKBALL" → "Kickball")
    const rawSheetName = sourceSheet.getName().trim();
    const sheetName = normalizeSport(rawSheetName) || rawSheetName;

    // Parse using existing logic
    const parsed = parseSourceRowEnhanced(vals, sheetName);

    // Create cell mapping for field updates
    const cellMapping = createCellMapping(sourceSheet, rowNumber, vals);

    Logger.log(`Parsed product data: ${JSON.stringify(parsed, null, 2)}`);
    Logger.log(`Cell mapping: ${JSON.stringify(cellMapping, null, 2)}`);
    
    return {
      parsedData: parsed,
      cellMapping: cellMapping,
      sourceSheet: sourceSheet,
      rowNumber: rowNumber
    };

  } catch (_error) {
    Logger.log(`Error parsing row data: ${_error}`);
    return null;
  }
}

/**
 * Validate required fields for product creation
 */
export function validateRequiredFields(productData) {
  const requiredFields = [
    'sportName',
    'year',
    'season',
    'dayOfPlay',
    'division',
    'location',
    'leagueStartTime',
    'leagueEndTime',
    'seasonStartDate',
    'seasonEndDate',
    'price',
    'totalInventory'
  ];

  const missingFields = [];
  
  for (const field of requiredFields) {
    const value = getNestedValue(productData, field);
    if (value === null || value === undefined || value === '') {
      missingFields.push(field);
    }
  }

  return {
    isValid: missingFields.length === 0,
    missingFields: missingFields
  };
}

/**
 * Get nested value from object using dot notation
 */
export function getNestedValue(obj, path) {
  return path.split('.').reduce((current, key) => {
    return current && current[key] !== undefined ? current[key] : null;
  }, obj);
}

/**
 * Flatten product data for display and editing
 * Treats {raw, formatted} shaped objects as leaf values (returns the formatted string)
 */
export function flattenProductData(obj, result = {}) {
  for (const key in obj) {
    const val = obj[key];
    if (val !== null && typeof val === 'object' && !Array.isArray(val) && !(val instanceof Date)) {
      // Treat {raw, formatted} objects as leaf values — use formatted for display
      if ('formatted' in val && 'raw' in val) {
        result[key] = val.formatted;
      } else {
        flattenProductData(val, result);
      }
    } else {
      result[key] = val;
    }
  }
  return result;
}

/**
 * Get numbered list of editable fields
 */
export function getEditableFieldsList(productData) {
  const flat = flattenProductData(productData);
  const sportName = flat.sportName;
  let editableFields = getEditableFieldsMeta(sportName);

  // Filter out numberVetSpotsToReleaseAtGoLive if it's not truthy or equals totalInventory
  editableFields = editableFields.filter(field => {
    if (field.key === 'numberVetSpotsToReleaseAtGoLive') {
      const vetSpots = parseInt(flat[field.key]) || 0;
      const totalInv = parseInt(flat.totalInventory) || 0;
      return vetSpots > 0 && vetSpots !== totalInv;
    }
    return true;
  });

  const fields = [];
  for (let i = 0; i < editableFields.length; i++) {
    const field = editableFields[i];
    // offDatesCommaSeparated is the display key but data is stored as offDates array
    let value = flat[field.key];
    if (field.key === 'offDatesCommaSeparated' && (value === null || value === undefined)) {
      const offDatesArr = flat.offDates;
      if (Array.isArray(offDatesArr) && offDatesArr.length > 0) {
        value = offDatesArr.map(d => formatDateMdYY(d)).filter(Boolean).join(', ');
      }
    }
    let displayValue;

    // Handle TBD values specially
    if (value === 'TBD' || (typeof value === 'string' && value.trim().toUpperCase() === 'TBD')) {
      displayValue = 'TBD';
    } else if (value === null || value === undefined || value === '') {
      displayValue = '[Not Found]';
    } else if (field.format === 'price' && value) {
      displayValue = `$${value}`;
    } else if (field.format === 'date') {
      displayValue = formatDateMdYY(value) || '[Not Found]';
    } else if (field.format === 'datetime') {
      displayValue = formatDateTimeMdYYhm(value) || '[Not Found]';
    } else if (field.format === 'time') {
      displayValue = formatTimeForDisplay(value) || '[Not Found]';
    } else {
      displayValue = value;
    }

    fields.push(`${field.name}: ${displayValue}`);
  }

  return fields;
}

/**
 * Return ordered editable fields metadata used for display, validation, and updates
 * Each item: { key, name, format? }
 * format: 'date' | 'datetime' | 'time' | 'price' | undefined
 */
export function getEditableFieldsMeta(sportName) {
  // Core ordered list (indexes are used by UI section slicing)
  const meta = [
    // === BASIC INFO === (0..6)
    { key: 'sportName', name: 'Sport' },
    { key: 'dayOfPlay', name: 'Day' },
    { key: 'division', name: 'Division' },
    { key: 'season', name: 'Season' },
    { key: 'year', name: 'Year' },
    { key: 'levelOfPlay', name: 'Level of Play' },
    { key: 'teamAssignment', name: 'Team Assignment' },
    { key: 'dodgeballBallType', name: 'Dodgeball Ball Type' },

    // === DATES & TIMES (and Types first to preserve legacy slicing) === (7..15)
    { key: 'newPlayerOrientationDateTime', name: 'New Player Orientation Date/Time', format: 'datetime' },
    { key: 'scoutNightDateTime', name: 'Scout Night Date/Time', format: 'datetime' },
    { key: 'openingPartyDate', name: 'Opening Party Date', format: 'date' },
    { key: 'seasonStartDate', name: 'Season Start Date', format: 'date' },
    { key: 'seasonEndDate', name: 'Season End Date', format: 'date' },
    { key: 'alternativeStartTime', name: 'Alternative Start Time (Optional)', format: 'time' },
    { key: 'alternativeEndTime', name: 'Alternative End Time (Optional)', format: 'time' },
    { key: 'offDatesCommaSeparated', name: 'Off Dates, Separated by Comma' },

    // === SPECIAL EVENTS === (16..18)
    { key: 'rainDate', name: 'Rain Date', format: 'date' },
    { key: 'closingPartyDate', name: 'Closing Party Date', format: 'date' },

    // === LOCATION & PRICING === (19..21)
    { key: 'leagueStartTime', name: 'Sport Start Time', format: 'time' },
    { key: 'leagueEndTime', name: 'Sport End Time', format: 'time' },
    { key: 'gameDuration', name: 'Game Duration' },
    { key: 'location', name: 'Location' },
    { key: 'price', name: 'Price', format: 'price' },
    { key: 'leagueContactEmail', name: 'League Contact Email' },
    { key: 'vetStatusDeterminedBy', name: 'Vet Status Determined By' },

    // === REGISTRATION WINDOWS === (22..)
    { key: 'vetRegistrationStartDateTime', name: 'Veteran Registration Start Date/Time', format: 'datetime' },
    { key: 'tnbWtnbRegistrationStartDateTime', name: 'WTNB/BIPOC/TNB Registration Start Date/Time', format: 'datetime' },
    { key: 'openRegistrationStartDateTime', name: 'Open Registration Start Date/Time', format: 'datetime' },
    { key: 'totalInventory', name: 'Total Inventory' },
    { key: 'totalWeeks', name: 'Total Weeks' }
  ];

  // Filter out irrelevant fields for the given sport
  const irrelevant = irrelevantFieldsForSport[sportName] || [];
  return meta.filter(f => irrelevant.indexOf(f.key) === -1);
}

/**
 * Update field value in product data
 */
export function updateFieldValue(productData, fieldNumber, newValue) {
  const flat = flattenProductData(productData);
  const sportName = flat.sportName;
  const meta = getEditableFieldsMeta(sportName);
  const field = meta[fieldNumber - 1];
  
  if (!field) {
    throw new Error(`Invalid field number: ${fieldNumber}`);
  }

  // Update the field in the flattened data
  flat[field.key] = newValue;
  
  // Reconstruct the nested structure
  return reconstructNestedStructure(flat);
}

/**
 * Reconstruct nested structure from flattened data
 */
export function reconstructNestedStructure(flatData) {
  const result = {};
  
  // Basic fields
  result.sportName = flatData.sportName;
  result.year = flatData.year;
  result.season = flatData.season;
  result.dayOfPlay = flatData.dayOfPlay;
  result.location = flatData.location;
  result.price = flatData.price;
  result.totalInventory = flatData.totalInventory;
  result.totalWeeks = flatData.totalWeeks;
  result.leagueContactEmail = flatData.leagueContactEmail;
  result.vetStatusDeterminedBy = flatData.vetStatusDeterminedBy;
  result.gameDuration = flatData.gameDuration;
  
  // Regular season basic details
  result.regularSeasonBasicDetails = {
    year: flatData.year,
    season: flatData.season,
    dayOfPlay: flatData.dayOfPlay,
    division: flatData.division,
    location: flatData.location,
    leagueStartTime: flatData.leagueStartTime,
    leagueEndTime: flatData.leagueEndTime,
    alternativeStartTime: flatData.alternativeStartTime,
    alternativeEndTime: flatData.alternativeEndTime
  };
  
  // Optional league info
  result.optionalLeagueInfo = {
    levelOfPlay: flatData.levelOfPlay,
    teamAssignment: flatData.teamAssignment,
    dodgeballBallType: flatData.dodgeballBallType
  };
  
  // Important dates
  result.importantDates = {
    seasonStartDate: flatData.seasonStartDate,
    seasonEndDate: flatData.seasonEndDate,
    vetRegistrationStartDateTime: flatData.vetRegistrationStartDateTime,
    tnbWtnbRegistrationStartDateTime: flatData.tnbWtnbRegistrationStartDateTime,
    openRegistrationStartDateTime: flatData.openRegistrationStartDateTime,
    newPlayerOrientationDateTime: flatData.newPlayerOrientationDateTime,
    scoutNightDateTime: flatData.scoutNightDateTime,
    openingPartyDate: flatData.openingPartyDate,
    closingPartyDate: flatData.closingPartyDate,
    rainDate: flatData.rainDate,
    offDatesCommaSeparated: flatData.offDatesCommaSeparated
  };
  
  // Inventory info
  result.inventoryInfo = {
    price: flatData.price,
    totalInventory: flatData.totalInventory,
    totalWeeks: flatData.totalWeeks
  };
  
  return result;
}

/**
 * Get enum options for a field, considering sport-specific options
 */
export function getEnumOptionsForField(fieldKey, sportName) {
  if (!fieldKey || !productFieldEnums[fieldKey]) {
    return null;
  }

  const enumValue = productFieldEnums[fieldKey];
  
  // Handle sport-specific enums (like location)
  if (typeof enumValue === 'object' && !Array.isArray(enumValue)) {
    return enumValue[sportName] || null;
  }
  
  // Handle regular arrays
  if (Array.isArray(enumValue)) {
    return enumValue;
  }
  
  return null;
}

/**
 * Validate enum field value, ignoring case, whitespace, and special characters
 * Handles comma-separated values for multi-value fields like 'types'
 */
export function validateEnumValue(fieldKey, value, sportName) {
  const enumOptions = getEnumOptionsForField(fieldKey, sportName);
  if (!enumOptions) {
    return { valid: true }; // No enum to validate against
  }

  // Handle comma-separated values for multi-value fields
  if (fieldKey === 'types') {
    const values = value.toString().split(',').map(v => v.trim()).filter(v => v);
    const normalizedValues = [];
    
    for (const val of values) {
      const normalizedInput = val.toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ').trim();
      let found = false;
      
      for (const option of enumOptions) {
        const normalizedOption = option.toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ').trim();
        if (normalizedInput === normalizedOption) {
          normalizedValues.push(option);
          found = true;
          break;
        }
      }
      
      if (!found) {
        return { 
          valid: false, 
          message: `Invalid value "${val}". Valid options are: ${enumOptions.join(', ')}` 
        };
      }
    }
    
    return { valid: true, normalizedValue: normalizedValues.join(', ') };
  }

  // Single value validation
  const normalizedInput = value.toString().toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ').trim();
  
  // Check against each enum option
  for (const option of enumOptions) {
    const normalizedOption = option.toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ').trim();
    if (normalizedInput === normalizedOption) {
      return { valid: true, normalizedValue: option };
    }
  }
  
  return { 
    valid: false, 
    message: `Invalid value. Valid options are: ${enumOptions.join(', ')}` 
  };
}

/**
 * Validate field input with type-specific validation
 */
export function validateFieldInput(fieldKey, value, productData) {
  try {
    const str = String(value || '').trim();

    // Basic numeric validations
    if (fieldKey === 'price') {
      const n = Number(str);
      if (!Number.isFinite(n) || n < 0) return { ok: false, message: 'Price must be a non-negative number.' };
      return { ok: true, normalizedValue: n };
    }
    if (fieldKey === 'totalInventory') {
      const n = Number(str);
      if (!Number.isInteger(n) || n <= 0) return { ok: false, message: 'Total Inventory must be a positive integer.' };
      return { ok: true, normalizedValue: n };
    }
    if (fieldKey === 'year') {
      const n = Number(str);
      if (!Number.isInteger(n) || n < 2024 || n > 2035) return { ok: false, message: 'Year must be an integer between 2024 and 2035.' };
      return { ok: true, normalizedValue: n };
    }

    // Enum validations using the centralized enum system
    const flat = flattenProductData(productData);
    const sportName = flat.sportName;
    const enumValidation = validateEnumValue(fieldKey, str, sportName);
    if (!enumValidation.valid) {
      return { ok: false, message: enumValidation.message };
    }
    if (enumValidation.normalizedValue) {
      return { ok: true, normalizedValue: enumValidation.normalizedValue };
    }

    // Time validations
    if (fieldKey === 'leagueStartTime' || fieldKey === 'leagueEndTime' || fieldKey === 'alternativeStartTime' || fieldKey === 'alternativeEndTime') {
      if (str.toUpperCase() === 'TBD') return { ok: true, normalizedValue: 'TBD' };
      if (!isTime12h(str)) {
        return { ok: false, message: 'Time must be in the format HH:MM AM/PM (e.g., 8:00 PM).' };
      }
      return { ok: true };
    }

    // Datetime validations
    if (fieldKey === 'vetRegistrationStartDateTime' || fieldKey === 'tnbWtnbRegistrationStartDateTime' || fieldKey === 'openRegistrationStartDateTime' || fieldKey === 'newPlayerOrientationDateTime' || fieldKey === 'scoutNightDateTime') {
      if (str.toUpperCase() === 'TBD') return { ok: true, normalizedValue: 'TBD' };
      if (str === '') return { ok: true, normalizedValue: null };
      if (!isDateTimeAllowed(str)) {
        return { ok: false, message: 'Date/Time must be in MM/DD/YYYY HH:MM AM/PM format or ISO 8601 format.' };
      }
      return { ok: true };
    }

    // Date validations
    if (fieldKey === 'seasonStartDate' || fieldKey === 'seasonEndDate' || fieldKey === 'openingPartyDate' || fieldKey === 'closingPartyDate' || fieldKey === 'rainDate') {
      if (str.toUpperCase() === 'TBD') return { ok: true, normalizedValue: 'TBD' };
      if (str === '') return { ok: true, normalizedValue: null };
      if (!isDateMMDDYYYY(str)) {
        return { ok: false, message: 'Date must be in MM/DD/YYYY format.' };
      }
      return { ok: true };
    }

    // Default validation - just return the string
    return { ok: true, normalizedValue: str };

  } catch (e) {
    return { ok: false, message: 'Unexpected error validating input.' };
  }
}
