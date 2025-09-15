/**
 * Main entry point and menu for parse-registration-info
 * User interface and migration workflow
 *
 * @fileoverview Main controller for parse-registration-info
 * @requires config/constants.gs
 * @requires core/migration.gs
 * @requires core/flagsParser.gs
 * @requires core/portedFromProductCreateSheet/createShopifyProduct.gs
 * @requires core/portedFromProductCreateSheet/shopifyProductCreation.gs
 * @requires helpers/textUtils.gs
 * @requires validators/fieldValidation.gs
 */
/** biome-ignore-all lint/suspicious/useIterableCallbackReturn: <explanation> */

// Import references for editor support
/// <reference path="config/constants.gs" />
/// <reference path="core/migration.gs" />
/// <reference path="core/flagsParser.gs" />
/// <reference path="core/portedFromProductCreateSheet/createShopifyProduct.gs" />
/// <reference path="core/portedFromProductCreateSheet/shopifyProductCreation.gs" />
/// <reference path="helpers/textUtils.gs" />
/// <reference path="validators/fieldValidation.gs" />
/// <reference path="instructions.gs" />

/***** MENU *****/
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📊 BARS Sport Registration Parser')
    .addItem('🔄 Migrate Row to Product Creation Sheet', 'showMigrationPrompt')
    .addItem('🛍️ Create Shopify Product', 'showCreateProductPrompt')
    .addSeparator()
    .addItem('📘 View Instructions', 'showInstructions')
    .addToUi();

  // Show instructions on first open
  showInstructions();
}

/***** ENTRY POINTS *****/

/**
 * Entry point for Create Shopify Product functionality
 */
function showCreateProductPrompt() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getActiveSheet();

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
        const { division } = parseBFlags_(bLines, []);

        const sportNorm = toTitleCase_(lastA);
        const dayNorm = toTitleCase_(dayRaw);

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

