/**
 * Main entry point and menu for parse-registration-info
 * User interface and product creation workflow
 *
 * @fileoverview Main controller for parse-registration-info
 */

import { showInstructions } from './instructions.js';
import { createShopifyProductFromRow } from './productCreationOrchestrator.js';
import { showActionsSidebar } from '../ui/actionsSidebar.js';
import { capitalize } from '../helpers/textUtils.js';
import { parseLeagueBasicInfo } from '../parsers/parseLeagueBasicInfo.js';
import { isDateMMDDYYYY, isTimeRange12h, isDateTimeAllowed } from '../helpers/formatValidators.js';

/***** MENU *****/
export function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📊 BARS Sport Registration Parser')
    .addItem('🗂️ Open Actions Panel', 'showActionsSidebar')
    .addSeparator()
    .addItem('🛍️ Create Shopify Product', 'showCreateProductPrompt')
    .addSeparator()
    .addItem('📘 View Instructions', 'showInstructions')
    .addToUi();
}

/***** EVENT HANDLERS *****/

/**
 * Triggered when any cell is edited in the spreadsheet
 * Shows warning when columns A or B are edited
 * @param {GoogleAppsScript.Events.SheetsOnEdit} e - The edit event
 */

// biome-ignore lint/correctness/noUnusedVariables: <this is called in GAS on edit>
export function  onEdit(e) {
  const range = e.range;
  const column = range.getColumn();

  // Check if the edited cell is in column A (1) or B (2)
  if (column === 1 || column === 2) {
    const ui = SpreadsheetApp.getUi();
    ui.alert(
      'Column Edit Warning',
      'Please do not edit columns without confirming with Joe or web team first - this can cause issues with proper product creation',
      ui.ButtonSet.OK
    );
  }

  // TODO: add warnings to force users to put dates in a consistent format

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const editedValue = range.getDisplayValue();
  const emptyLike = (s) => String(s || '').trim() === '' || String(s).trim().toUpperCase() === 'TBD';

  // Season Start/End: C(3), D(4) expect MM/DD/YYYY
  if ((column === 3 || column === 4) && !emptyLike(editedValue) && !isDateMMDDYYYY(editedValue)) {
    ss.toast('Please use MM/DD/YYYY for Season Start/End (e.g., 10/15/2025).', 'Date format warning', 8);
  }

  // Price: E(5) numeric
  if (column === 5 && !emptyLike(editedValue)) {
    const n = Number(editedValue);
    if (!Number.isFinite(n) || n < 0) {
      ss.toast('Price should be a non-negative number (e.g., 150).', 'Price format warning', 8);
    }
  }

  // Play Times: F(6) prefer "HH:MM AM/PM - HH:MM AM/PM"
  if (column === 6 && !emptyLike(editedValue)) {
    if (!isTimeRange12h(editedValue)) {
      ss.toast('Play Times should look like "8:00 PM - 11:00 PM".', 'Time format warning', 8);
    }
  }

  // Registration windows: L(12), M(13), N(14) allow ISO 8601 or MM/DD/YYYY HH:MM AM/PM
  if ((column === 12 || column === 13 || column === 14) && !emptyLike(editedValue)) {
    if (!isDateTimeAllowed(editedValue)) {
      ss.toast('Use ISO (YYYY-MM-DDTHH:MM:SSZ) or MM/DD/YYYY HH:MM AM/PM for registration dates.', 'Datetime format warning', 10);
    }
  }

  // Real-time parse check with debounce (throttle alerts per cell ~3s)
  maybeWarnUnparseableCell(e);
}

/**
 * Warn if edited cell content doesn't match expected parsable format for that column.
 * Debounced via CacheService (no repeated alerts for same cell within 3s).
 */
export function maybeWarnUnparseableCell(e) {
  try {
    const range = e.range;
    const value = range.getDisplayValue();
    const col = range.getColumn();
    const sheet = range.getSheet();
    const key = `editwarn:${sheet.getSheetId()}:${range.getRow()}:${col}`;
    const cache = CacheService.getScriptCache();

    // Throttle repeated alerts per cell
    if (cache.get(key)) return;

    const v = String(value || '').trim();
    if (!v || v.toUpperCase() === 'TBD') return; // allow empty/TBD

    // Expected per-column parsers
    let ok = true;
    let help = '';
    switch (col) {
      case 3: // Season Start (C)
      case 4: // Season End (D)
        ok = isDateMMDDYYYY(v);
        help = 'Examples: 10/15/2025 or 1/5/2025';
        break;
      case 5: // Price (E)
        ok = Number.isFinite(Number(v)) && Number(v) >= 0;
        help = 'Examples: 150 or 85.00';
        break;
      case 6: // Play Times (F)
        ok = isTimeRange12h(v);
        help = 'Example: 8:00 PM - 11:00 PM';
        break;
      case 12: // Vet register (L)
      case 13: // WTNB/BIPOC/TNB register (M)
      case 14: // Open register (N)
        ok = isDateTimeAllowed(v);
        help = 'Examples: 2025-09-17T23:00:00Z or 09/17/2025 11:00 PM';
        break;
      default:
        ok = true; // no strict check for other columns yet
    }

    if (!ok) {
      // Set throttle (3 seconds)
      cache.put(key, '1', 3);
      const ui = SpreadsheetApp.getUi();
      ui.alert('Parse warning', `The product creation script cannot parse this cell.\n\nValue: "${v}"\n\nExpected format. ${help}`, ui.ButtonSet.OK);
    }
  } catch (err) {
    // best-effort; do not block edits
    console.log(`maybeWarnUnparseableCell error: ${err}`);
  }
}

