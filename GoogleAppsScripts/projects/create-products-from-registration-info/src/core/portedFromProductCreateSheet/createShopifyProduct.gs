/**
 * Ported Shopify product creation logic from product-variant-creation
 * This handles creating products and variants directly from parse-registration-info
 *
 * @fileoverview Create Shopify products and variants from parsed registration data
 * @requires ../../parsers/_rowParser.gs
 * @requires ../../validators/fieldValidation.gs
 * @requires ../../shared-utilities/secretsUtils.gs
 * @requires ../../shared-utilities/ShopifyUtils.gs
 */

// Import references for editor support
/// <reference path="../../validators/fieldValidation.gs" />

/**
 * Main function to create Shopify product from a row in parse-registration-info
 */

// biome-ignore lint/correctness/noUnusedVariables: <it's called from menu items>
function  createShopifyProductFromRow_(sourceSheet, selectedRow) {
  const ui = SpreadsheetApp.getUi();

  // Read and parse the row data
  const parsedData = parseRowDataForProductCreation_(sourceSheet, selectedRow);
  if (!parsedData) {
    ui.alert('Failed to parse row data for product creation.');
    return;
  }

  const unresolvedFields = calculateUnresolvedFieldsForParsedData(parsedData);

  // After user confirms, we will validate+canonize nested shape; for now keep parsed

  // Show confirmation dialog with editable fields
  Logger.log(`About to show confirmation dialog with product data: ${JSON.stringify(parsedData, null, 2)}`);
  const confirmedData = showProductCreationConfirmationDialog_(parsedData, unresolvedFields);
  if (!confirmedData) {
    return; // User cancelled
  }

  // Create the product and variants
  try {
    // Validate and canonicalize nested request structure just before sending
    const validNested = validProductCreateRequest_(confirmedData);
    Logger.log(`About to send confirmed data to backend (nested): ${JSON.stringify(validNested, null, 2)}`);
    const result = sendProductInfoToBackendForCreation(validNested);

    console.log('done!')

    // if (result.success) {
    //   // Write the results back to the sheet
    //   writeProductCreationResults_(sourceSheet, selectedRow, result);

    //   ui.alert(`✅ Product created successfully!\n\nProduct URL: ${result.productUrl}\n\nVariants created:\n${result.variantsSummary}`);
    // } else {
    //   ui.alert(`❌ Product creation failed:\n\n${result.error}`);
    // }

  } catch (error) {
    Logger.log(`Error in sendProductInfoToBackendForCreation: ${error}`);
    ui.alert(`❌ Unexpected error during product creation:\n\n${error.message}`);
  }
}

/**
 * Parse row data specifically for product creation
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

    Logger.log(`Parsed product data: ${JSON.stringify(parsed, null, 2)}`);
    return parsed;

  } catch (error) {
    Logger.log(`Error parsing row data: ${error}`);
    return null;
  }
}

/**
 * Show confirmation dialog with editable fields
 */
