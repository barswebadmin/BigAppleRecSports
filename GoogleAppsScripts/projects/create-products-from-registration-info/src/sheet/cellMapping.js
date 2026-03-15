/**
 * Cell mapping and sheet update functions
 * Handles mapping between parsed fields and their source cells, and updating the sheet
 *
 * @fileoverview Sheet cell mapping and update functionality
 */

import { formatDateForSheet, formatDateTimeForSheet, formatTimeForSheet, formatDateTimeForDisplay } from '../utils/formatting.js';

/**
 * Stub for go-live request — legacy backend integration not active.
 * Logs the intent without making an API call.
 */
function sendGoLiveRequest(productUrl, goLiveTime) {
  Logger.log(`[sendGoLiveRequest stub] productUrl=${productUrl}, goLiveTime=${goLiveTime}`);
  SpreadsheetApp.getUi().alert('Go-Live Scheduled', `Product go-live request logged for: ${productUrl}`, SpreadsheetApp.getUi().ButtonSet.OK);
}

/**
 * Create a mapping of field keys to their corresponding cell references
 * This allows us to update the original sheet when fields are edited
 */
export function createCellMapping(sourceSheet, rowNumber, vals) {
  const mapping = {};
  
  // Map each field to its corresponding cell
  // Note: Some fields may come from multi-field cells or require special handling
  
  // Basic field mappings
  mapping.dayOfPlay = { column: 'A', row: rowNumber, value: vals.A };
  mapping.division = { column: 'A', row: rowNumber, value: vals.A };
  mapping.levelOfPlay = { column: 'A', row: rowNumber, value: vals.A };
  mapping.teamAssignment = { column: 'A', row: rowNumber, value: vals.A };
  mapping.types = { column: 'A', row: rowNumber, value: vals.A };
  
  // League details (column B contains multiple fields)
  mapping.totalInventory = { column: 'B', row: rowNumber, value: vals.B };
  mapping.numberVetSpotsToReleaseAtGoLive = { column: 'B', row: rowNumber, value: vals.B };
  
  // Season dates
  mapping.seasonStartDate = { column: 'C', row: rowNumber, value: vals.C };
  mapping.seasonEndDate = { column: 'D', row: rowNumber, value: vals.D };
  
  // Price
  mapping.price = { column: 'E', row: rowNumber, value: vals.E };
  
  // Play times (column F contains multiple fields)
  mapping.leagueStartTime = { column: 'F', row: rowNumber, value: vals.F };
  mapping.leagueEndTime = { column: 'F', row: rowNumber, value: vals.F };
  mapping.alternativeStartTime = { column: 'F', row: rowNumber, value: vals.F };
  mapping.alternativeEndTime = { column: 'F', row: rowNumber, value: vals.F };
  
  // Location
  mapping.location = { column: 'G', row: rowNumber, value: vals.G };
  
  // League Contact Email
  mapping.leagueContactEmail = { column: 'H', row: rowNumber, value: vals.H };
  
  // Vet Status Determined By
  mapping.vetStatusDeterminedBy = { column: 'I', row: rowNumber, value: vals.I };
  
  // Registration dates
  mapping.vetRegistrationStartDateTime = { column: 'L', row: rowNumber, value: vals.L };
  mapping.tnbWtnbRegistrationStartDateTime = { column: 'M', row: rowNumber, value: vals.M };
  mapping.openRegistrationStartDateTime = { column: 'N', row: rowNumber, value: vals.N };
  
  return mapping;
}

/**
 * Update the corresponding cell in the source sheet when a field is edited
 */
export function updateCellInSourceSheet(fieldKey, newValue, cellMapping, sourceSheet, rowNumber) {
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
        cellValue = formatDateForSheet(newValue);
      }
    } else if (fieldKey === 'vetRegistrationStartDateTime' || 
               fieldKey === 'tnbWtnbRegistrationStartDateTime' || 
               fieldKey === 'openRegistrationStartDateTime') {
      // Convert Date object to MM/DD/YYYY HH:MM AM/PM format for display
      if (newValue instanceof Date) {
        cellValue = formatDateTimeForSheet(newValue);
      }
    } else if (fieldKey === 'leagueStartTime' || fieldKey === 'leagueEndTime' ||
               fieldKey === 'alternativeStartTime' || fieldKey === 'alternativeEndTime') {
      // Convert time to HH:MM AM/PM format
      if (newValue instanceof Date) {
        cellValue = formatTimeForSheet(newValue);
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
 * Write product creation results by finding columns by header name in row 1.
 * Looks up: "Product URL", "Vet Registration Variant ID", "Early Registration Variant ID",
 *           "Open Registration Variant ID", "Waitlist Registration Variant ID"
 */
export function writeProductCreationResults(sourceSheet, rowNumber, result) {
  try {
    if (!result.success || !result.data) {
      Logger.log('No successful result data to write to sheet');
      return;
    }

    const data = result.data;

    // Output columns (Product URL, variant IDs) live in row 1 of the sheet.
    // Row 2 contains the data-input headers; row 1 has the result/output headers.
    const lastCol = sourceSheet.getLastColumn();
    const headers = sourceSheet.getRange(1, 1, 1, lastCol).getValues()[0];

    const colIndex = (name) => {
      const idx = headers.findIndex(h => h.toString().trim() === name);
      if (idx === -1) {
        Logger.log(`⚠️ Column "${name}" not found in header row`);
        return -1;
      }
      return idx + 1; // 1-based
    };

    const writes = [
      { name: 'Product URL',                    value: data.productUrl },
      { name: 'Vet Registration Variant ID',    value: data.veteranVariantGid },
      { name: 'Early Registration Variant ID',  value: data.earlyVariantGid },
      { name: 'Open Registration Variant ID',   value: data.openVariantGid },
      { name: 'Waitlist Registration Variant ID', value: data.waitlistVariantGid },
    ];

    for (const { name, value } of writes) {
      if (!value) continue;
      const col = colIndex(name);
      if (col === -1) continue;
      sourceSheet.getRange(rowNumber, col).setValue(value);
      Logger.log(`Updated "${name}" (col ${col}) row ${rowNumber}: ${value}`);
    }

  } catch (error) {
    Logger.log(`Error writing product creation results: ${error.message}`);
  }
}

/**
 * Handle checkbox validation for column P (go-live checkbox)
 * This function should be called from an onEdit trigger
 */
export function handleGoLiveCheckboxEdit(e) {
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
      goLiveTimeDisplay = formatDateTimeForDisplay(vetRegistrationDate);
    } else if (earlyRegistrationDate) {
      goLiveTime = earlyRegistrationDate;
      goLiveTimeDisplay = formatDateTimeForDisplay(earlyRegistrationDate);
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
      sendGoLiveRequest(productUrl, goLiveTime);
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
