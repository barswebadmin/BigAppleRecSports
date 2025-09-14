/**
 * Google Sheets Helper Functions
 * Copy these functions into your Google Apps Script projects as needed
 */

// =============================================================================
// BASIC SHEET ACCESS FUNCTIONS
// =============================================================================

/**
 * Get the active sheet from the active spreadsheet
 * @returns {Sheet} Active sheet
 */
function getSheet() {
  return SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
}

/**
 * Get all data from the active sheet
 * @returns {Array<Array>} 2D array of sheet data
 */
function getSheetData() {
  return getSheet().getDataRange().getValues();
}

/**
 * Get headers from the active sheet (first row)
 * @returns {Array} Array of header strings
 */
function getSheetHeaders() {
  const data = getSheetData();
  return data[0];
}

/**
 * Get sheet by ID
 * @param {string} sheetId - Google Sheets ID
 * @returns {Spreadsheet} Spreadsheet object
 */
function getSheetById(sheetId) {
  return SpreadsheetApp.openById(sheetId);
}

/**
 * Get data from a specific sheet by ID
 * @param {string} sheetId - Google Sheets ID
 * @param {string} sheetName - Optional sheet name (defaults to first sheet)
 * @returns {Array<Array>} 2D array of sheet data
 */
function getSheetDataById(sheetId, sheetName = null) {
  const spreadsheet = SpreadsheetApp.openById(sheetId);
  const sheet = sheetName ? spreadsheet.getSheetByName(sheetName) : spreadsheet.getSheets()[0];
  return sheet.getDataRange().getValues();
}

// =============================================================================
// ROW PARSING AND DATA EXTRACTION
// =============================================================================

/**
 * Parse row data based on headers (generic version for refunds/orders)
 * @param {Array} rowObject - Row data array
 * @param {Array} sheetHeaders - Headers array
 * @returns {Object} Parsed row data object
 */
function parseRefundRowData(rowObject, sheetHeaders) {
  const rowData = {};

  sheetHeaders.forEach((header, i) => {
    const lowerHeader = header.toLowerCase().trim();

    if (lowerHeader.includes("timestamp")) {
      rowData.requestSubmittedAt = rowObject[i];
    } else if (lowerHeader.includes("email address")) {
      rowData.requestorEmail = rowObject[i];
    } else if (lowerHeader.includes("order number")) {
      rowData.rawOrderNumber = rowObject[i];
    } else if (lowerHeader.includes("do you want a refund")) {
      rowData.refundOrCredit = rowObject[i].toLowerCase().includes("refund") ? "refund" : "credit";
    } else if (lowerHeader.includes("anything else to note")) {
      rowData.requestNotes = rowObject[i];
    } else if (lowerHeader.includes("first name")) {
      rowData.requestorFirstName = rowObject[i];
    } else if (lowerHeader.includes("last name")) {
      rowData.requestorLastName = rowObject[i];
    }
  });

  return rowData;
}

/**
 * Generic function to find a row by column value
 * @param {Array<Array>} data - Sheet data (2D array)
 * @param {string} columnName - Column header to search in
 * @param {string} searchValue - Value to search for
 * @param {Function} normalizeFunc - Optional normalization function
 * @returns {Array|null} Row data or null if not found
 */
function findRowByColumnValue(data, columnName, searchValue, normalizeFunc = null) {
  if (!data || data.length === 0) return null;

  const headers = data[0];
  const columnIndex = headers.findIndex(h => h.toLowerCase().includes(columnName.toLowerCase()));

  if (columnIndex === -1) {
    Logger.log(`❌ Column '${columnName}' not found in headers.`);
    return null;
  }

  const normalizedSearch = normalizeFunc ? normalizeFunc(searchValue) : searchValue;

  // Find matching row (skip header row)
  const matchingRow = data
    .slice(1)
    .find(row => {
      const cellValue = row[columnIndex];
      const normalizedCell = normalizeFunc ? normalizeFunc(cellValue) : cellValue;
      return normalizedCell === normalizedSearch;
    });

  return matchingRow || null;
}

/**
 * Get request details from order number (specific implementation)
 * @param {string} rawOrderNumber - Order number to search for
 * @returns {Object|null} Parsed request data or null if not found
 */
