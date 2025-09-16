/**
 * Cell mapping and sheet update functions
 * Handles mapping between parsed fields and their source cells, and updating the sheet
 *
 * @fileoverview Sheet cell mapping and update functionality
 */

/**
 * Create a mapping of field keys to their corresponding cell references
 * This allows us to update the original sheet when fields are edited
 */
function createCellMapping_(sourceSheet, rowNumber, vals) {
  const mapping = {};
  
  // Map each field to its corresponding cell
  // Note: Some fields may come from multi-field cells or require special handling
  
  // Basic field mappings
  mapping.sportName = { column: 'A', row: rowNumber, value: vals.A };
  mapping.dayOfPlay = { column: 'B', row: rowNumber, value: vals.B };
  mapping.division = { column: 'B', row: rowNumber, value: vals.B };
  mapping.season = { column: 'B', row: rowNumber, value: vals.B };
  mapping.year = { column: 'B', row: rowNumber, value: vals.B };
  mapping.socialOrAdvanced = { column: 'B', row: rowNumber, value: vals.B };
  mapping.types = { column: 'B', row: rowNumber, value: vals.B };
  
  // League details (column C contains multiple fields)
  mapping.sportSubCategory = { column: 'C', row: rowNumber, value: vals.C };
  mapping.totalInventory = { column: 'C', row: rowNumber, value: vals.C };
  mapping.numberVetSpotsToReleaseAtGoLive = { column: 'C', row: rowNumber, value: vals.C };
  
  // Season dates
  mapping.seasonStartDate = { column: 'D', row: rowNumber, value: vals.D };
  mapping.seasonEndDate = { column: 'E', row: rowNumber, value: vals.E };
  
  // Price
  mapping.price = { column: 'F', row: rowNumber, value: vals.F };
  
  // Play times (column G contains multiple fields)
  mapping.leagueStartTime = { column: 'G', row: rowNumber, value: vals.G };
  mapping.leagueEndTime = { column: 'G', row: rowNumber, value: vals.G };
  mapping.alternativeStartTime = { column: 'G', row: rowNumber, value: vals.G };
  mapping.alternativeEndTime = { column: 'G', row: rowNumber, value: vals.G };
  
  // Location
  mapping.location = { column: 'H', row: rowNumber, value: vals.H };
  
  // Registration dates
  mapping.earlyRegistrationStartDateTime = { column: 'M', row: rowNumber, value: vals.M };
  mapping.vetRegistrationStartDateTime = { column: 'N', row: rowNumber, value: vals.N };
  mapping.openRegistrationStartDateTime = { column: 'O', row: rowNumber, value: vals.O };
  
  return mapping;
}

/**
 * Update the corresponding cell in the source sheet when a field is edited
 */
function updateCellInSourceSheet_(fieldKey, newValue, cellMapping, sourceSheet, rowNumber) {
  try {
    const cellInfo = cellMapping[fieldKey];
    if (!cellInfo) {
      Logger.log(`No cell mapping found for field: ${fieldKey}`);
      return;
    }

    // For fields that come from multi-field cells (like column B, C, G), we need special handling
    // For now, we'll update the cell directly - in a more sophisticated implementation,
    // we might need to parse and reconstruct the cell content
    const cellRef = `${cellInfo.column}${cellInfo.row}`;
    
    // Handle different field types
    let cellValue = newValue;
    
    if (fieldKey === 'seasonStartDate' || fieldKey === 'seasonEndDate') {
      // Convert Date object to MM/DD/YYYY format for display
      if (newValue instanceof Date) {
        cellValue = formatDateForSheet_(newValue);
      }
    } else if (fieldKey === 'vetRegistrationStartDateTime' || 
               fieldKey === 'earlyRegistrationStartDateTime' || 
               fieldKey === 'openRegistrationStartDateTime') {
      // Convert Date object to MM/DD/YYYY HH:MM AM/PM format for display
      if (newValue instanceof Date) {
        cellValue = formatDateTimeForSheet_(newValue);
      }
    } else if (fieldKey === 'leagueStartTime' || fieldKey === 'leagueEndTime' ||
               fieldKey === 'alternativeStartTime' || fieldKey === 'alternativeEndTime') {
      // Convert time to HH:MM AM/PM format
      if (newValue instanceof Date) {
        cellValue = formatTimeForSheet_(newValue);
      }
    }
    
    // Update the cell
    sourceSheet.getRange(cellRef).setValue(cellValue);
    Logger.log(`Updated cell ${cellRef} with value: ${cellValue} for field: ${fieldKey}`);
    
  } catch (error) {
    Logger.log(`Error updating cell for field ${fieldKey}: ${error.message}`);
  }
}

