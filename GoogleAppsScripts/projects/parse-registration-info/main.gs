/**
 * Main entry point and menu for parse-registration-info
 * User interface and product creation workflow
 *
 * @fileoverview Main controller for parse-registration-info
 * @requires config/constants.gs
 * @requires src/parsers/bFlagsParser.gs
 * @requires core/portedFromProductCreateSheet/createShopifyProduct.gs
 * @requires core/portedFromProductCreateSheet/shopifyProductCreation.gs
 * @requires helpers/textUtils.gs
 * @requires validators/fieldValidation.gs
 */

// Import references for editor support
/// <reference path="src/config/constants.gs" />
/// <reference path="src/parsers/parseColBLeagueDetails.gs" />
/// <reference path="src/core/portedFromProductCreateSheet/createShopifyProduct.gs" />
/// <reference path="src/core/portedFromProductCreateSheet/shopifyProductCreation.gs" />
/// <reference path="src/helpers/textUtils.gs" />
/// <reference path="src/validators/fieldValidation.gs" />
/// <reference path="src/core/instructions.gs" />

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
function onEdit(e) {
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
}

/***** ENTRY POINTS *****/

/**
 * Entry point for Create Shopify Product functionality
 */
function showCreateProductPrompt() {
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
        const sportNorm = toTitleCase_(lastA);
        const { division } = parseColBLeagueDetails_(bLines, [], sportNorm);
        const dayNorm = toTitleCase_(dayRaw);

        const bOneLine = bRaw.replace(/\s*\n+\s*/g, ' / ');
        validRows.push({
          sheetRow,
          a: sportNorm,
          b: `${dayNorm}${bOneLine.replace(/^([^/]+)/, '').trim() ? ' ' + bOneLine.replace(/^([^/]+)/, '').trim() : ''}`,
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

// showMigrationPrompt function removed - only creating products from this sheet, not migrating them