function showMigrationPrompt() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sourceSheet = ss.getActiveSheet();

  const lastRow = sourceSheet.getLastRow();
  if (lastRow < SOURCE_LISTING_START_ROW) {
    ui.alert('No data rows found to migrate.');
    return;
  }

  const startRow = SOURCE_LISTING_START_ROW + 1; // => 4
  const values = sourceSheet
    .getRange(startRow, 1, lastRow - SOURCE_LISTING_START_ROW, 2) // rows 4..last
    .getDisplayValues();

  const targetSs = SpreadsheetApp.openById(TARGET_SPREADSHEET_ID);
  const destTabName = (sourceSheet.getRange('A1').getDisplayValue() || '').trim();
  const targetSheet = destTabName ? targetSs.getSheetByName(destTabName) : null;
  const targetMap = targetSheet ? getTargetIndexMap_(targetSheet, TARGET_HEADER_ROW) : new Map();

  Logger.log(`destinationTabName ${destTabName}`)
  Logger.log(`targetSheet: ${targetSheet}`)
  Logger.log('targetMap entries:\n%s', JSON.stringify(
    Array.from(targetMap.entries()).map(([k, v]) => ({ key: k, row: v.row, readyTrue: v.readyTrue })), null, 2
  ));

  let lastA = '';
  const rows = [];
  for (let i = 0; i < values.length; i++) {
    const sheetRow = startRow + i;      // actual sheet row number
    const aRaw = (values[i][0] || '').trim();
    const bRaw = (values[i][1] || '').trim();

    if (aRaw) lastA = aRaw;             // carry forward merged A
    if (!bRaw) continue; // skip blanks (no day/details)

    // Break B into lines for parsing
    const bLines = bRaw.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    const dayRaw = (bLines[0] || '').trim();
    const { division } = parseBFlags_(bLines, []);  // reuse your helper

    // Normalize using same logic as migration
    const sportNorm = toTitleCase_(lastA);
    const dayNorm   = toTitleCase_(dayRaw);

    // If we have a target tab, filter out rows that exist with Ready=true
    if (targetSheet) {
      const key = makeKey_(sportNorm, dayNorm, division);
      const found = targetMap.get(key);
      if (found && found.readyTrue) continue; // hide from options
    }

    const bOneLine = bRaw.replace(/\s*\n+\s*/g, ' / ');
    rows.push({ sheetRow, a: sportNorm, b: `${dayNorm}${bOneLine.replace(/^([^/]+)/, '').trim() ? ' ' + bOneLine.replace(/^([^/]+)/, '').trim() : ''}` });
  }

  if (!rows.length) {
    ui.alert('No rows found to migrate. Make sure column B has content.');
    return;
  }

  const items = rows.map(r => `${r.sheetRow}: ${r.a ? r.a : ''} | ${r.b}`);

  const message =
    'Enter the ROW NUMBER to migrate.\n\n' +
    'Available rows (Row#):\n' +
    items.slice(0, 60).join('\n') + (items.length > 60 ? `\n… (${items.length - 60} more)` : '') +
    '\n\nDestination tab will be looked up by cell A1 (on this sheet). Make sure that has the season and year you want this to be ported into.';

  const resp = ui.prompt('Migrate a row', message, ui.ButtonSet.OK_CANCEL);
  if (resp.getSelectedButton() !== ui.Button.OK) return;

  const selectedRow = parseInt(resp.getResponseText().trim(), 10);
  if (!Number.isInteger(selectedRow) || selectedRow < SOURCE_LISTING_START_ROW || selectedRow > lastRow) {
    ui.alert('Invalid row number.');
    return;
  }
  const bCell = sourceSheet.getRange(selectedRow, 2).getDisplayValue().trim();
  if (!bCell) {
    ui.alert('That row has no details in column B (day/league info). Please pick a row with data.');
    return;
  }
  const ab = sourceSheet.getRange(selectedRow, 1, 1, 2).getDisplayValues()[0];
  if (!ab[0].toString().trim() && !ab[1].toString().trim()) {
    ui.alert('That row has no data in columns A or B. Please pick a row with data.');
    return;
  }

  try {
    const { unresolved, requiredCheck, cancel, writeAttempts, writeFailures, targetRow } = migrateRowToTarget_(sourceSheet, selectedRow);
    if (cancel) return ui.alert('Canceled')

    // Determine success status
    const hasWriteFailures = writeFailures && writeFailures.length > 0;
    const successfulWrites = writeAttempts ? writeAttempts.length - (writeFailures ? writeFailures.length : 0) : 0;
    const totalAttempts = writeAttempts ? writeAttempts.length : 0;

    const parts = [];

    if (hasWriteFailures) {
      parts.push(`Migration of row ${selectedRow} completed with WARNINGS.`);
      parts.push(`Successfully written: ${successfulWrites}/${totalAttempts} fields to target row ${targetRow}`);
    } else {
      parts.push(`Migration of row ${selectedRow} completed successfully.`);
      if (totalAttempts > 0) {
        parts.push(`All ${totalAttempts} fields written successfully to target row ${targetRow}`);
      }
    }

    // Show write failures first (most important)
    if (hasWriteFailures) {
      parts.push(`\n❌ Write failures (${writeFailures.length}):`);
      writeFailures.slice(0, 5).forEach(failure => {
        if (failure.header === 'ALL_FIELDS') {
          parts.push(`• Sheet write error: ${failure.reason}`);
        } else {
          parts.push(`• ${failure.header}: "${failure.expected}" → "${failure.actual}" (${failure.reason})`);
        }
      });
      if (writeFailures.length > 5) parts.push(`• ... and ${writeFailures.length - 5} more write failures`);
    }

    if (unresolved.length) {
      parts.push(`\n⚠️ Unresolved items (${unresolved.length}):`);
      unresolved.slice(0, 5).forEach(item => parts.push(`• ${item}`));
      if (unresolved.length > 5) parts.push(`• ... and ${unresolved.length - 5} more`);
    }

    if (requiredCheck.missing.length) {
      parts.push(`\n⚠️ Missing required fields (${requiredCheck.missing.length}):`);
      requiredCheck.missing.slice(0, 5).forEach(item => parts.push(`• ${item}`));
      if (requiredCheck.missing.length > 5) parts.push(`• ... and ${requiredCheck.missing.length - 5} more`);
    }

    ui.alert(parts.join('\n'));
  } catch (err) {
    ui.alert(`Migration failed: ${err.message}`);
    Logger.log('Migration error: %s', err.toString());
  }
}