/**
 * Write product creation results to columns Q-U
 * Q: Product URL
 * R: Vet Registration Variant Id  
 * S: Early Registration Variant Id
 * T: Open Registration Variant Id
 * U: Waitlist Registration Variant Id
 */
function writeProductCreationResults_(sourceSheet, rowNumber, result) {
  try {
    if (!result.success || !result.data) {
      Logger.log('No successful result data to write to sheet');
      return;
    }

    const data = result.data;
    const updates = [];

    // Column Q: Product URL
    if (data.productUrl) {
      updates.push({ column: 'Q', value: data.productUrl });
    }

    // Column R: Vet Registration Variant Id
    if (data.veteranVariantGid) {
      updates.push({ column: 'R', value: data.veteranVariantGid });
    }

    // Column S: Early Registration Variant Id
    if (data.earlyVariantGid) {
      updates.push({ column: 'S', value: data.earlyVariantGid });
    }

    // Column T: Open Registration Variant Id
    if (data.openVariantGid) {
      updates.push({ column: 'T', value: data.openVariantGid });
    }

    // Column U: Waitlist Registration Variant Id
    if (data.waitlistVariantGid) {
      updates.push({ column: 'U', value: data.waitlistVariantGid });
    }

    // Write all updates to the sheet
    for (const update of updates) {
      const cellRef = `${update.column}${rowNumber}`;
      sourceSheet.getRange(cellRef).setValue(update.value);
      Logger.log(`Updated cell ${cellRef} with value: ${update.value}`);
    }

    Logger.log(`Successfully wrote ${updates.length} values to row ${rowNumber}`);

  } catch (error) {
    Logger.log(`Error writing product creation results: ${error.message}`);
  }
}

/**
 * Handle checkbox validation for column P (go-live checkbox)
 * This function should be called from an onEdit trigger
 */
function handleGoLiveCheckboxEdit_(e) {
  const ui = SpreadsheetApp.getUi();
  
  try {
    const range = e.range;
    const sheet = range.getSheet();
    const row = range.getRow();
    const column = range.getColumn();
    
    // Check if this is column P (16th column)
    if (column !== 16) {
      return;
    }
    
    // Check if the checkbox was checked (value is true)
    const isChecked = range.getValue() === true;
    if (!isChecked) {
      return; // Only handle when checkbox is checked
    }
    
    // Check if required columns have values
    const productUrl = sheet.getRange(row, 17).getValue(); // Column Q
    const earlyVariantId = sheet.getRange(row, 19).getValue(); // Column S  
    const openVariantId = sheet.getRange(row, 20).getValue(); // Column T
    
    if (!productUrl || !earlyVariantId || !openVariantId) {
      // Uncheck the checkbox and show error
      range.setValue(false);
      ui.alert('Cannot Schedule Product', 'You cannot schedule a product for publication before it has been created!', ui.ButtonSet.OK);
      return;
    }
    
    // Get registration dates to determine go-live time
    const vetRegistrationDate = sheet.getRange(row, 14).getValue(); // Column N
    const earlyRegistrationDate = sheet.getRange(row, 13).getValue(); // Column M
    
    let goLiveTime;
    let goLiveTimeDisplay;
    
    if (vetRegistrationDate) {
      goLiveTime = vetRegistrationDate;
      goLiveTimeDisplay = formatDateTimeForDisplay_(vetRegistrationDate);
    } else if (earlyRegistrationDate) {
      goLiveTime = earlyRegistrationDate;
      goLiveTimeDisplay = formatDateTimeForDisplay_(earlyRegistrationDate);
    } else {
      // Uncheck the checkbox and show error
      range.setValue(false);
      ui.alert('Cannot Schedule Product', 'No registration start time found. Please set vet or early registration date first.', ui.ButtonSet.OK);
      return;
    }
    
    // Show confirmation dialog
    const confirmResponse = ui.alert(
      'Confirm Product Go-Live',
      `By clicking OK, you will be setting this live at ${goLiveTimeDisplay}\n\nPlease double-check the product page in Shopify to confirm details look correct and validate the automation.`,
      ui.ButtonSet.OK_CANCEL
    );
    
    if (confirmResponse === ui.Button.OK) {
      // Send go-live request to backend
      sendGoLiveRequest_(productUrl, goLiveTime);
    } else {
      // Uncheck the checkbox if user cancelled
      range.setValue(false);
    }
    
  } catch (error) {
    Logger.log(`Error handling go-live checkbox: ${error.message}`);
    // Uncheck the checkbox on error
    if (e.range) {
      e.range.setValue(false);
    }
  }
}