function getRequestDetailsFromOrderNumber(rawOrderNumber) {
  const data = getSheetData();
  const sheetHeaders = getSheetHeaders();

  const orderIdColIndex = sheetHeaders.findIndex(h => h.toLowerCase().includes("order number"));
  const timestampColIndex = sheetHeaders.findIndex(h => h.toLowerCase().includes("timestamp"));

  if (orderIdColIndex === -1) {
    Logger.log(`❌ Order column header not found.`);
    return null;
  }

  // Find all matching rows
  const matchingRows = data
    .slice(1) // skip headers
    .filter(row => {
      const cellValue = row[orderIdColIndex];
      return normalizeOrderNumber(cellValue?.toString()?.trim()) === normalizeOrderNumber(rawOrderNumber);
    });

  if (matchingRows.length === 0) {
    Logger.log(`❌ No matching order found for ${rawOrderNumber}.`);
    return null;
  }

  // Return the row with the most recent timestamp
  const mostRecentRow = matchingRows.sort((a, b) => new Date(b[timestampColIndex]) - new Date(a[timestampColIndex]))[0];

  return parseRefundRowData(mostRecentRow, sheetHeaders);
}

// =============================================================================
// SHEET LINK AND REFERENCE FUNCTIONS
// =============================================================================

/**
 * Generate a link to a specific row in a Google Sheet
 * @param {string} sheetId - Google Sheets ID
 * @param {string} sheetGid - Sheet GID (tab identifier)
 * @param {number} rowNumber - Row number (1-based)
 * @returns {string} Direct link to the row
 */
function getSheetRowLink(sheetId, sheetGid, rowNumber) {
  return `https://docs.google.com/spreadsheets/d/${sheetId}/edit#gid=${sheetGid}&range=A${rowNumber}`;
}

/**
 * Get row link for a specific order number (specific implementation)
 * @param {string} orderNumber - Order number to find
 * @param {string} sheetId - Google Sheets ID
 * @param {string} sheetGid - Sheet GID
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

  // Convert to 1-based row index for Google Sheets link
  const rowNumber = rowIndex + 2;

  // If sheetId and sheetGid are provided, use them; otherwise use defaults
  if (sheetId && sheetGid) {
    return getSheetRowLink(sheetId, sheetGid, rowNumber);
  }

  // Fallback - this would need to be customized per project
  throw new Error("sheetId and sheetGid are required for getRowLink");
}

// =============================================================================
// SHEET MODIFICATION FUNCTIONS
// =============================================================================

/**
 * Mark an order as processed in the sheet
 * @param {string} rawOrderNumber - Order number to mark as processed
 * @returns {boolean} Success status
 */
function markOrderAsProcessed(rawOrderNumber) {
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    const data = sheet.getDataRange().getValues();
    const headers = data[0];

    const orderColIndex = headers.findIndex(h =>
      h.toLowerCase().includes("order number")
    );
    const processedColIndex = headers.findIndex(h =>
      h.toLowerCase().includes("processed")
    );

    if (orderColIndex === -1 || processedColIndex === -1) {
      throw new Error(
        `Missing required columns.\nHeaders: ${JSON.stringify(headers)}\nFound orderColIndex: ${orderColIndex}, processedColIndex: ${processedColIndex}`
      );
    }

    const normalizedTarget = normalizeOrderNumber(rawOrderNumber);
    let matchedValue = null;
    const rowIndex = data.findIndex((row, i) => {
      if (i === 0) return false;
      const cellValue = row[orderColIndex];
      const normalizedCell = normalizeOrderNumber(cellValue?.toString().trim() || "");
      if (normalizedCell === normalizedTarget) {
        matchedValue = cellValue;
        return true;
      }
      return false;
    });

    if (rowIndex === -1) {
      throw new Error(
        `Order number not found.\nRaw input: ${rawOrderNumber}\nNormalized: ${normalizedTarget}\nColumn Index: ${orderColIndex}\nExample values:\n` +
        data.slice(1, 6).map(row => row[orderColIndex]).join("\n")
      );
    }

    sheet.getRange(rowIndex + 1, processedColIndex + 1).setValue(true);
    Logger.log(`✅ Marked order ${rawOrderNumber} as processed`);
    return true;
  } catch (error) {
    Logger.log(`❌ Error marking order as processed: ${error.message}`);
    return false;
  }
}

/**
 * Update a cell value in the active sheet
 * @param {number} row - Row number (1-based)
 * @param {number} col - Column number (1-based)
 * @param {any} value - Value to set
 * @returns {boolean} Success status
 */
function updateCellValue(row, col, value) {
  try {
    const sheet = getSheet();
    sheet.getRange(row, col).setValue(value);
    return true;
  } catch (error) {
    Logger.log(`❌ Error updating cell (${row}, ${col}): ${error.message}`);
    return false;
  }
}

/**
 * Append a new row to the active sheet
 * @param {Array} rowData - Array of values to append
 * @returns {boolean} Success status
 */
function appendRowToSheet(rowData) {
  try {
    const sheet = getSheet();
    sheet.appendRow(rowData);
    return true;
  } catch (error) {
    Logger.log(`❌ Error appending row: ${error.message}`);
    return false;
  }
}