function showProductCreationConfirmationDialog_(productData, unresolvedFields) {
  const ui = SpreadsheetApp.getUi();

  Logger.log(`showProductCreationConfirmationDialog_ called with productData: ${JSON.stringify(productData, null, 2)}`);
  Logger.log(`Unresolved fields: ${JSON.stringify(unresolvedFields)}`);

  // Check if there are unresolved fields and ask user for confirmation
  if (unresolvedFields && unresolvedFields.length > 0) {
    const unresolvedMessage = buildUnresolvedFieldsMessage_(unresolvedFields);
    const proceedAnyway = ui.alert(
      '⚠️ Unresolved Fields Detected',
      unresolvedMessage + '\n\nDo you want to proceed with product creation anyway?',
      ui.ButtonSet.YES_NO
    );

    if (proceedAnyway !== ui.Button.YES) {
      return null; // User chose not to proceed
    }
  }

  // Create an HTML dialog for better UX
  const htmlTemplate = HtmlService.createTemplate(`
    <!DOCTYPE html>
    <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; }
          .field-group { margin-bottom: 15px; }
          label { display: block; font-weight: bold; margin-bottom: 5px; }
          input, select, textarea { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
          textarea { height: 60px; resize: vertical; }
          .buttons { text-align: center; margin-top: 20px; }
          button { margin: 0 10px; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
          .confirm { background-color: #4CAF50; color: white; }
          .cancel { background-color: #f44336; color: white; }
          .info { background-color: #e3f2fd; padding: 10px; border-radius: 4px; margin-bottom: 20px; }
          .warning { background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 4px; margin-bottom: 20px; border-left: 4px solid #ffc107; }
          .unresolved-list { margin: 10px 0; padding-left: 20px; }
        </style>
      </head>
      <body>
        <div class="info">
          <strong>🛍️ Create Shopify Product</strong><br>
          Review and edit the product details below, then click "Create Product" to proceed.
        </div>

        <?= unresolvedWarningHtml ?>


        <form id="productForm">
          <div class="field-group">
            <label for="sportName">Sport:</label>
            <input type="text" id="sportName" name="sportName" value="<?= sportName ?>" required>
          </div>

          <div class="field-group">
            <label for="dayOfPlay">Day:</label>
            <input type="text" id="dayOfPlay" name="dayOfPlay" value="<?= dayOfPlay ?>" required>
          </div>

          <div class="field-group">
            <label for="division">Division:</label>
            <select id="division" name="division" required>
              <option value="Open" <?= division === 'Open' ? 'selected' : '' ?>>Open</option>
              <option value="WTNB+" <?= division === 'WTNB+' ? 'selected' : '' ?>>WTNB+</option>
              <option value="Social" <?= division === 'Social' ? 'selected' : '' ?>>Social</option>
              <option value="Advanced" <?= division === 'Advanced' ? 'selected' : '' ?>>Advanced</option>
            </select>
          </div>

          <div class="field-group">
            <label for="season">Season:</label>
            <select id="season" name="season" required>
              <option value="Spring" <?= season === 'Spring' ? 'selected' : '' ?>>Spring</option>
              <option value="Summer" <?= season === 'Summer' ? 'selected' : '' ?>>Summer</option>
              <option value="Fall" <?= season === 'Fall' ? 'selected' : '' ?>>Fall</option>
              <option value="Winter" <?= season === 'Winter' ? 'selected' : '' ?>>Winter</option>
            </select>
          </div>

          <div class="field-group">
            <label for="year">Year:</label>
            <input type="number" id="year" name="year" value="<?= year ?>" min="2024" max="2030" required>
          </div>

          <div class="field-group">
            <label for="seasonStartDate">Season Start Date:</label>
            <input type="text" id="seasonStartDate" name="seasonStartDate" value="<?= seasonStartDate ?>" placeholder="MM/DD/YYYY" required>
          </div>

          <div class="field-group">
            <label for="seasonEndDate">Season End Date:</label>
            <input type="text" id="seasonEndDate" name="seasonEndDate" value="<?= seasonEndDate ?>" placeholder="MM/DD/YYYY" required>
          </div>

          <div class="field-group">
            <label for="price">Price ($):</label>
            <input type="number" id="price" name="price" value="<?= price ?>" min="0" step="0.01" required>
          </div>

          <div class="field-group">
            <label for="location">Location:</label>
            <input type="text" id="location" name="location" value="<?= location ?>" required>
          </div>

          <div class="field-group">
            <label for="playTimes">Play Times:</label>
            <input type="text" id="playTimes" name="playTimes" value="<?= playTimes ?>" required>
          </div>

          <div class="field-group">
            <label for="leagueDetails">League Details:</label>
            <textarea id="leagueDetails" name="leagueDetails"><?= leagueDetails ?></textarea>
          </div>

          <div class="field-group">
            <label for="totalInventory">Total Inventory:</label>
            <input type="number" id="totalInventory" name="totalInventory" value="<?= totalInventory ?>" min="1" required>
          </div>
        </form>

        <div class="buttons">
          <button type="button" class="confirm" onclick="createProduct()">🛍️ Create Product</button>
          <button type="button" class="cancel" onclick="google.script.host.close()">❌ Cancel</button>
        </div>

        <script>
          function createProduct() {
            const form = document.getElementById('productForm');
            const formData = new FormData(form);
            const data = {};
            for (let [key, value] of formData.entries()) {
              data[key] = value;
            }
            google.script.run
              .withSuccessHandler(() => google.script.host.close())
              .withFailureHandler((error) => alert('Error: ' + error))
              .processProductCreation(data);
          }
        </script>
      </body>
    </html>
  `);

  // Set template variables - flatten nested structure for template access
  const flatData = flattenProductData_(productData);
  Logger.log(`Template flatData: ${JSON.stringify(flatData, null, 2)}`);

  // First set all top-level fields from original productData
  Object.keys(productData).forEach(key => {
    if (typeof productData[key] !== 'object' || productData[key] === null || Array.isArray(productData[key])) {
      htmlTemplate[key] = productData[key] || '';
      Logger.log(`Set top-level template variable ${key}: ${htmlTemplate[key]}`);
    }
  });

  // Then set all flattened nested fields
  Object.keys(flatData).forEach(key => {
    // Only set if not already set from top-level (avoid overwriting)
    if (!(key in htmlTemplate)) {
      htmlTemplate[key] = flatData[key] || '';
      Logger.log(`Set nested template variable ${key}: ${htmlTemplate[key]}`);
    }
  });

  // Add missing template variables that are used in HTML but not in productData
  const leagueStartTime = flatData.leagueStartTime || '';
  const leagueEndTime = flatData.leagueEndTime || '';
  htmlTemplate.playTimes = (leagueStartTime && leagueEndTime) ? `${leagueStartTime} - ${leagueEndTime}` : '';
  htmlTemplate.leagueDetails = 'some details'; // This can be filled manually by user

  // Add unresolved fields warning to template
  if (unresolvedFields && unresolvedFields.length > 0) {
    htmlTemplate.unresolvedWarningHtml = `
      <div class="warning">
        <strong>⚠️ Warning: ${unresolvedFields.length} Unresolved Fields</strong><br>
        The following fields could not be automatically parsed and may need manual entry:
        <ul class="unresolved-list">
          ${unresolvedFields.map(field => `<li>${field}</li>`).join('')}
        </ul>
      </div>`;
  } else {
    htmlTemplate.unresolvedWarningHtml = '';
  }

  const htmlOutput = htmlTemplate.evaluate()
    .setWidth(500)
    .setHeight(700);

  // Use the new interactive prompt with validation and editing
  return showInteractiveProductCreationPrompt_(productData);
}

/**
 * Build a user-friendly message about unresolved fields
 * @param {Array<string>} unresolvedFields - Array of field names that couldn't be parsed
 * @returns {string} Formatted message for the user
 */
