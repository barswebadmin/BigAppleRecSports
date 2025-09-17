/**
 * Main entry point and menu for parse-registration-info
 * User interface and product creation workflow
 *
 * @fileoverview Main controller for parse-registration-info
 * @requires config/constants.gs
 * @requires ../parsers/bFlagsParser.gs
 * @requires core/productCreationOrchestrator.gs
 * @requires helpers/textUtils.gs
 * @requires validators/fieldValidation.gs
 */
/** biome-ignore-all lint/suspicious/useIterableCallbackReturn: <explanation> */

// Import references for editor support
/// <reference path="../config/constants.gs" />
/// <reference path="../parsers/parseColBLeagueBasicInfo_.gs" />
/// <reference path="./productCreationOrchestrator.gs" />
/// <reference path="../helpers/textUtils.gs" />
/// <reference path="../validators/fieldValidation.gs" />
/// <reference path="./instructions.gs" />

// Configuration constants
const ENVIRONMENT = 'dev'; // 'prod' or 'dev'
const NGROK_URL = 'https://56d6dd03ac9d.ngrok-free.app';

/***** MENU *****/
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📊 BARS Sport Registration Parser')
    .addItem('🛍️ Create Shopify Product', 'showCreateProductPrompt')
    .addSeparator()
    .addItem('📘 View Instructions', 'showInstructions')
    .addToUi();

  // Show instructions on first open
  showInstructions();
}

/***** EVENT HANDLERS *****/

/**
 * Triggered when any cell is edited in the spreadsheet
 * Shows warning when columns A or B are edited
 * @param {GoogleAppsScript.Events.SheetsOnEdit} e - The edit event
 */

// biome-ignore lint/correctness/noUnusedVariables: <this is called in GAS on edit>
function  onEdit(e) {
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

  // Lightweight format helpers
  // Use shared validators
  const isDateMMDDYYYY = isDateMMDDYYYY_;
  const isTimeRange12h = isTimeRange12h_;
  const isDateTimeAllowed = isDateTimeAllowed_;

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const editedValue = range.getDisplayValue();
  const emptyLike = (s) => String(s || '').trim() === '' || String(s).trim().toUpperCase() === 'TBD';

  // Season Start/End: D(4), E(5) expect MM/DD/YYYY
  if ((column === 4 || column === 5) && !emptyLike(editedValue) && !isDateMMDDYYYY(editedValue)) {
    ss.toast('Please use MM/DD/YYYY for Season Start/End (e.g., 10/15/2025).', 'Date format warning', 8);
  }

  // Price: F(6) numeric
  if (column === 6 && !emptyLike(editedValue)) {
    const n = Number(editedValue);
    if (!Number.isFinite(n) || n < 0) {
      ss.toast('Price should be a non-negative number (e.g., 150).', 'Price format warning', 8);
    }
  }

  // Play Times: G(7) prefer "HH:MM AM/PM - HH:MM AM/PM"
  if (column === 7 && !emptyLike(editedValue)) {
    if (!isTimeRange12h(editedValue)) {
      ss.toast('Play Times should look like "8:00 PM - 11:00 PM".', 'Time format warning', 8);
    }
  }

  // Registration windows: M(13), N(14), O(15) allow ISO 8601 or MM/DD/YYYY HH:MM AM/PM
  if ((column === 13 || column === 14 || column === 15) && !emptyLike(editedValue)) {
    if (!isDateTimeAllowed(editedValue)) {
      ss.toast('Use ISO (YYYY-MM-DDTHH:MM:SSZ) or MM/DD/YYYY HH:MM AM/PM for registration dates.', 'Datetime format warning', 10);
    }
  }

  // Real-time parse check with debounce (throttle alerts per cell ~3s)
  maybeWarnUnparseableCell_(e);
}

/**
 * Warn if edited cell content doesn't match expected parsable format for that column.
 * Debounced via CacheService (no repeated alerts for same cell within 3s).
 */
function maybeWarnUnparseableCell_(e) {
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
      case 4: // Season Start
      case 5: // Season End
        ok = isDateMMDDYYYY_(v);
        help = 'Examples: 10/15/2025 or 1/5/2025';
        break;
      case 6: // Price
        ok = Number.isFinite(Number(v)) && Number(v) >= 0;
        help = 'Examples: 150 or 85.00';
        break;
      case 7: // Play Times
        ok = isTimeRange12h_(v);
        help = 'Example: 8:00 PM - 11:00 PM';
        break;
      case 13: // Early/WTNB/BIPOC/TNB register
      case 14: // Vet register
      case 15: // Open register
        ok = isDateTimeAllowed_(v);
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
    console.log(`maybeWarnUnparseableCell_ error: ${err}`);
  }
}

/***** ENTRY POINTS *****/

/**
 * Entry point for Create Shopify Product functionality
 */

// biome-ignore lint/correctness/noUnusedVariables: <this is called in GAS on menu item click>
function  showCreateProductPrompt() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getActiveSheet();

  const SOURCE_LISTING_START_ROW = 3; // source headers end at row 2; data from row 3+
  const lastRow = sourceSheet.getLastRow();
  if (lastRow < SOURCE_LISTING_START_ROW) {
    ui.alert('No data rows found to create products from.');
    return;
  }

  const startRow = SOURCE_LISTING_START_ROW + 1;
  const values = sourceSheet
    .getRange(startRow, 1, lastRow - SOURCE_LISTING_START_ROW, 21) // A to U columns (including Q for productUrl)
    .getDisplayValues();

  // Filter rows that have the required columns populated
  const requiredColumns = [
    { col: 1, name: 'Day/Type' },      // A/B merged
    { col: 2, name: 'League Details' }, // C
    { col: 3, name: 'Season Start' },   // D
    { col: 4, name: 'Season End' },     // E
    { col: 5, name: 'Price' },          // F
    { col: 6, name: 'Play Times' },     // G
    { col: 7, name: 'Location' },       // H
    { col: 12, name: 'WTNB/BIPOC/TNB Register' }, // M
    { col: 14, name: 'Open Register' }   // O
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
      // Check if Product URL (column Q, index 16) is empty
      const productUrl = (rowValues[16] || '').toString().trim();
      const hasExistingProduct = productUrl.length > 0;

      if (!hasExistingProduct) {
        const bLines = bRaw.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
        const dayRaw = (bLines[0] || '').trim();
        const sportNorm = capitalize(lastA, true);
        const { division } = parseColBLeagueBasicInfo_(bRaw, [], sportNorm);
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
    createShopifyProductFromRow_(sourceSheet, selectedRow);
  } catch (error) {
    Logger.log(`Error creating product: ${error}`);
    ui.alert(`Error creating product: ${error.message}`);
  }
}
