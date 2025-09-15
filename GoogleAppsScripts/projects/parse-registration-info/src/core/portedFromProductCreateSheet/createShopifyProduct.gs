/**
 * Ported Shopify product creation logic from product-variant-creation
 * This handles creating products and variants directly from parse-registration-info
 *
 * @fileoverview Create Shopify products and variants from parsed registration data
 * @requires ../rowParser.gs
 * @requires ../../shared-utilities/secretsUtils.gs
 * @requires ../../shared-utilities/ShopifyUtils.gs
 */

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

  // Show confirmation dialog with editable fields
  const confirmedData = showProductCreationConfirmationDialog_(parsedData);
  if (!confirmedData) {
    return; // User cancelled
  }

  // Create the product and variants
  try {
    const result = sendProductInfoToBackendForCreation(confirmedData);

    if (result.success) {
      // Write the results back to the sheet
      writeProductCreationResults_(sourceSheet, selectedRow, result);

      ui.alert(`✅ Product created successfully!\n\nProduct URL: ${result.productUrl}\n\nVariants created:\n${result.variantsSummary}`);
    } else {
      ui.alert(`❌ Product creation failed:\n\n${result.error}`);
    }

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
    const unresolved = [];
    const parsed = parseSourceRowEnhanced_(vals, unresolved);

    if (unresolved.length > 0) {
      Logger.log(`Unresolved fields during parsing: ${JSON.stringify(unresolved)}`);
    }

    // Convert to product-variant-creation format
    const productData = convertToProductCreationFormat_(parsed, rowNumber);

    Logger.log(`Parsed product data: ${JSON.stringify(productData, null, 2)}`);
    return productData;

  } catch (error) {
    Logger.log(`Error parsing row data: ${error}`);
    return null;
  }
}

/**
 * Convert parsed data to product-variant-creation format
 */
function convertToProductCreationFormat_(parsed, rowNumber) {
  // Map parsed data to the format expected by product creation logic
  return {
    rowNumber: rowNumber,
    sport: parsed.sport || '',
    day: parsed.day || '',
    sportSubCategory: (parsed.sport && parsed.sport.toLowerCase() === 'dodgeball') ? (parsed.sportSubCategory || '') : 'N/A',
    division: parsed.division || '',
    season: parsed.season || '',
    year: parseInt(parsed.year) || new Date().getFullYear(),
    socialOrAdvanced: parsed.socialOrAdvanced || '',
    types: parsed.types || '',
    newPlayerOrientationDateTime: parsed.newPlayerOrientationDateTime || null,
    scoutNightDateTime: (parsed.sport && parsed.sport.toLowerCase() === 'kickball') ? (parsed.scoutNightDateTime || null) : null,
    openingPartyDate: parsed.openingPartyDate || null,
    seasonStartDate: parsed.seasonStartDate || '',
    seasonEndDate: parsed.seasonEndDate || '',
    offDatesCommaSeparated: parsed.offDatesCommaSeparated || '',
    rainDate: (parsed.sport && parsed.sport.toLowerCase() === 'kickball') ? (parsed.rainDate || null) : null,
    closingPartyDate: parsed.closingPartyDate || null,
    sportStartTime: parsed.sportStartTime || '',
    sportEndTime: parsed.sportEndTime || '',
    alternativeStartTime: parsed.alternativeStartTime || null,
    alternativeEndTime: parsed.alternativeEndTime || null,
    location: parsed.location || '',
    price: parsed.price || 0,
    vetRegistrationStartDateTime: parsed.vetRegistrationStartDateTime || null,
    earlyRegistrationStartDateTime: parsed.earlyRegistrationStartDateTime || null,
    openRegistrationStartDateTime: parsed.openRegistrationStartDateTime || null,
    numOfWeeks: parsed.numOfWeeks || 0,
    totalInventory: parsed.totalInventory || '', // Use empty string for missing data, not default

    // Additional fields for display/editing
    leagueDetails: parsed.notes || '',
    playTimes: parsed.times || '',
    wtnbRegister: parsed.wtnbRegister || '',
    openRegister: parsed.openRegister || ''
  };
}

/**
 * Show confirmation dialog with editable fields
 */