function buildUnresolvedFieldsMessage_(unresolvedFields) {
  if (!unresolvedFields || unresolvedFields.length === 0) {
    return '';
  }

  const count = unresolvedFields.length;
  const fieldList = unresolvedFields.map(field => `• ${formatFieldNameForUser_(field)}`).join('\n');

  return `${count} field${count > 1 ? 's' : ''} could not be automatically parsed from the spreadsheet data:\n\n${fieldList}\n\nThese fields may be missing or contain data that couldn't be recognized. You'll need to manually review and complete them during product creation.`;
}

/**
 * Format field names for user-friendly display
 * @param {string} fieldName - Internal field name
 * @returns {string} User-friendly field name
 */
function formatFieldNameForUser_(fieldName) {
  // Convert camelCase to readable format
  const formatted = fieldName
    .replace(/([A-Z])/g, ' $1') // Add space before capital letters
    .replace(/^./, str => str.toUpperCase()) // Capitalize first letter
    .replace(/\bDate\b/g, 'Date') // Ensure Date is capitalized
    .replace(/\bTime\b/g, 'Time') // Ensure Time is capitalized
    .replace(/\bId\b/g, 'ID') // Ensure ID is capitalized
    .trim();

  // Handle specific field mappings for better readability
  const fieldMappings = {
    'Sport Name': 'Sport',
    'Day Of Play': 'Day of Play',
    'Sport Sub Category': 'Sport Sub-Category',
    'Social Or Advanced': 'Social/Advanced Level',
    'New Player Orientation Date Time': 'New Player Orientation',
    'Scout Night Date Time': 'Scout Night',
    'Opening Party Date': 'Opening Party',
    'Season Start Date': 'Season Start',
    'Season End Date': 'Season End',
    'Off Dates': 'Off Dates (Skipped Dates)',
    'Rain Date': 'Rain Date',
    'Closing Party Date': 'Closing Party',
    'Vet Registration Start Date Time': 'Veteran Registration Start',
    'Early Registration Start Date Time': 'Early Registration Start',
    'Open Registration Start Date Time': 'Open Registration Start',
    'League Start Time': 'League Start Time',
    'League End Time': 'League End Time',
    'Alternative Start Time': 'Alternative Start Time',
    'Alternative End Time': 'Alternative End Time',
    'Total Inventory': 'Total Players/Inventory',
    'Number Vet Spots To Release At Go Live': 'Veteran Spots at Go-Live'
  };

  return fieldMappings[formatted] || formatted;
}

/**
 * Validate that all required fields are present
 */
function validateRequiredFields_(productData) {
  const requiredFields = [
    { key: 'sportName', name: 'Sport', path: 'sportName' },
    { key: 'dayOfPlay', name: 'Day', path: 'dayOfPlay' },
    { key: 'division', name: 'Division', path: 'division' },
    { key: 'season', name: 'Season', path: 'season' },
    { key: 'year', name: 'Year', path: 'year' },
    { key: 'seasonStartDate', name: 'Season Start Date', path: 'importantDates.seasonStartDate' },
    { key: 'seasonEndDate', name: 'Season End Date', path: 'importantDates.seasonEndDate' },
    { key: 'leagueStartTime', name: 'League Start Time', path: 'leagueStartTime' },
    { key: 'leagueEndTime', name: 'League End Time', path: 'leagueEndTime' },
    { key: 'location', name: 'Location', path: 'location' },
    { key: 'price', name: 'Price', path: 'inventoryInfo.price' },
    { key: 'totalInventory', name: 'Total Inventory', path: 'inventoryInfo.totalInventory' },
    { key: 'earlyRegistrationStartDateTime', name: 'Early Registration Start', path: 'importantDates.earlyRegistrationStartDateTime' },
    { key: 'openRegistrationStartDateTime', name: 'Open Registration Start', path: 'importantDates.openRegistrationStartDateTime' }
  ];

  const missingFields = [];

  for (const field of requiredFields) {
    const value = getNestedValue_(productData, field.path);
    if (!value || value === '' || value === 0 || (typeof value === 'string' && value.trim() === '')) {
      missingFields.push(field.name);
    }
  }

  return {
    isValid: missingFields.length === 0,
    missingFields: missingFields
  };
}

/**
 * Get nested value from object using dot notation path
 * @param {Object} obj - Object to get value from
 * @param {string} path - Dot notation path (e.g., 'importantDates.seasonStartDate')
 * @returns {*} Value at the path, or undefined if not found
 */
function getNestedValue_(obj, path) {
  if (!obj || !path) return undefined;

  const keys = path.split('.');
  let current = obj;

  for (const key of keys) {
    if (current == null || typeof current !== 'object') {
      return undefined;
    }
    current = current[key];
  }

  return current;
}

/**
 * Recursively flatten nested object for display/validation purposes
 * @param {Object} obj - Object to flatten
 * @param {Object} result - Result object to accumulate flattened keys
 * @returns {Object} Flattened object with all nested fields at top level
 */
function flattenProductData_(obj, result = {}) {
  if (!obj || typeof obj !== 'object') return result;

  for (const key of Object.keys(obj)) {
    const value = obj[key];

    if (value && typeof value === 'object' && !Array.isArray(value) && !(value instanceof Date)) {
      // Recursively flatten nested objects
      flattenProductData_(value, result);
    } else {
      // Add the field to the flattened result
      result[key] = value;
    }
  }

  // Special handling for offDatesCommaSeparated
  if (result.offDates && Array.isArray(result.offDates)) {
    result.offDatesCommaSeparated = result.offDates.join(', ');
  }

  return result;
}

