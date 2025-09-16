/**
 * Product creation dialog and user interaction functions
 * Handles all UI dialogs, prompts, and user interaction flows
 *
 * @fileoverview User interface for product creation workflow
 * @requires ../helpers/formatValidators.gs
 * @requires ../config/constants.gs
 * @requires ../helpers/normalizers.gs
 */

/**
 * Show confirmation dialog with editable fields
 */
function showProductCreationConfirmationDialog_(productData, unresolvedFields, cellMapping, sourceSheet, rowNumber) {
  const ui = SpreadsheetApp.getUi();

  Logger.log(`showProductCreationConfirmationDialog_ called with productData: ${JSON.stringify(productData, null, 2)}`);
  Logger.log(`Unresolved fields: ${JSON.stringify(unresolvedFields)}`);

  // Check if there are unresolved fields and ask user for confirmation
  if (unresolvedFields && unresolvedFields.length > 0) {
    const errorDisplay = buildErrorDisplay_(productData, unresolvedFields);
    const action = ui.alert(
      '🛍️ Create Shopify Product - Missing Required Fields',
      errorDisplay,
      ui.ButtonSet.OK_CANCEL
    );

    if (action === ui.Button.CANCEL) {
      return null; // User cancelled
    }

    const userAction = action.getResponseText().trim().toLowerCase();
    if (userAction === 'cancel') {
      return null;
    } else if (userAction === 'update') {
      productData = showFieldEditingFlow_(productData, cellMapping, sourceSheet, rowNumber);
      if (!productData) return null; // User cancelled editing
      continue; // Re-validate
    } else {
      ui.alert('Invalid Input', 'Please type "update" or "cancel"', ui.ButtonSet.OK);
      continue;
    }
  }

  // All required fields present - text-based confirmation
  const confirmationDisplay = buildConfirmationDisplay_(productData);
  const action = ui.alert(
    '🛍️ Create Shopify Product - All Parsed Fields',
    confirmationDisplay,
    ui.ButtonSet.OK_CANCEL
  );

  if (action === ui.Button.CANCEL) {
    return null; // User cancelled
  }

  const userAction = action.getResponseText().trim().toLowerCase();
  if (userAction === 'create') {
    return productData; // Ready to create
  } else if (userAction === 'update') {
    productData = showFieldEditingFlow_(productData, cellMapping, sourceSheet, rowNumber);
    if (!productData) return null; // User cancelled editing
    continue; // Re-validate and show confirmation again
  } else {
    ui.alert('Invalid Input', 'Please type "create" or "update"', ui.ButtonSet.OK);
    continue;
  }
}

/**
 * Show field editing flow
 */
