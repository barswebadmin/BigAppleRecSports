/**
 * Main entry point and menu for parse-registration-info
 * User interface and migration workflow
 * 
 * @fileoverview Main controller for parse-registration-info
 * @requires config/constants.gs
 * @requires core/migration.gs
 * @requires core/flagsParser.gs
 * @requires helpers/textUtils.gs
 * @requires validators/fieldValidation.gs
 */

// Import references for editor support
/// <reference path="config/constants.gs" />
/// <reference path="core/migration.gs" />
/// <reference path="core/flagsParser.gs" />
/// <reference path="helpers/textUtils.gs" />
/// <reference path="validators/fieldValidation.gs" />
/// <reference path="instructions.gs" />

/***** MENU *****/
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📊 BARS Sport Registration Parser')
    .addItem('🔄 Migrate Row to Product Creation Sheet', 'showMigrationPrompt')
    .addSeparator()
    .addItem('📘 View Instructions', 'showInstructions')
    .addToUi();
    
  // Show instructions on first open
  showInstructions();
}

/***** ENTRY POINT *****/
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
    const { unresolved, requiredCheck, cancel } = migrateRowToTarget_(sourceSheet, selectedRow);
    if (cancel) return ui.alert('Canceled')

    const parts = [`Migration of row ${selectedRow} completed successfully.`];
    if (unresolved.length) {
      parts.push(`\n⚠️ Unresolved items (${unresolved.length}):`);
      unresolved.slice(0, 10).forEach(item => parts.push(`• ${item}`));
      if (unresolved.length > 10) parts.push(`• ... and ${unresolved.length - 10} more`);
    }
    if (requiredCheck.missing.length) {
      parts.push(`\n⚠️ Missing required fields (${requiredCheck.missing.length}):`);
      requiredCheck.missing.slice(0, 10).forEach(item => parts.push(`• ${item}`));
      if (requiredCheck.missing.length > 10) parts.push(`• ... and ${requiredCheck.missing.length - 10} more`);
    }
    ui.alert(parts.join('\n'));
  } catch (err) {
    ui.alert(`Migration failed: ${err.message}`);
    Logger.log('Migration error: %s', err.toString());
  }
}