/**
 * Build error display for missing required fields
 */
function buildErrorDisplay_(productData, missingFields) {
  // Flatten the nested data for easier access
  const flatData = flattenProductData_(productData);
  // Helper function to format values for display with specific formatting rules
  function formatValue(value, label, formatType = 'default') {
    // Handle TBD values specially first, before checking for empty
    if (value === 'TBD' || (typeof value === 'string' && value.trim().toUpperCase() === 'TBD')) {
      return `${label}: TBD`;
    }

    if (value === null || value === undefined || value === '') {
      return `${label}: [Not Found]`;
    }

    switch (formatType) {
      case 'price':
        return `${label}: $${value}`;
      case 'time':
        if (value instanceof Date) {
          return `${label}: ${value.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}`;
        } else if (typeof value === 'string' && value.includes(':')) {
          try {
            const [hours, minutes] = value.split(':');
            const hour = parseInt(hours);
            const min = parseInt(minutes);
            const period = hour >= 12 ? 'PM' : 'AM';
            const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
            return `${label}: ${displayHour}:${min.toString().padStart(2, '0')} ${period}`;
          } catch {
            return `${label}: ${value}`;
          }
        }
        return `${label}: ${value}`;
      case 'datetime':
        if (value instanceof Date) {
          return `${label}: ${value.toLocaleDateString('en-US')} ${value.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}`;
        } else if (typeof value === 'string' && value.trim()) {
          return `${label}: ${value}`;
        }
        return `${label}: [Not Found]`;
      case 'date':
        if (value instanceof Date) {
          return `${label}: ${value.toLocaleDateString('en-US')}`;
        }
        return `${label}: ${value}`;
      default:
        if (value instanceof Date) {
          return `${label}: ${value.toLocaleDateString('en-US')}`;
        }
        return `${label}: ${value}`;
    }
  }

  let summary = `Cannot Create Shopify Product - Not all Required Fields are Present. Parsed Info Found:\n\n` +
    `=== BASIC INFO ===\n` +
    `${formatValue(flatData.sportName, 'Sport')}\n` +
    `${formatValue(flatData.dayOfPlay, 'Day')}\n`;

  // Only show sport sub-category for dodgeball
  if (flatData.sportName && flatData.sportName.toLowerCase() === 'dodgeball') {
    summary += `${formatValue(flatData.sportSubCategory, 'Sport Sub-Category')}\n`;
  }

  summary += `${formatValue(flatData.division, 'Division')}\n` +
    `${formatValue(flatData.season, 'Season')}\n` +
    `${formatValue(flatData.year, 'Year')}\n`;

  // Don't show Social/Advanced for bowling
  if (flatData.sportName && flatData.sportName.toLowerCase() !== 'bowling') {
    summary += `${formatValue(flatData.socialOrAdvanced, 'Social or Advanced')}\n`;
  }

  summary += `${formatValue(flatData.types, 'Type(s)')}\n\n` +

    `=== DATES & TIMES ===\n` +
    `${formatValue(flatData.seasonStartDate, 'Season Start Date', 'date')}\n` +
    `${formatValue(flatData.seasonEndDate, 'Season End Date', 'date')}\n` +
    `${formatValue(flatData.sportNameStartTime, 'Sport Start Time', 'time')}\n` +
    `${formatValue(flatData.sportNameEndTime, 'Sport End Time', 'time')}\n`;

  // Only show alternative times if they exist
  if (flatData.alternativeStartTime) {
    summary += `${formatValue(flatData.alternativeStartTime, 'Alternative Start Time', 'time')}\n`;
  }
  if (flatData.alternativeEndTime) {
    summary += `${formatValue(flatData.alternativeEndTime, 'Alternative End Time', 'time')}\n`;
  }

  summary += `${formatValue(flatData.offDatesCommaSeparated, 'Off Dates')}\n\n` +

    `=== SPECIAL EVENTS ===\n`;

  // Don't show New Player Orientation for bowling
  if (flatData.sportName && flatData.sportName.toLowerCase() !== 'bowling') {
    summary += `${formatValue(flatData.newPlayerOrientationDateTime, 'New Player Orientation', 'datetime')}\n`;
  }

  summary += `${formatValue(flatData.openingPartyDate, 'Opening Party Date', 'date')}\n`;

  // Only show Rain Date for kickball
  if (flatData.sportName && flatData.sportName.toLowerCase() === 'kickball') {
    summary += `${formatValue(flatData.rainDate, 'Rain Date', 'date')}\n`;
  }

  summary += `${formatValue(flatData.closingPartyDate, 'Closing Party Date', 'date')}\n\n` +

    `=== LOCATION & PRICING ===\n` +
    `${formatValue(flatData.location, 'Location')}\n` +
    `${formatValue(flatData.price, 'Price', 'price')}\n` +
    `${formatValue(flatData.totalInventory, 'Total Inventory')}\n\n` +

    `=== REGISTRATION WINDOWS ===\n` +
    `${formatValue(flatData.vetRegistrationStartDateTime, 'Veteran Registration Start', 'datetime')}\n` +
    `${formatValue(flatData.earlyRegistrationStartDateTime, 'Early Registration Start', 'datetime')}\n` +
    `${formatValue(flatData.openRegistrationStartDateTime, 'Open Registration Start', 'datetime')}\n\n`;

  return summary;
}

