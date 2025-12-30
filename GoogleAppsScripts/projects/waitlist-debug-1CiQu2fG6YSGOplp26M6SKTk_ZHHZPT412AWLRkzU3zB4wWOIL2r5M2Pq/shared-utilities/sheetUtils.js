/**
 * Google Sheets Helper Functions
 * Consolidated sheet access and modification utilities
 */

// =============================================================================
// BASIC SHEET ACCESS FUNCTIONS
// =============================================================================

function getSheet() {
  const spreadsheet = SpreadsheetApp.openById(WAITLIST_SPREADSHEET_ID);
  return spreadsheet.getSheets()[0];
}

function getSheetData() {
  return getSheet().getDataRange().getValues();
}

function getSheetHeaders() {
  const data = getSheetData();
  return data[0];
}

function getSheetById(sheetId) {
  return SpreadsheetApp.openById(sheetId);
}

function getSheetDataById(sheetId, sheetName = null) {
  const spreadsheet = SpreadsheetApp.openById(sheetId);
  const sheet = sheetName ? spreadsheet.getSheetByName(sheetName) : spreadsheet.getSheets()[0];
  return sheet.getDataRange().getValues();
}

// =============================================================================
// ROW FINDING AND SEARCHING
// =============================================================================

function findRowByColumnValue(data, columnName, searchValue, normalizeFunc = null) {
  if (!data || data.length === 0) return null;

  const headers = data[0];
  const columnIndex = headers.findIndex(h => h.toLowerCase().includes(columnName.toLowerCase()));

  if (columnIndex === -1) {
    Logger.log(`❌ Column '${columnName}' not found in headers.`);
    return null;
  }

  const normalizedSearch = normalizeFunc ? normalizeFunc(searchValue) : searchValue;

  const matchingRow = data
    .slice(1)
    .find(row => {
      const cellValue = row[columnIndex];
      const normalizedCell = normalizeFunc ? normalizeFunc(cellValue) : cellValue;
      return normalizedCell === normalizedSearch;
    });

  return matchingRow || null;
}

// =============================================================================
// SHEET MODIFICATION FUNCTIONS
// =============================================================================

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

// =============================================================================
// WAITLIST-SPECIFIC SEARCH FUNCTIONS
// =============================================================================

/**
 * Get all leagues for a given email address
 * Returns array of {league, spot} objects
 * @param {string} email - Email address to search for
 * @returns {Object} - {leagues: [], debugLog: []}
 */
function getAllLeaguesForEmail(email) {
  const debugLog = [];
  debugLog.push(`🔍 Getting all leagues for email: ${email}`);
  
  try {
    const sheet = getSheet();
    const dataRange = sheet.getDataRange();
    const values = dataRange.getValues();
    const backgrounds = dataRange.getBackgrounds();
    const headers = values[0];
    const dataRows = values.slice(1);
    const backgroundRows = backgrounds.slice(1);
    
    debugLog.push(`📊 Found ${dataRows.length} total rows`);
    
    const emailCol = headers.findIndex(h => h.toLowerCase().includes("email address"));
    const leagueCol = headers.findIndex(h => h.toLowerCase().includes("please select the league you want to sign up for"));
    const notesCol = headers.findIndex(h => h.toLowerCase().includes("notes"));
    
    if (emailCol === -1 || leagueCol === -1) {
      debugLog.push(`❌ Required columns not found. Email col: ${emailCol}, League col: ${leagueCol}`);
      return { leagues: [], debugLog };
    }
    
    debugLog.push(`📍 Column indices - Email: ${emailCol}, League: ${leagueCol}, Notes: ${notesCol}`);
    
    const leagueData = new Map();
    let matchingRows = 0;
    
    dataRows.forEach((row, index) => {
      const rowEmail = (row[emailCol] || '').toString().trim().toLowerCase();
      const rowLeague = (row[leagueCol] || '').toString().trim();
      const rowNotes = notesCol !== -1 ? (row[notesCol] || '').toString().trim().toLowerCase() : '';
      const rowBackgrounds = backgroundRows[index];
      
      // Skip if row has any cell with a background color (not white/default)
      const hasBackgroundColor = rowBackgrounds.some(bg => {
        const bgLower = (bg || '').toLowerCase();
        return bgLower && bgLower !== '#ffffff' && bgLower !== '#fff' && bgLower !== 'white';
      });
      
      if (hasBackgroundColor) {
        return;
      }
      
      if (rowNotes.includes('process') || rowNotes.includes('cancel') || rowNotes.includes('done')) {
        return;
      }
      
      if (!leagueData.has(rowLeague)) {
        leagueData.set(rowLeague, { position: 0, found: false });
      }
      
      leagueData.get(rowLeague).position++;
      
      if (rowEmail === email.toLowerCase()) {
        matchingRows++;
        if (!leagueData.get(rowLeague).found) {
          leagueData.get(rowLeague).found = true;
          leagueData.get(rowLeague).spot = leagueData.get(rowLeague).position;
        }
      }
    });
    
    debugLog.push(`📊 Found ${matchingRows} matching rows for email`);
    
    const leagues = [];
    for (const [league, data] of leagueData.entries()) {
      if (data.found) {
        leagues.push({
          league: league,
          spot: data.spot
        });
        debugLog.push(`   ✅ ${league}: Position #${data.spot}`);
      }
    }
    
    debugLog.push(`✅ Returning ${leagues.length} leagues`);
    return { leagues, debugLog };
    
  } catch (error) {
    debugLog.push(`💥 Error: ${error.message}`);
    return { leagues: [], debugLog, error: error.message };
  }
}
