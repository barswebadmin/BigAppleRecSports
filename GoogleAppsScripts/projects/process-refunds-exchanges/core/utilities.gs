/**
 * ========================================================================
 * ESSENTIAL UTILITIES
 * ========================================================================
 *
 * Consolidated utility functions used by the core refunds processing system.
 * Only includes functions that are actively used by the application.
 */

/**
 * Normalize order number to include # prefix
 * @param {string|number} orderNumber - Raw order number
 * @returns {string} Normalized order number with # prefix
 */
function normalizeOrderNumber(orderNumber) {
  const str = String(orderNumber || "").trim();
  return str.startsWith("#") ? str : `#${str}`;
}

/**
 * Get sheet data from the main refunds spreadsheet
 * @returns {Array} Sheet data as 2D array
 */
function getSheetData() {
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName('Form Responses 1') ||
                SpreadsheetApp.openById(SHEET_ID).getActiveSheet();
  return sheet.getDataRange().getValues();
}

/**
 * Get sheet headers from the main refunds spreadsheet
 * @returns {Array} Header row as array
 */
function getSheetHeaders() {
  const data = getSheetData();
  return data[0] || [];
}

/**
 * Generate link to specific row in Google Sheets for given order number
 * @param {string} orderNumber - Order number to find
 * @param {string} sheetId - Sheet ID (uses SHEET_ID if not provided)
 * @param {string} sheetGid - Sheet GID (uses SHEET_GID if not provided)
 * @returns {string} Link to the row or empty string if not found
 */
function getRowLink(orderNumber, sheetId = null, sheetGid = null) {
  const data = getSheetData();
  const sheetHeaders = getSheetHeaders();

  const orderIdColIndex = sheetHeaders.findIndex(h => h.toLowerCase().includes("order number"));

  const rowIndex = data.slice(1).findIndex(row => {
    const cellValue = row[orderIdColIndex];
    if (!cellValue) return false;
    return normalizeOrderNumber(cellValue.toString()) === normalizeOrderNumber(orderNumber.toString());
  });

  if (rowIndex === -1) {
    Logger.log(`⚠️ Order number ${orderNumber} not found in sheet.`);
    return "";
  }

  const actualRowNumber = rowIndex + 2; // +1 for 0-based index, +1 for header row
  const targetSheetId = sheetId || SHEET_ID;
  const targetSheetGid = sheetGid || SHEET_GID;

  if (!targetSheetId || !targetSheetGid) {
    throw new Error("sheetId and sheetGid are required for getRowLink");
  }

  return `https://docs.google.com/spreadsheets/d/${targetSheetId}/edit#gid=${targetSheetGid}&range=A${actualRowNumber}:A${actualRowNumber}`;
}

/**
 * Update the Notes column (column K) for a specific order
 * @param {string} rawOrderNumber - Order number to find
 * @param {string} requestorEmail - Email to help identify the correct row
 * @param {string} note - Note to add to column K
 * @returns {boolean} Success status
 */
function updateOrderNotesColumn(rawOrderNumber, requestorEmail, note) {
  try {
    const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName('Form Responses 1') ||
                  SpreadsheetApp.openById(SHEET_ID).getActiveSheet();
    const data = sheet.getDataRange().getValues();
    const headers = data[0];

    // Find column indices
    const orderColIndex = headers.findIndex(h => h.toLowerCase().includes("order number"));
    const emailColIndex = headers.findIndex(h => h.toLowerCase().includes("email"));
    const notesColIndex = headers.findIndex(h => h.toLowerCase().includes("notes") || h.toLowerCase().includes("note"));

    if (orderColIndex === -1) {
      throw new Error(`Order number column not found. Headers: ${JSON.stringify(headers)}`);
    }

    if (notesColIndex === -1) {
      throw new Error(`Notes column not found. Headers: ${JSON.stringify(headers)}`);
    }

    // Find the row with matching order number
    const normalizedSearchOrder = normalizeOrderNumber(rawOrderNumber);
    let rowIndex = -1;

    for (let i = 1; i < data.length; i++) {
      const rowOrderNumber = data[i][orderColIndex];
      if (rowOrderNumber && normalizeOrderNumber(rowOrderNumber.toString()) === normalizedSearchOrder) {
        // Double-check with email if provided
        if (requestorEmail && emailColIndex !== -1) {
          const rowEmail = data[i][emailColIndex];
          if (rowEmail && rowEmail.toString().toLowerCase().trim() === requestorEmail.toLowerCase().trim()) {
            rowIndex = i;
            break;
          }
        } else {
          rowIndex = i;
          break;
        }
      }
    }

    if (rowIndex === -1) {
      Logger.log(`⚠️ Order ${rawOrderNumber} not found for email ${requestorEmail}`);
      return false;
    }

    // Update the Notes column (K is the 11th column, index 10)
    const targetRow = rowIndex + 1; // Convert to 1-based indexing for Sheets
    const targetCol = notesColIndex + 1; // Convert to 1-based indexing for Sheets

    sheet.getRange(targetRow, targetCol).setValue(note);
    Logger.log(`✅ Updated Notes column for order ${rawOrderNumber}: "${note}"`);

    return true;

  } catch (error) {
    Logger.log(`❌ Error updating Notes column: ${error.toString()}`);
    return false;
  }
}