/**
 * Get numbered list of editable fields
 */
function getEditableFieldsList_(productData) {
  const editableFields = [
    { key: 'sportName', name: 'Sport', format: 'default' },
    { key: 'dayOfPlay', name: 'Day', format: 'default' },
    { key: 'sportSubCategory', name: 'Sport Sub-Category', format: 'default' },
    { key: 'division', name: 'Division', format: 'default' },
    { key: 'season', name: 'Season', format: 'default' },
    { key: 'year', name: 'Year', format: 'default' },
    { key: 'socialOrAdvanced', name: 'Social or Advanced', format: 'default' },
    { key: 'types', name: 'Type(s)', format: 'default' },
    { key: 'newPlayerOrientationDateTime', name: 'New Player Orientation Date/Time', format: 'datetime' },
    { key: 'scoutNightDateTime', name: 'Scout Night Date/Time', format: 'datetime' },
    { key: 'openingPartyDate', name: 'Opening Party Date', format: 'date' },
    { key: 'seasonStartDate', name: 'Season Start Date', format: 'date' },
    { key: 'seasonEndDate', name: 'Season End Date', format: 'date' },
    { key: 'alternativeStartTime', name: 'Alternative Start Time\n(Optional)', format: 'time' },
    { key: 'alternativeEndTime', name: 'Alternative End Time\n(Optional)', format: 'time' },
    { key: 'offDatesCommaSeparated', name: 'Off Dates, Separated by Comma (Leave Blank if None)\n\nMake Sure This is in the Format M/D/YY', format: 'default' },
    { key: 'rainDate', name: 'Rain Date', format: 'date' },
    { key: 'closingPartyDate', name: 'Closing Party Date', format: 'date' },
    { key: 'leagueStartTime', name: 'Sport Start Time', format: 'time' },
    { key: 'leagueEndTime', name: 'Sport End Time', format: 'time' },
    { key: 'location', name: 'Location', format: 'default' },
    { key: 'price', name: 'Price', format: 'price' },
    { key: 'vetRegistrationStartDateTime', name: 'Veteran Registration Start Date/Time\n(Leave Blank if No Vet Registration Applies for This Season)', format: 'datetime' },
    { key: 'earlyRegistrationStartDateTime', name: 'Early Registration Start Date/Time', format: 'datetime' },
    { key: 'openRegistrationStartDateTime', name: 'Open Registration Start Date/Time', format: 'datetime' },
    { key: 'totalInventory', name: 'Total Inventory', format: 'default' }
  ];

  const fields = [];
  for (let i = 0; i < editableFields.length; i++) {
    const field = editableFields[i];
    const value = productData[field.key];
    let displayValue;

    // Handle TBD values specially
    if (value === 'TBD' || (typeof value === 'string' && value.trim().toUpperCase() === 'TBD')) {
      displayValue = 'TBD';
    } else if (value === null || value === undefined || value === '') {
      displayValue = '[Not Found]';
    } else if (field.format === 'price' && value) {
      displayValue = `$${value}`;
    } else {
      displayValue = value.toString();
    }

    fields.push(`${i + 1}. ${field.name}: ${displayValue}`);
  }

  return fields;
}

/**
 * Update a specific field value
 */
function updateFieldValue_(productData, fieldNumber, newValue) {
  const editableFields = [
    'sportName', 'dayOfPlay', 'sportSubCategory', 'division', 'season', 'year',
    'socialOrAdvanced', 'types', 'newPlayerOrientationDateTime', 'scoutNightDateTime',
    'openingPartyDate', 'seasonStartDate', 'seasonEndDate', 'alternativeStartTime',
    'alternativeEndTime', 'offDatesCommaSeparated', 'rainDate', 'closingPartyDate',
    'leagueStartTime', 'leagueEndTime', 'location', 'price', 'vetRegistrationStartDateTime',
    'earlyRegistrationStartDateTime', 'openRegistrationStartDateTime', 'totalInventory'
  ];

  if (fieldNumber < 1 || fieldNumber > editableFields.length) {
    throw new Error(`Invalid field number: ${fieldNumber}`);
  }

  const fieldKey = editableFields[fieldNumber - 1];
  const updated = { ...productData };

  // Handle special parsing for certain field types
  if (fieldKey === 'price' || fieldKey === 'totalInventory' || fieldKey === 'year') {
    updated[fieldKey] = parseInt(newValue) || 0;
  } else {
    updated[fieldKey] = newValue;
  }

  return updated;
}

/**
 * Interactive product creation flow with validation and editing
 */