function showFieldEditingFlow_(productData, cellMapping, sourceSheet, rowNumber) {
  const ui = SpreadsheetApp.getUi();

  while (true) {
    // Re-canonicalize to ensure keys are in expected nested places, then flatten for display
    const canonical = canonicalizeForDisplay_(productData);
    const editableFields = getEditableFieldsList_(canonical);

    const fieldListText = editableFields.map((field, index) => `${index + 1}. ${field}`).join('\n');

    const fieldResponse = ui.prompt(
      'Edit Field',
      `Select a field to edit (enter the number):\n\n${fieldListText}\n\nType "create" to proceed to creation, or click Cancel to abort.`,
      ui.ButtonSet.OK_CANCEL
    );

    if (fieldResponse.getSelectedButton() !== ui.Button.OK) {
      return null; // User cancelled
    }

    const fieldInput = fieldResponse.getResponseText().trim().toLowerCase();
    if (fieldInput === 'create') {
      return canonical; // Ready to create
    }

    const fieldNumber = parseInt(fieldInput);
    if (isNaN(fieldNumber) || fieldNumber < 1 || fieldNumber > editableFields.length) {
      ui.alert('Invalid Input', 'Please enter a valid field number or "create"', ui.ButtonSet.OK);
      continue;
    }

    // Get current field info
    const flat = flattenProductData_(canonical);
    const sportName = flat.sportName;
    const meta = getEditableFieldsMeta_(sportName);
    const fieldName = meta[fieldNumber - 1] ? meta[fieldNumber - 1].name : `Field #${fieldNumber}`;
    const currentValue = editableFields[fieldNumber - 1].split(': ').slice(1).join(': ');
    const fieldKey = meta[fieldNumber - 1] ? meta[fieldNumber - 1].key : null;

    // Get enum options for this field
    const enumOptions = getEnumOptionsForField_(fieldKey, sportName);
    let enumText = '';
    if (enumOptions) {
      enumText = '\n\nValid options:\n' + enumOptions.join('\n');
      
      // Add multi-value instructions for fields that accept multiple values
      if (fieldKey === 'types') {
        enumText += '\n\nYou can enter multiple values separated by commas (e.g., "Draft, Buddy Sign-up")';
      }
    }
    
    // Add format instructions for specific fields
    let formatText = '';
    if (fieldKey === 'offDatesCommaSeparated') {
      formatText = '\n\nMake sure this is in the format M/D/YY (or leave blank if none)';
    } else if (fieldKey === 'vetRegistrationStartDateTime') {
      formatText = '\n\nLeave blank if no vet registration applies for this season';
    }

    const valueResponse = ui.prompt(
      'Edit Field',
      `Enter new value for ${fieldName}:\n\nCurrent: ${currentValue}${enumText}${formatText}`,
      ui.ButtonSet.OK
    );

    if (valueResponse.getSelectedButton() !== ui.Button.OK) {
      continue; // Back to field selection
    }

    const newValueRaw = valueResponse.getResponseText();
    const newValue = (newValueRaw != null ? newValueRaw.trim() : '');
    if (newValue) {
      try {
        // Validate input before applying
        const fieldKey = meta[fieldNumber - 1] ? meta[fieldNumber - 1].key : undefined;
        const v = validateFieldInput_(fieldKey, newValue, canonical);
        if (!v.ok) {
          ui.alert('Invalid Value', v.message || 'The value is not allowed for this field.', ui.ButtonSet.OK);
          continue;
        }
        const normalizedValue = v.normalizedValue != null ? v.normalizedValue : newValue;
        // Apply update on canonical object and continue loop
        const updated = updateFieldValue_(canonical, fieldNumber, normalizedValue);
        productData = canonicalizeForDisplay_(updated);
        
        // Update the corresponding cell in the source sheet
        updateCellInSourceSheet_(fieldKey, normalizedValue, cellMapping, sourceSheet, rowNumber);
      } catch (error) {
        ui.alert('Error', `Failed to update field: ${error.message}`, ui.ButtonSet.OK);
      }
    }
  }
}

/**
 * Build error display for missing required fields
 */
function buildErrorDisplay_(productData, missingFields) {
  const flat = flattenProductData_(productData);
  const editableFields = getEditableFieldsList_(productData);
  
  let display = 'Cannot create product - the following required fields are missing:\n\n';
  display += editableFields.map((field, index) => `${index + 1}. ${field}`).join('\n');
  display += '\n\nType "update" to edit fields or "cancel" to abort.';
  
  return display;
}

/**
 * Build confirmation display for all parsed fields
 */
function buildConfirmationDisplay_(productData) {
  const flat = flattenProductData_(productData);
  const editableFields = getEditableFieldsList_(productData);
  
  let display = '=== BASIC INFO ===\n';
  display += editableFields.slice(0, 7).join('\n');
  display += '\n\n=== DATES & TIMES ===\n';
  display += editableFields.slice(7, 16).join('\n');
  display += '\n\n=== SPECIAL EVENTS ===\n';
  display += editableFields.slice(16, 19).join('\n');
  display += '\n\n=== LOCATION & PRICING ===\n';
  display += editableFields.slice(19, 22).join('\n');
  display += '\n\n=== REGISTRATION WINDOWS ===\n';
  display += editableFields.slice(22).join('\n');
  display += '\n\nCreate this product in Shopify with the above parsed data?\n\nType "create" to proceed or "update" to edit fields:';
  
  return display;
}

/**
 * Build unresolved fields message
 */
function buildUnresolvedFieldsMessage_(unresolvedFields) {
  return unresolvedFields.map(field => {
    const formattedName = formatFieldNameForUser_(field);
    return `• ${formattedName}`;
  }).join('\n');
}

/**
 * Format field name for user display
 */
function formatFieldNameForUser_(fieldName) {
  // Convert camelCase to Title Case
  return fieldName
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, str => str.toUpperCase())
    .trim();
}