function showProductCreationConfirmationDialog_(productData) {
  const ui = SpreadsheetApp.getUi();

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
        </style>
      </head>
      <body>
        <div class="info">
          <strong>🛍️ Create Shopify Product</strong><br>
          Review and edit the product details below, then click "Create Product" to proceed.
        </div>

        <form id="productForm">
          <div class="field-group">
            <label for="sport">Sport:</label>
            <input type="text" id="sport" name="sport" value="<?= sport ?>" required>
          </div>

          <div class="field-group">
            <label for="day">Day:</label>
            <input type="text" id="day" name="day" value="<?= day ?>" required>
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

  // Set template variables
  Object.keys(productData).forEach(key => {
    htmlTemplate[key] = productData[key] || '';
  });

  const htmlOutput = htmlTemplate.evaluate()
    .setWidth(500)
    .setHeight(700);

  // Use the new interactive prompt with validation and editing
  return showInteractiveProductCreationPrompt_(productData);
}

/**
 * Validate that all required fields are present
 */
function validateRequiredFields_(productData) {
  const requiredFields = [
    { key: 'sport', name: 'Sport' },
    { key: 'day', name: 'Day' },
    { key: 'division', name: 'Division' },
    { key: 'season', name: 'Season' },
    { key: 'year', name: 'Year' },
    { key: 'seasonStartDate', name: 'Season Start Date' },
    { key: 'seasonEndDate', name: 'Season End Date' },
    { key: 'sportStartTime', name: 'Sport Start Time' },
    { key: 'sportEndTime', name: 'Sport End Time' },
    { key: 'location', name: 'Location' },
    { key: 'price', name: 'Price' },
    { key: 'totalInventory', name: 'Total Inventory' },
    { key: 'earlyRegistrationStartDateTime', name: 'Early Registration Start' },
    { key: 'openRegistrationStartDateTime', name: 'Open Registration Start' }
  ];

  const missingFields = [];

  for (const field of requiredFields) {
    const value = productData[field.key];
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
 * Build error display for missing required fields
 */
function buildErrorDisplay_(productData, missingFields) {
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
    `${formatValue(productData.sport, 'Sport')}\n` +
    `${formatValue(productData.day, 'Day')}\n`;

  // Only show sport sub-category for dodgeball
  if (productData.sport && productData.sport.toLowerCase() === 'dodgeball') {
    summary += `${formatValue(productData.sportSubCategory, 'Sport Sub-Category')}\n`;
  }

  summary += `${formatValue(productData.division, 'Division')}\n` +
    `${formatValue(productData.season, 'Season')}\n` +
    `${formatValue(productData.year, 'Year')}\n`;

  // Don't show Social/Advanced for bowling
  if (productData.sport && productData.sport.toLowerCase() !== 'bowling') {
    summary += `${formatValue(productData.socialOrAdvanced, 'Social or Advanced')}\n`;
  }

  summary += `${formatValue(productData.types, 'Type(s)')}\n\n` +

    `=== DATES & TIMES ===\n` +
    `${formatValue(productData.seasonStartDate, 'Season Start Date', 'date')}\n` +
    `${formatValue(productData.seasonEndDate, 'Season End Date', 'date')}\n` +
    `${formatValue(productData.sportStartTime, 'Sport Start Time', 'time')}\n` +
    `${formatValue(productData.sportEndTime, 'Sport End Time', 'time')}\n`;

  // Only show alternative times if they exist
  if (productData.alternativeStartTime) {
    summary += `${formatValue(productData.alternativeStartTime, 'Alternative Start Time', 'time')}\n`;
  }
  if (productData.alternativeEndTime) {
    summary += `${formatValue(productData.alternativeEndTime, 'Alternative End Time', 'time')}\n`;
  }

  summary += `${formatValue(productData.offDatesCommaSeparated, 'Off Dates')}\n\n` +

    `=== SPECIAL EVENTS ===\n`;

  // Don't show New Player Orientation for bowling
  if (productData.sport && productData.sport.toLowerCase() !== 'bowling') {
    summary += `${formatValue(productData.newPlayerOrientationDateTime, 'New Player Orientation', 'datetime')}\n`;
  }

  summary += `${formatValue(productData.openingPartyDate, 'Opening Party Date', 'date')}\n`;

  // Only show Rain Date for kickball
  if (productData.sport && productData.sport.toLowerCase() === 'kickball') {
    summary += `${formatValue(productData.rainDate, 'Rain Date', 'date')}\n`;
  }

  summary += `${formatValue(productData.closingPartyDate, 'Closing Party Date', 'date')}\n\n` +

    `=== LOCATION & PRICING ===\n` +
    `${formatValue(productData.location, 'Location')}\n` +
    `${formatValue(productData.price, 'Price', 'price')}\n` +
    `${formatValue(productData.totalInventory, 'Total Inventory')}\n\n` +

    `=== REGISTRATION WINDOWS ===\n` +
    `${formatValue(productData.vetRegistrationStartDateTime, 'Veteran Registration Start', 'datetime')}\n` +
    `${formatValue(productData.earlyRegistrationStartDateTime, 'Early Registration Start', 'datetime')}\n` +
    `${formatValue(productData.openRegistrationStartDateTime, 'Open Registration Start', 'datetime')}\n\n`;

  return summary;
}

/**
 * Get numbered list of editable fields
 */
function getEditableFieldsList_(productData) {
  const editableFields = [
    { key: 'sport', name: 'Sport', format: 'default' },
    { key: 'day', name: 'Day', format: 'default' },
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
    { key: 'sportStartTime', name: 'Sport Start Time', format: 'time' },
    { key: 'sportEndTime', name: 'Sport End Time', format: 'time' },
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
    'sport', 'day', 'sportSubCategory', 'division', 'season', 'year',
    'socialOrAdvanced', 'types', 'newPlayerOrientationDateTime', 'scoutNightDateTime',
    'openingPartyDate', 'seasonStartDate', 'seasonEndDate', 'alternativeStartTime',
    'alternativeEndTime', 'offDatesCommaSeparated', 'rainDate', 'closingPartyDate',
    'sportStartTime', 'sportEndTime', 'location', 'price', 'vetRegistrationStartDateTime',
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
    `${formatValue(productData.sport, 'Sport')}\n` +
    `${formatValue(productData.day, 'Day')}\n`;

  // Only show sport sub-category for dodgeball
  if (productData.sport && productData.sport.toLowerCase() === 'dodgeball') {
    summary += `${formatValue(productData.sportSubCategory, 'Sport Sub-Category')}\n`;
  }

  summary += `${formatValue(productData.division, 'Division')}\n` +
    `${formatValue(productData.season, 'Season')}\n` +
    `${formatValue(productData.year, 'Year')}\n`;

  // Don't show Social/Advanced for bowling
  if (productData.sport && productData.sport.toLowerCase() !== 'bowling') {
    summary += `${formatValue(productData.socialOrAdvanced, 'Social or Advanced')}\n`;
  }

  summary += `${formatValue(productData.types, 'Type(s)')}\n\n` +

    `=== DATES & TIMES ===\n` +
    `${formatValue(productData.seasonStartDate, 'Season Start Date', 'date')}\n` +
    `${formatValue(productData.seasonEndDate, 'Season End Date', 'date')}\n` +
    `${formatValue(productData.sportStartTime, 'Sport Start Time', 'time')}\n` +
    `${formatValue(productData.sportEndTime, 'Sport End Time', 'time')}\n`;

  // Only show alternative times if they exist
  if (productData.alternativeStartTime) {
    summary += `${formatValue(productData.alternativeStartTime, 'Alternative Start Time', 'time')}\n`;
  }
  if (productData.alternativeEndTime) {
    summary += `${formatValue(productData.alternativeEndTime, 'Alternative End Time', 'time')}\n`;
  }

  summary += `${formatValue(productData.offDatesCommaSeparated, 'Off Dates')}\n\n` +

    `=== SPECIAL EVENTS ===\n`;

  // Don't show New Player Orientation for bowling
  if (productData.sport && productData.sport.toLowerCase() !== 'bowling') {
    summary += `${formatValue(productData.newPlayerOrientationDateTime, 'New Player Orientation', 'datetime')}\n`;
  }

  summary += `${formatValue(productData.openingPartyDate, 'Opening Party Date', 'date')}\n`;

  // Only show Rain Date for kickball
  if (productData.sport && productData.sport.toLowerCase() === 'kickball') {
    summary += `${formatValue(productData.rainDate, 'Rain Date', 'date')}\n`;
  }

  summary += `${formatValue(productData.closingPartyDate, 'Closing Party Date', 'date')}\n\n` +

    `=== LOCATION & PRICING ===\n` +
    `${formatValue(productData.location, 'Location')}\n` +
    `${formatValue(productData.price, 'Price', 'price')}\n` +
    `${formatValue(productData.totalInventory, 'Total Inventory')}\n\n` +

    `=== REGISTRATION WINDOWS ===\n` +
    `${formatValue(productData.vetRegistrationStartDateTime, 'Veteran Registration Start', 'datetime')}\n` +
    `${formatValue(productData.earlyRegistrationStartDateTime, 'Early Registration Start', 'datetime')}\n` +
    `${formatValue(productData.openRegistrationStartDateTime, 'Open Registration Start', 'datetime')}\n\n` +

    `Create this product in Shopify with the above parsed data?`;

  return summary;
}

/**
 * Simple confirmation prompt (fallback for HTML dialog)
 */
function showSimpleConfirmationPrompt_(productData) {
  const ui = SpreadsheetApp.getUi();

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
    `${formatValue(productData.sport, 'Sport')}\n` +
    `${formatValue(productData.day, 'Day')}\n`;

  // Only show sport sub-category for dodgeball
  if (productData.sport && productData.sport.toLowerCase() === 'dodgeball') {
    summary += `${formatValue(productData.sportSubCategory, 'Sport Sub-Category')}\n`;
  }

  summary += `${formatValue(productData.division, 'Division')}\n` +
    `${formatValue(productData.season, 'Season')}\n` +
    `${formatValue(productData.year, 'Year')}\n` +
    `${formatValue(productData.socialOrAdvanced, 'Social or Advanced')}\n` +
    `${formatValue(productData.types, 'Type(s)')}\n\n` +

    `=== DATES & TIMES ===\n` +
    `${formatValue(productData.seasonStartDate, 'Season Start Date', 'date')}\n` +
    `${formatValue(productData.seasonEndDate, 'Season End Date', 'date')}\n` +
    `${formatValue(productData.sportStartTime, 'Sport Start Time', 'time')}\n` +
    `${formatValue(productData.sportEndTime, 'Sport End Time', 'time')}\n`;

  // Only show alternative times if they exist
  if (productData.alternativeStartTime) {
    summary += `${formatValue(productData.alternativeStartTime, 'Alternative Start Time', 'time')}\n`;
  }
  if (productData.alternativeEndTime) {
    summary += `${formatValue(productData.alternativeEndTime, 'Alternative End Time', 'time')}\n`;
  }

  summary += `${formatValue(productData.offDatesCommaSeparated, 'Off Dates')}\n\n` +

    `=== SPECIAL EVENTS ===\n` +
    `${formatValue(productData.newPlayerOrientationDateTime, 'New Player Orientation', 'datetime')}\n`;

  // Only show Scout Night for kickball
  if (productData.sport && productData.sport.toLowerCase() === 'kickball') {
    summary += `${formatValue(productData.scoutNightDateTime, 'Scout Night', 'datetime')}\n`;
  }

  summary += `${formatValue(productData.openingPartyDate, 'Opening Party Date', 'date')}\n`;

  // Only show Rain Date for kickball
  if (productData.sport && productData.sport.toLowerCase() === 'kickball') {
    summary += `${formatValue(productData.rainDate, 'Rain Date', 'date')}\n`;
  }

  summary += `${formatValue(productData.closingPartyDate, 'Closing Party Date', 'date')}\n\n` +

    `=== LOCATION & PRICING ===\n` +
    `${formatValue(productData.location, 'Location')}\n` +
    `${formatValue(productData.price, 'Price', 'price')}\n` +
    `${formatValue(productData.totalInventory, 'Total Inventory')}\n\n` +

    `=== REGISTRATION WINDOWS ===\n` +
    `${formatValue(productData.vetRegistrationStartDateTime, 'Veteran Registration Start', 'datetime')}\n` +
    `${formatValue(productData.earlyRegistrationStartDateTime, 'Early Registration Start', 'datetime')}\n` +
    `${formatValue(productData.openRegistrationStartDateTime, 'Open Registration Start', 'datetime')}\n\n` +

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