function showInteractiveProductCreationPrompt_(productData) {
  const ui = SpreadsheetApp.getUi();

  while (true) {
    const validation = validateRequiredFields_(productData);

    if (!validation.isValid) {
      // Show error display
      const errorDisplay = buildErrorDisplay_(productData, validation.missingFields);
      ui.alert('Missing Required Fields', errorDisplay, ui.ButtonSet.OK);

      // Ask user what to do
      const action = ui.prompt(
        'Product Creation',
        'Required fields are missing. Type "update" to edit fields or "cancel" to abort:',
        ui.ButtonSet.OK_CANCEL
      );

      if (action.getSelectedButton() !== ui.Button.OK) {
        return null; // User cancelled
      }

      const userAction = action.getResponseText().trim().toLowerCase();
      if (userAction === 'cancel') {
        return null;
      } else if (userAction === 'update') {
        productData = showFieldEditingFlow_(productData);
        if (!productData) return null; // User cancelled editing
        continue; // Re-validate
      } else {
        ui.alert('Invalid Input', 'Please type "update" or "cancel"', ui.ButtonSet.OK);
        continue;
      }
    }

    // All required fields present - show confirmation
    const confirmDisplay = buildConfirmationDisplay_(productData);
    const action = ui.prompt(
      'Confirm Product Creation',
      confirmDisplay + '\n\nType "create" to proceed or "update" to edit fields:',
      ui.ButtonSet.OK_CANCEL
    );

    if (action.getSelectedButton() !== ui.Button.OK) {
      return null; // User cancelled
    }

    const userAction = action.getResponseText().trim().toLowerCase();
    if (userAction === 'create') {
      return productData; // Ready to create
    } else if (userAction === 'update') {
      productData = showFieldEditingFlow_(productData);
      if (!productData) return null; // User cancelled editing
      continue; // Re-validate and show confirmation again
    } else {
      ui.alert('Invalid Input', 'Please type "create" or "update"', ui.ButtonSet.OK);
      continue;
    }
  }
}

/**
 * Show field editing flow
 */
function showFieldEditingFlow_(productData) {
  const ui = SpreadsheetApp.getUi();

  while (true) {
    const editableFields = getEditableFieldsList_(productData);
    const fieldsList = editableFields.join('\n');

    const fieldResponse = ui.prompt(
      'Edit Fields',
      `Select a field to edit (enter the number):\n\n${fieldsList}\n\nOr type "done" to finish editing:`,
      ui.ButtonSet.OK_CANCEL
    );

    if (fieldResponse.getSelectedButton() !== ui.Button.OK) {
      return null; // User cancelled
    }

    const input = fieldResponse.getResponseText().trim();
    if (input.toLowerCase() === 'done') {
      return productData;
    }

    const fieldNumber = parseInt(input);
    if (isNaN(fieldNumber) || fieldNumber < 1 || fieldNumber > editableFields.length) {
      ui.alert('Invalid Input', 'Please enter a valid field number or "done"', ui.ButtonSet.OK);
      continue;
    }

    // Get current field info
    const fieldNames = [
      'Sport', 'Day', 'Division', 'Season', 'Year', 'Social or Advanced', 'Type(s)',
      'Season Start Date', 'Season End Date', 'Sport Start Time', 'Sport End Time',
      'Location', 'Price', 'Total Inventory', 'Veteran Registration Start',
      'Early Registration Start', 'Open Registration Start'
    ];

    const fieldName = fieldNames[fieldNumber - 1];
    const currentValue = editableFields[fieldNumber - 1].split(': ')[1];

    const valueResponse = ui.prompt(
      'Edit Field',
      `Enter new value for ${fieldName}:\n\nCurrent: ${currentValue}`,
      ui.ButtonSet.OK_CANCEL
    );

    if (valueResponse.getSelectedButton() !== ui.Button.OK) {
      continue; // Back to field selection
    }

    const newValue = valueResponse.getResponseText().trim();
    if (newValue) {
      try {
        productData = updateFieldValue_(productData, fieldNumber, newValue);
        ui.alert('Success', `Updated ${fieldName} to: ${newValue}`, ui.ButtonSet.OK);
      } catch (error) {
        ui.alert('Error', `Failed to update field: ${error.message}`, ui.ButtonSet.OK);
      }
    }
  }
}

/**
 * Build confirmation display (same as before but extracted as separate function)
 */
