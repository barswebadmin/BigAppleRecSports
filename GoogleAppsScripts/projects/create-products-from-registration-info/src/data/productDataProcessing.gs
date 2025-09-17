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

/**
 * Parse row data for product creation
 */
function parseRowDataForProductCreation_(sourceSheet, rowNumber) {
  try {
    // Read source row columns A..O (same as migration logic)
    function getFilledDownA_(sheet, row, stopAtRow = 4) {
      for (let r = row; r >= stopAtRow; r--) {
        const v = sheet.getRange(r, 1).getDisplayValue().trim();
        if (v) return v;
      }
      return '';
    }

    const rowValues = sourceSheet.getRange(rowNumber, 1, 1, 21).getDisplayValues()[0]; // Read A to U columns
    const vals = {
      A: getFilledDownA_(sourceSheet, rowNumber), // Sport (merged)
      B: (rowValues[1] || '').toString(), // Day + flags
      C: (rowValues[2] || '').toString(), // League details
      D: (rowValues[3] || '').toString(), // Season start
      E: (rowValues[4] || '').toString(), // Season end
      F: (rowValues[5] || '').toString(), // Price
      G: (rowValues[6] || '').toString(), // Play times
      H: (rowValues[7] || '').toString(), // Location
      // Use correct column mapping (parser expects M=early, N=vet, O=open)
      M: (rowValues[12] || '').toString(), // Early registration (WTNB/BIPOC/TNB register)
      N: (rowValues[13] || '').toString(), // Vet register
      O: (rowValues[14] || '').toString(), // Open register
    };

    // Parse using existing logic
    const parsed = parseSourceRowEnhanced_(vals);

    // Create cell mapping for field updates
    const cellMapping = createCellMapping_(sourceSheet, rowNumber, vals);

    Logger.log(`Parsed product data: ${JSON.stringify(parsed, null, 2)}`);
    Logger.log(`Cell mapping: ${JSON.stringify(cellMapping, null, 2)}`);
    
    return {
      parsedData: parsed,
      cellMapping: cellMapping,
      sourceSheet: sourceSheet,
      rowNumber: rowNumber
    };

  } catch (error) {
    Logger.log(`Error parsing row data: ${error}`);
    return null;
  }
}

/**
 * Validate required fields for product creation
 */
function validateRequiredFields_(productData) {
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
    const value = getNestedValue_(productData, field);
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
function getNestedValue_(obj, path) {
  return path.split('.').reduce((current, key) => {
    return current && current[key] !== undefined ? current[key] : null;
  }, obj);
}

/**
 * Flatten product data for display and editing
 */
function flattenProductData_(obj, result = {}) {
  for (const key in obj) {
    if (obj[key] !== null && typeof obj[key] === 'object' && !Array.isArray(obj[key]) && !(obj[key] instanceof Date)) {
      flattenProductData_(obj[key], result);
    } else {
      result[key] = obj[key];
    }
  }
  return result;
}

/**
 * Get numbered list of editable fields
 */
function getEditableFieldsList_(productData) {
  const flat = flattenProductData_(productData);
  const sportName = flat.sportName;
  let editableFields = getEditableFieldsMeta_(sportName);

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
    const value = flat[field.key];
    let displayValue;

    // Handle TBD values specially
    if (value === 'TBD' || (typeof value === 'string' && value.trim().toUpperCase() === 'TBD')) {
      displayValue = 'TBD';
    } else if (value === null || value === undefined || value === '') {
      displayValue = '[Not Found]';
    } else if (field.format === 'price' && value) {
      displayValue = `$${value}`;
    } else if (field.format === 'date') {
      displayValue = formatDateMdYY_(value) || '[Not Found]';
    } else if (field.format === 'datetime') {
      displayValue = formatDateTimeMdYYhm_(value) || '[Not Found]';
    } else if (field.format === 'time') {
      displayValue = formatTimeForDisplay_(value) || '[Not Found]';
    } else {
      displayValue = value;
    }

    fields.push(`${field.name}: ${displayValue}`);
  }

  return fields;
}

/**
 * Update field value in product data
 */
function updateFieldValue_(productData, fieldNumber, newValue) {
  const flat = flattenProductData_(productData);
  const sportName = flat.sportName;
  const meta = getEditableFieldsMeta_(sportName);
  const field = meta[fieldNumber - 1];
  
  if (!field) {
    throw new Error(`Invalid field number: ${fieldNumber}`);
  }

  // Update the field in the flattened data
  flat[field.key] = newValue;
  
  // Reconstruct the nested structure
  return reconstructNestedStructure_(flat);
}