/***** ENTRY POINTS *****/

/**
 * Entry point for Create Shopify Product functionality
 */

// biome-ignore lint/correctness/noUnusedVariables: <this is called in GAS on menu item click>
export function  showCreateProductPrompt() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getActiveSheet();

  const SOURCE_LISTING_START_ROW = 3; // source headers end at row 2; data from row 3+
  const lastRow = sourceSheet.getLastRow();
  if (lastRow < SOURCE_LISTING_START_ROW) {
    ui.alert('No data rows found to create products from.');
    return;
  }

  const headerRow = sourceSheet.getRange(1, 1, 1, sourceSheet.getLastColumn()).getValues()[0];
  const productUrlColIndex = headerRow.findIndex(h => h.toString().trim() === 'Product URL');
  // Fall back to column Q (index 16) if header not found
  const productUrlIdx = productUrlColIndex !== -1 ? productUrlColIndex : 16;

  const startRow = SOURCE_LISTING_START_ROW + 1;
  const values = sourceSheet
    .getRange(startRow, 1, lastRow - SOURCE_LISTING_START_ROW, 21) // A to U columns (including Q for productUrl)
    .getDisplayValues();

  // Filter rows that have the required columns populated
  const requiredColumns = [
    { col: 0, name: 'Day/Type' },       // A (index 0)
    { col: 1, name: 'League Details' }, // B (index 1)
    { col: 2, name: 'Season Start' },   // C (index 2)
    { col: 3, name: 'Season End' },     // D (index 3)
    { col: 4, name: 'Price' },          // E (index 4)
    { col: 5, name: 'Play Times' },     // F (index 5)
    { col: 6, name: 'Location' },       // G (index 6)
    { col: 12, name: 'WTNB/BIPOC/TNB Register' }, // M (index 12)
    { col: 13, name: 'Open Register' }  // N (index 13)
  ];

  let lastA = '';
  const validRows = [];

  for (let i = 0; i < values.length; i++) {
    const sheetRow = startRow + i;
    const rowValues = values[i];

    const aRaw = (rowValues[0] || '').trim();
    const bRaw = (rowValues[1] || '').trim();

    if (aRaw) lastA = aRaw;
    if (!bRaw) continue; // skip rows without day/details

    // Check if required columns have values
    const hasRequiredValues = requiredColumns.every(req => {
      const value = (rowValues[req.col] || '').toString().trim();
      return value.length > 0;
    });

    if (hasRequiredValues) {
      // Check if Product URL column is empty
      const productUrl = (rowValues[productUrlIdx] || '').toString().trim();
      const hasExistingProduct = productUrl.length > 0;

      if (!hasExistingProduct) {
        const bLines = bRaw.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
        const dayRaw = (bLines[0] || '').trim();
        const sportNorm = capitalize(lastA, true);
        const { division } = parseLeagueBasicInfo(bRaw, sportNorm);
        const dayNorm = capitalize(dayRaw, true);

        const bOneLine = bRaw.replace(/\s*\n+\s*/g, ' / ');
        validRows.push({
          sheetRow,
          a: sportNorm,
          b: `${dayNorm}${bOneLine.replace(/^([^/]+)/, '').trim() ? ` ${bOneLine.replace(/^([^/]+)/, '').trim()}` : ''}`,
          division: division
        });
      }
    }
  }

  if (!validRows.length) {
    ui.alert('No rows available for product creation.\n\nRows must have:\n• All required data (Day/Type, League Details, Season Start/End, Price, Play Times, Location, WTNB/BIPOC Register, Open Register)\n• No existing product (column Q must be empty)\n\nRows with products already created are excluded from this list.');
    return;
  }

  const items = validRows.map(r => `${r.sheetRow}: ${r.a} | ${r.b}`);

  const message =
    'Enter the ROW NUMBER to create a Shopify product from.\n\n' +
    'Available rows (complete data, no existing product):\n' +
    items.slice(0, 60).join('\n') + (items.length > 60 ? `\n… (${items.length - 60} more)` : '')

  const resp = ui.prompt('Create Shopify Product', message, ui.ButtonSet.OK_CANCEL);
  if (resp.getSelectedButton() !== ui.Button.OK) return;

  const selectedRow = parseInt(resp.getResponseText().trim(), 10);
  if (!Number.isInteger(selectedRow) || selectedRow < SOURCE_LISTING_START_ROW || selectedRow > lastRow) {
    ui.alert('Invalid row number. Please enter a valid row number from the list.');
    return;
  }

  // Validate the selected row has data
  const selectedRowData = validRows.find(r => r.sheetRow === selectedRow);
  if (!selectedRowData) {
    ui.alert('Selected row does not have all required data for product creation.');
    return;
  }

  try {
    createShopifyProductFromRow(sourceSheet, selectedRow);
  } catch (error) {
    Logger.log(`Error creating product: ${error}`);
    ui.alert(`Error creating product: ${error.message}`);
  }
}