function buildConfirmationDisplay_(productData) {
  // Flatten the nested data for easier access
  const flatData = flattenProductData_(productData);
  // Helper function to format values for display with specific formatting rules
  function formatValue(value, label, formatType = 'default') {
    // Handle TBD values specially first, before checking for empty
    if (value === 'TBD' || (typeof value === 'string' && value.trim().toUpperCase() === 'TBD')) {
      return `${label}: TBD`;
    }

    if (value === null || value === undefined || value === '') {
      return `${label}: (empty)`;
    }

    switch (formatType) {
      case 'price':
        return `${label}: $${value}`;
      case 'time':
        if (value instanceof Date) {
          return `${label}: ${value.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}`;
        } else if (typeof value === 'string' && value.includes(':')) {
          try {
            const [hours, minutes] = value.split(':');
            const hour = parseInt(hours);
            const min = parseInt(minutes);
            const period = hour >= 12 ? 'PM' : 'AM';
            const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
            return `${label}: ${displayHour}:${min.toString().padStart(2, '0')} ${period}`;
          } catch {
            return `${label}: ${value}`;
          }
        }
        return `${label}: ${value}`;
      case 'datetime':
        if (value instanceof Date) {
          return `${label}: ${value.toLocaleDateString('en-US')} ${value.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}`;
        } else if (typeof value === 'string' && value.trim()) {
          return `${label}: ${value}`;
        }
        return `${label}: (empty)`;
      case 'date':
        if (value instanceof Date) {
          return `${label}: ${value.toLocaleDateString('en-US')}`;
        }
        return `${label}: ${value}`;
      default:
        if (value instanceof Date) {
          return `${label}: ${value.toLocaleDateString('en-US')}`;
        }
        return `${label}: ${value}`;
    }
  }

  // Only show fields that should be displayed based on sport type and presence
  let summary = `🛍️ Create Shopify Product - All Parsed Fields\n\n` +
    `=== BASIC INFO ===\n` +
    `${formatValue(flatData.sportName, 'Sport')}\n` +
    `${formatValue(flatData.dayOfPlay, 'Day')}\n`;

  // Only show sport sub-category for dodgeball
  if (flatData.sportName && flatData.sportName.toLowerCase() === 'dodgeball') {
    summary += `${formatValue(flatData.sportNameSubCategory, 'Sport Sub-Category')}\n`;
  }

  summary += `${formatValue(flatData.division, 'Division')}\n` +
    `${formatValue(flatData.season, 'Season')}\n` +
    `${formatValue(flatData.year, 'Year')}\n`;

  // Don't show Social/Advanced for bowling
  if (flatData.sportName && flatData.sportName.toLowerCase() !== 'bowling') {
    summary += `${formatValue(flatData.socialOrAdvanced, 'Social or Advanced')}\n`;
  }

  summary += `${formatValue(flatData.types, 'Type(s)')}\n\n` +

    `=== DATES & TIMES ===\n` +
    `${formatValue(flatData.seasonStartDate, 'Season Start Date', 'date')}\n` +
    `${formatValue(flatData.seasonEndDate, 'Season End Date', 'date')}\n` +
    `${formatValue(flatData.sportNameStartTime, 'Sport Start Time', 'time')}\n` +
    `${formatValue(flatData.sportNameEndTime, 'Sport End Time', 'time')}\n`;

  // Only show alternative times if they exist
  if (flatData.alternativeStartTime) {
    summary += `${formatValue(flatData.alternativeStartTime, 'Alternative Start Time', 'time')}\n`;
  }
  if (flatData.alternativeEndTime) {
    summary += `${formatValue(flatData.alternativeEndTime, 'Alternative End Time', 'time')}\n`;
  }

  summary += `${formatValue(flatData.offDatesCommaSeparated, 'Off Dates')}\n\n` +

    `=== SPECIAL EVENTS ===\n`;

  // Don't show New Player Orientation for bowling
  if (flatData.sportName && flatData.sportName.toLowerCase() !== 'bowling') {
    summary += `${formatValue(flatData.newPlayerOrientationDateTime, 'New Player Orientation', 'datetime')}\n`;
  }

  summary += `${formatValue(flatData.openingPartyDate, 'Opening Party Date', 'date')}\n`;

  // Only show Rain Date for kickball
  if (flatData.sportName && flatData.sportName.toLowerCase() === 'kickball') {
    summary += `${formatValue(flatData.rainDate, 'Rain Date', 'date')}\n`;
  }

  summary += `${formatValue(flatData.closingPartyDate, 'Closing Party Date', 'date')}\n\n` +

    `=== LOCATION & PRICING ===\n` +
    `${formatValue(flatData.location, 'Location')}\n` +
    `${formatValue(flatData.price, 'Price', 'price')}\n` +
    `${formatValue(flatData.totalInventory, 'Total Inventory')}\n\n` +

    `=== REGISTRATION WINDOWS ===\n` +
    `${formatValue(flatData.vetRegistrationStartDateTime, 'Veteran Registration Start', 'datetime')}\n` +
    `${formatValue(flatData.earlyRegistrationStartDateTime, 'Early Registration Start', 'datetime')}\n` +
    `${formatValue(flatData.openRegistrationStartDateTime, 'Open Registration Start', 'datetime')}\n\n` +

    `Create this product in Shopify with the above parsed data?`;

  return summary;
}

/**
 * Simple confirmation prompt (fallback for HTML dialog)
 */