/**
 * Reconstruct nested structure from flattened data
 */
function reconstructNestedStructure_(flatData) {
  const result = {};
  
  // Basic fields
  result.sportName = flatData.sportName;
  result.year = flatData.year;
  result.season = flatData.season;
  result.dayOfPlay = flatData.dayOfPlay;
  result.location = flatData.location;
  result.price = flatData.price;
  result.totalInventory = flatData.totalInventory;
  result.numberVetSpotsToReleaseAtGoLive = flatData.numberVetSpotsToReleaseAtGoLive;
  
  // Regular season basic details
  result.regularSeasonBasicDetails = {
    year: flatData.year,
    season: flatData.season,
    dayOfPlay: flatData.dayOfPlay,
    division: flatData.division,
    location: flatData.location,
    leagueStartTime: flatData.leagueStartTime,
    leagueEndTime: flatData.leagueEndTime,
    sportSubCategory: flatData.sportSubCategory,
    socialOrAdvanced: flatData.socialOrAdvanced,
    alternativeStartTime: flatData.alternativeStartTime,
    alternativeEndTime: flatData.alternativeEndTime
  };
  
  // Optional league info
  result.optionalLeagueInfo = {
    socialOrAdvanced: flatData.socialOrAdvanced,
    sportSubCategory: flatData.sportSubCategory,
    types: flatData.types ? flatData.types.split(',').map(t => t.trim()) : []
  };
  
  // Important dates
  result.importantDates = {
    seasonStartDate: flatData.seasonStartDate,
    seasonEndDate: flatData.seasonEndDate,
    vetRegistrationStartDateTime: flatData.vetRegistrationStartDateTime,
    earlyRegistrationStartDateTime: flatData.earlyRegistrationStartDateTime,
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
    numberVetSpotsToReleaseAtGoLive: flatData.numberVetSpotsToReleaseAtGoLive
  };
  
  return result;
}

/**
 * Get enum options for a field, considering sport-specific options
 */
function getEnumOptionsForField_(fieldKey, sportName) {
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
function validateEnumValue_(fieldKey, value, sportName) {
  const enumOptions = getEnumOptionsForField_(fieldKey, sportName);
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
function validateFieldInput_(fieldKey, value, productData) {
  try {
    const str = String(value || '').trim();
    const lower = str.toLowerCase();

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
    const flat = flattenProductData_(productData);
    const sportName = flat.sportName;
    const enumValidation = validateEnumValue_(fieldKey, str, sportName);
    if (!enumValidation.valid) {
      return { ok: false, message: enumValidation.message };
    }
    if (enumValidation.normalizedValue) {
      return { ok: true, normalizedValue: enumValidation.normalizedValue };
    }

    // Time validations
    if (fieldKey === 'leagueStartTime' || fieldKey === 'leagueEndTime' || fieldKey === 'alternativeStartTime' || fieldKey === 'alternativeEndTime') {
      if (str.toUpperCase() === 'TBD') return { ok: true, normalizedValue: 'TBD' };
      if (typeof isTime12h_ === 'function' && !isTime12h_(str)) {
        return { ok: false, message: 'Time must be in the format HH:MM AM/PM (e.g., 8:00 PM).' };
      }
      return { ok: true };
    }

    // Datetime validations
    if (fieldKey === 'vetRegistrationStartDateTime' || fieldKey === 'earlyRegistrationStartDateTime' || fieldKey === 'openRegistrationStartDateTime' || fieldKey === 'newPlayerOrientationDateTime' || fieldKey === 'scoutNightDateTime') {
      if (str.toUpperCase() === 'TBD') return { ok: true, normalizedValue: 'TBD' };
      if (str === '') return { ok: true, normalizedValue: null };
      if (typeof isDateTimeAllowed_ === 'function' && !isDateTimeAllowed_(str)) {
        return { ok: false, message: 'Date/Time must be in MM/DD/YYYY HH:MM AM/PM format or ISO 8601 format.' };
      }
      return { ok: true };
    }

    // Date validations
    if (fieldKey === 'seasonStartDate' || fieldKey === 'seasonEndDate' || fieldKey === 'openingPartyDate' || fieldKey === 'closingPartyDate' || fieldKey === 'rainDate') {
      if (str.toUpperCase() === 'TBD') return { ok: true, normalizedValue: 'TBD' };
      if (str === '') return { ok: true, normalizedValue: null };
      if (typeof isDateMMDDYYYY_ === 'function' && !isDateMMDDYYYY_(str)) {
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
