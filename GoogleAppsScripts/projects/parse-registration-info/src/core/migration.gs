/**
 * Migration logic for parse-registration-info
 * Handles the actual data transfer to target spreadsheet
 *
 * @fileoverview Migration workflow and data transfer
 * @requires ../config/constants.gs
 * @requires ../validators/fieldValidation.gs
 * @requires ../helpers/textUtils.gs
 * @requires rowParser.gs
 */

// Import references for editor support
/// <reference path="../config/constants.gs" />
/// <reference path="../validators/fieldValidation.gs" />
/// <reference path="../helpers/textUtils.gs" />
/// <reference path="rowParser.gs" />

/**
 * Main migration function - transfers a parsed row to target sheet
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sourceSheet - Source spreadsheet
 * @param {number} row - Row number to migrate
 * @returns {{unresolved: Array<string>, requiredCheck: Object, cancel: boolean}} Migration result
 */
function migrateRowToTarget_(sourceSheet, row) {
  const ui = SpreadsheetApp.getUi();

  // Destination tab from A1
  const destTabName = (sourceSheet.getRange('A1').getDisplayValue() || '').trim();
  if (!destTabName) throw new Error('Cell A1 (destination tab name) is blank.');

  const targetSs = SpreadsheetApp.openById(TARGET_SPREADSHEET_ID);
  const targetSheet = targetSs.getSheetByName(destTabName);
  if (!targetSheet) {
    ui.alert(
      'Tab Not Found',
      `The value in A1 "${destTabName}" cannot be found as a tab in the Google Sheet "BARS 2025 Product and Variant Creation".\n\n` +
      `URL: https://docs.google.com/spreadsheets/d/${TARGET_SPREADSHEET_ID}/edit`,
      ui.ButtonSet.OK
    );
    throw new Error(`Destination tab "${destTabName}" not found.`);
  }

  // Read source row columns A..O
  function getFilledDownA_(sheet, row, stopAtRow = 4) {
    for (let r = row; r >= stopAtRow; r--) {
      const v = sheet.getRange(r, 1).getDisplayValue().trim();
      if (v) return v;
    }
    return '';
  }

  const rowValues = sourceSheet.getRange(row, 1, 1, 15).getDisplayValues()[0];
  const vals = {
    A: getFilledDownA_(sourceSheet, row), // respects merged A cells (Bowling/Kickball/Dodgeball/Pickleball)
    B: (rowValues[1] || '').toString(), // day + flags
    C: (rowValues[2] || '').toString(), // league details (notes)
    D: (rowValues[3] || '').toString(), // season start
    E: (rowValues[4] || '').toString(), // season end
    F: (rowValues[5] || '').toString(), // price
    G: (rowValues[6] || '').toString(), // times
    H: (rowValues[7] || '').toString(), // location
    M: (rowValues[12] || '').toString(), // early reg (WTNB/BIPOC/TNB register)
    N: (rowValues[13] || '').toString(), // vet reg
    O: (rowValues[14] || '').toString(), // open reg
  };

  const unresolved = [];
  const parsed = parseSourceRowEnhanced_(vals, unresolved);

  Logger.log('Source row %s — raw vals:\n%s', row, JSON.stringify(vals, null, 2));
  Logger.log('Parsed values (pretty):\n%s', JSON.stringify(parsed, null, 2));

  const nonEmptyKeys = Object.keys(parsed).filter(k => parsed[k] !== '' && parsed[k] != null);
  if (nonEmptyKeys.length < 3) { // threshold: tune as you like
    Logger.log('Parsed looks too empty; aborting write. Parsed:\n%s', JSON.stringify(parsed, null, 2));
    throw new Error('Parsed row looks empty — aborting to avoid overwriting with blanks.');
  }

  // Map to target columns by header
  const targetHeadersRaw = targetSheet
    .getRange(TARGET_HEADER_ROW, 1, 1, targetSheet.getLastColumn())
    .getDisplayValues()[0];

  // Build fuzzy index over target headers
  const headerIdx = buildFuzzyHeaderIndex_(targetHeadersRaw);

  // Ready column (fuzzy, stricter threshold)
  const readyLookup = headerIdx.bestFor('Ready to Create Product?', { threshold: 0.80 });
  const readyColIdx1Based = readyLookup ? readyLookup.col : null;
  Logger.log('Ready col (1-based): %s ; matched "%s" @ score=%.2f',
            readyColIdx1Based || 'n/a',
            readyLookup ? readyLookup.raw : 'n/a',
            readyLookup ? readyLookup.score : -1);

  // Map each desired target header → matched column (1-based) using fuzzy lookup
  const colForHeader = {};
  const unresolvedLocal = [];
  const mappingDebug = [];

  for (const [targetHeader, objectKey] of Object.entries(headerMapping)) {
    const hit = headerIdx.bestFor(targetHeader, { threshold: 0.72 });
    mappingDebug.push({
      targetHeader,
      objectKey,
      matched: hit ? hit.raw : 'none',
      score: hit ? hit.score.toFixed(2) : 'n/a',
      col: hit ? hit.col : 'n/a'
    });
    if (hit) {
      colForHeader[targetHeader] = hit.col;
    } else {
      unresolvedLocal.push(`Header not found in target: "${targetHeader}"`);
    }
  }

  Logger.log('Header mapping debug:\n%s', JSON.stringify(mappingDebug, null, 2));

  // Check required fields
  const requiredCheck = checkRequiredFields_(parsed, targetHeadersRaw, unresolved);

  // Find or create target row
  const targetMap = getTargetIndexMap_(targetSheet, TARGET_HEADER_ROW);
  const key = makeKey_(parsed.sport, parsed.day, parsed.division);
  let targetRowIdx = null;

  const existing = targetMap.get(key);
  if (existing) {
    targetRowIdx = existing.row;
    Logger.log(`Found existing row ${targetRowIdx} for key "${key}"`);

    // Confirm overwrite if it's marked ready
    if (existing.readyTrue) {
      const confirmResp = ui.alert(
        'Overwrite Ready Row?',
        `Row ${targetRowIdx} is marked "Ready to Create Product" = TRUE. Overwrite anyway?`,
        ui.ButtonSet.YES_NO
      );
      if (confirmResp !== ui.Button.YES) {
        return { unresolved, requiredCheck, cancel: true };
      }
    }
  } else {
    // Append new row
    targetRowIdx = targetSheet.getLastRow() + 1;
    Logger.log(`Creating new row ${targetRowIdx} for key "${key}"`);
  }

  // Write data to target sheet with validation check
  const targetRange = targetSheet.getRange(targetRowIdx, 1, 1, targetSheet.getLastColumn());
  const currentValues = targetRange.getValues()[0];
  const originalValues = [...currentValues]; // Keep copy for comparison

  const writeAttempts = [];
  const writeFailures = [];

  for (const [targetHeader, objectKey] of Object.entries(headerMapping)) {
    const colIdx1Based = colForHeader[targetHeader];
    if (!colIdx1Based) continue; // header not found

    const val = parsed[objectKey];
    if (val !== '' && val != null) {
      writeAttempts.push({
        header: targetHeader,
        column: colIdx1Based,
        oldValue: currentValues[colIdx1Based - 1],
        newValue: val,
        objectKey: objectKey
      });
      currentValues[colIdx1Based - 1] = val;
    }
  }

  // Attempt to write values
  try {
    targetRange.setValues([currentValues]);

    // Verify the write succeeded by reading back the values
    const writtenValues = targetRange.getValues()[0];

    // Check each attempted write
    for (const attempt of writeAttempts) {
      const actualValue = writtenValues[attempt.column - 1];
      const expectedValue = attempt.newValue;

      if (actualValue !== expectedValue) {
        writeFailures.push({
          header: attempt.header,
          column: attempt.column,
          expected: expectedValue,
          actual: actualValue,
          objectKey: attempt.objectKey,
          reason: `Data validation or formatting rule rejected the value`
        });
      }
    }

    Logger.log(`Migration attempted to row ${targetRowIdx}. Successful writes: ${writeAttempts.length - writeFailures.length}/${writeAttempts.length}`);
    if (writeFailures.length > 0) {
      Logger.log(`Write failures: ${JSON.stringify(writeFailures, null, 2)}`);
    }

  } catch (writeError) {
    Logger.log(`Error writing to target sheet: ${writeError.message}`);
    writeFailures.push({
      header: 'ALL_FIELDS',
      reason: `Failed to write to sheet: ${writeError.message}`,
      error: writeError.message
    });
  }

  return {
    unresolved: [...unresolved, ...unresolvedLocal],
    requiredCheck,
    cancel: false,
    writeAttempts: writeAttempts,
    writeFailures: writeFailures,
    targetRow: targetRowIdx
  };
}