function showSimpleConfirmationPrompt_(productData) {
  const ui = SpreadsheetApp.getUi();

  // Flatten the nested data for easier access
  const flatData = flattenProductData_(productData);

  // Helper function to format values for display with specific formatting rules
  function formatValue(value, label, formatType = 'default') {
    // Handle TBD values specially first, before checking for empty
    if (value === 'TBD' || (typeof value === 'string' && value.trim().toUpperCase() === 'TBD')) {
      return `${label}: TBD`;
    }

    if (value === null || value === undefined || value === '') {
      return `${label}: (empty)`;
    }

    switch (formatType) {
      case 'price':
        return `${label}: $${value}`;
      case 'time':
        if (value instanceof Date) {
          return `${label}: ${value.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}`;
        } else if (typeof value === 'string' && value.includes(':')) {
          // Try to parse time string
          try {
            const [hours, minutes] = value.split(':');
            const hour = parseInt(hours);
            const min = parseInt(minutes);
            const period = hour >= 12 ? 'PM' : 'AM';
            const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
            return `${label}: ${displayHour}:${min.toString().padStart(2, '0')} ${period}`;
          } catch {
            return `${label}: ${value}`;
          }
        }
        return `${label}: ${value}`;
      case 'datetime':
        if (value instanceof Date) {
          return `${label}: ${value.toLocaleDateString('en-US')} ${value.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}`;
        } else if (typeof value === 'string' && value.trim()) {
          return `${label}: ${value}`;
        }
        return `${label}: (empty)`;
      case 'date':
        if (value instanceof Date) {
          return `${label}: ${value.toLocaleDateString('en-US')}`;
        }
        return `${label}: ${value}`;
      default:
        if (value instanceof Date) {
          return `${label}: ${value.toLocaleDateString('en-US')}`;
        }
        return `${label}: ${value}`;
    }
  }

  // Only show fields that should be displayed based on sport type and presence
  let summary = `🛍️ Create Shopify Product - All Parsed Fields\n\n` +
    `=== BASIC INFO ===\n` +
    `${formatValue(flatData.sportName, 'Sport')}\n` +
    `${formatValue(flatData.dayOfPlay, 'Day')}\n`;

  // Only show sport sub-category for dodgeball
  if (flatData.sportName && flatData.sportName.toLowerCase() === 'dodgeball') {
    summary += `${formatValue(flatData.sportNameSubCategory, 'Sport Sub-Category')}\n`;
  }

  summary += `${formatValue(flatData.division, 'Division')}\n` +
    `${formatValue(flatData.season, 'Season')}\n` +
    `${formatValue(flatData.year, 'Year')}\n` +
    `${formatValue(flatData.socialOrAdvanced, 'Social or Advanced')}\n` +
    `${formatValue(flatData.types, 'Type(s)')}\n\n` +

    `=== DATES & TIMES ===\n` +
    `${formatValue(flatData.seasonStartDate, 'Season Start Date', 'date')}\n` +
    `${formatValue(flatData.seasonEndDate, 'Season End Date', 'date')}\n` +
    `${formatValue(flatData.sportNameStartTime, 'Sport Start Time', 'time')}\n` +
    `${formatValue(flatData.sportNameEndTime, 'Sport End Time', 'time')}\n`;

  // Only show alternative times if they exist
  if (flatData.alternativeStartTime) {
    summary += `${formatValue(flatData.alternativeStartTime, 'Alternative Start Time', 'time')}\n`;
  }
  if (flatData.alternativeEndTime) {
    summary += `${formatValue(flatData.alternativeEndTime, 'Alternative End Time', 'time')}\n`;
  }

  summary += `${formatValue(flatData.offDatesCommaSeparated, 'Off Dates')}\n\n` +

    `=== SPECIAL EVENTS ===\n` +
    `${formatValue(flatData.newPlayerOrientationDateTime, 'New Player Orientation', 'datetime')}\n`;

  // Only show Scout Night for kickball
  if (flatData.sportName && flatData.sportName.toLowerCase() === 'kickball') {
    summary += `${formatValue(flatData.scoutNightDateTime, 'Scout Night', 'datetime')}\n`;
  }

  summary += `${formatValue(flatData.openingPartyDate, 'Opening Party Date', 'date')}\n`;

  // Only show Rain Date for kickball
  if (flatData.sportName && flatData.sportName.toLowerCase() === 'kickball') {
    summary += `${formatValue(flatData.rainDate, 'Rain Date', 'date')}\n`;
  }

  summary += `${formatValue(flatData.closingPartyDate, 'Closing Party Date', 'date')}\n\n` +

    `=== LOCATION & PRICING ===\n` +
    `${formatValue(flatData.location, 'Location')}\n` +
    `${formatValue(flatData.price, 'Price', 'price')}\n` +
    `${formatValue(flatData.totalInventory, 'Total Inventory')}\n\n` +

    `=== REGISTRATION WINDOWS ===\n` +
    `${formatValue(flatData.vetRegistrationStartDateTime, 'Veteran Registration Start', 'datetime')}\n` +
    `${formatValue(flatData.earlyRegistrationStartDateTime, 'Early Registration Start', 'datetime')}\n` +
    `${formatValue(flatData.openRegistrationStartDateTime, 'Open Registration Start', 'datetime')}\n\n` +

    `Create this product in Shopify with the above parsed data?`;

  const response = ui.alert('Confirm Product Creation', summary, ui.ButtonSet.YES_NO);

  if (response === ui.Button.YES) {
    return productData; // Return the original data for now
  } else {
    return null; // User cancelled
  }
}

/**
 * Create the Shopify product and variants
 */
// createShopifyProductAndVariants_ removed - now calling sendProductInfoToBackendForCreation directly

/**
 * Write product creation results back to the sheet
 */
function writeProductCreationResults_(sourceSheet, rowNumber, result) {
  try {
    // Write to columns Q, R, S, T, U
    const productUrlCol = 17; // Q
    const vetVariantCol = 18; // R
    const earlyVariantCol = 19; // S
    const openVariantCol = 20; // T
    const waitlistVariantCol = 21; // U

    // Write Product URL (Q)
    if (result.productUrl) {
      sourceSheet.getRange(rowNumber, productUrlCol).setFormula(`=HYPERLINK("${result.productUrl}", "${result.productUrl}")`);
    }

    // Write Variant IDs (R, S, T, U)
    if (result.variants) {
      if (result.variants.vet) {
        sourceSheet.getRange(rowNumber, vetVariantCol).setValue(result.variants.vet);
      }
      if (result.variants.early) {
        sourceSheet.getRange(rowNumber, earlyVariantCol).setValue(result.variants.early);
      }
      if (result.variants.open) {
        sourceSheet.getRange(rowNumber, openVariantCol).setValue(result.variants.open);
      }
      if (result.variants.waitlist) {
        sourceSheet.getRange(rowNumber, waitlistVariantCol).setValue(result.variants.waitlist);
      }
    }

    Logger.log(`Successfully wrote product creation results to row ${rowNumber}`);

  } catch (error) {
    Logger.log(`Error writing results to sheet: ${error}`);
    throw error;
  }
}
