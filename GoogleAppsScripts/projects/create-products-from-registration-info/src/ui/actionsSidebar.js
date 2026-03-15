/**
 * Actions Sidebar — server-side GAS functions
 * Opens the sidebar and handles button actions from it
 */

import { createShopifyProductFromRow } from '../core/productCreationOrchestrator.js';
import { parseLeagueBasicInfo } from '../parsers/parseLeagueBasicInfo.js';
import { capitalize } from '../helpers/textUtils.js';
import { getSecret } from '../shared-utilities/secretsUtils.js';

/**
 * Open the Actions sidebar
 */
export function showActionsSidebar() {
  const html = HtmlService.createHtmlOutputFromFile('ActionsSidebar')
    .setTitle('Actions')
    .setWidth(340);
  SpreadsheetApp.getUi().showSidebar(html);
}

/**
 * Called by the sidebar on load — returns all data rows with their state
 */
export function getSidebarRowData() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getActiveSheet();

  const SOURCE_LISTING_START_ROW = 3;
  const lastRow = sheet.getLastRow();
  if (lastRow < SOURCE_LISTING_START_ROW) return [];

  // Row 1: output headers (Product URL etc.)
  const row1Headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const productUrlCol = row1Headers.findIndex(h => h.toString().trim() === 'Product URL');
  const productUrlColIdx = productUrlCol !== -1 ? productUrlCol : 16; // 0-based

  const dataStartRow = SOURCE_LISTING_START_ROW + 1;
  const values = sheet.getRange(dataStartRow, 1, lastRow - SOURCE_LISTING_START_ROW, Math.max(21, productUrlColIdx + 1))
    .getDisplayValues();

  let lastA = '';
  const rows = [];

  for (let i = 0; i < values.length; i++) {
    const sheetRow = dataStartRow + i;
    const rowValues = values[i];

    const aRaw = (rowValues[0] || '').trim();
    const bRaw = (rowValues[1] || '').trim();
    if (aRaw) lastA = aRaw;
    if (!bRaw) continue;

    const sportName = capitalize(lastA, true);
    const { dayOfPlay, division } = parseLeagueBasicInfo(bRaw, sportName);
    const productUrl = (rowValues[productUrlColIdx] || '').toString().trim();

    rows.push({
      row: sheetRow,
      label: `${sportName} — ${dayOfPlay} — ${division}`,
      hasProduct: productUrl.length > 0,
      productUrl: productUrl
    });
  }

  return rows;
}

/**
 * Create product for a given row — called from sidebar
 */
export function sidebarCreateProduct(rowNumber) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getActiveSheet();
  createShopifyProductFromRow(sheet, rowNumber);
}

/**
 * Delete product for a given row — calls Shopify productDelete, then clears sheet cells
 */
export function sidebarDeleteProduct(rowNumber) {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getActiveSheet();

  // Find output columns by header name in row 1
  const lastCol = sheet.getLastColumn();
  const headers = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  const colIndex = function(name) {
    const idx = headers.findIndex(function(h) { return h.toString().trim() === name; });
    return idx !== -1 ? idx + 1 : -1;
  };

  const productUrlCol = colIndex('Product URL');
  if (productUrlCol === -1) {
    ui.alert('Cannot find "Product URL" column in row 1.');
    return;
  }

  const productUrl = sheet.getRange(rowNumber, productUrlCol).getValue().toString().trim();
  if (!productUrl) {
    ui.alert('No Product URL found for this row.');
    return;
  }

  // Extract numeric product ID from URL
  const idMatch = productUrl.match(/\/products\/(\d+)/);
  if (!idMatch) {
    ui.alert(`Could not parse product ID from URL:\n${productUrl}`);
    return;
  }
  const productGid = `gid://shopify/Product/${idMatch[1]}`;

  const confirm = ui.alert(
    '⚠️ Confirm Delete',
    `This will permanently delete the Shopify product and clear all IDs from row ${rowNumber}.\n\nProduct: ${productUrl}\n\nThis cannot be undone. Are you sure?`,
    ui.ButtonSet.OK_CANCEL
  );
  if (confirm !== ui.Button.OK) return;

  // Call Shopify productDelete
  const mutation = JSON.stringify({
    query: `mutation productDelete($input: ProductDeleteInput!) {
      productDelete(input: $input) {
        deletedProductId
        userErrors { field message }
      }
    }`,
    variables: { input: { id: productGid } }
  });

  let response;
  try {
    response = UrlFetchApp.fetch(getSecret('SHOPIFY_GRAPHQL_URL'), {
      method: 'post',
      contentType: 'application/json',
      headers: { 'X-Shopify-Access-Token': getSecret('SHOPIFY_ACCESS_TOKEN') },
      payload: mutation,
      muteHttpExceptions: true
    });
  } catch (e) {
    ui.alert(`❌ Network error deleting product: ${e.message}`);
    return;
  }

  let data;
  try {
    data = JSON.parse(response.getContentText());
  } catch (_e) {
    ui.alert('❌ Could not parse Shopify delete response.');
    return;
  }

  Logger.log(`productDelete response: ${JSON.stringify(data)}`);

  if (data.errors && data.errors.length) {
    ui.alert(`❌ Shopify error:\n${data.errors.map(function(e) { return e.message; }).join('\n')}`);
    return;
  }

  const userErrors = (data.data && data.data.productDelete && data.data.productDelete.userErrors) || [];
  if (userErrors.length) {
    ui.alert(`❌ Delete failed:\n${userErrors.map(function(e) { return e.field + ': ' + e.message; }).join('\n')}`);
    return;
  }

  // Clear output columns from sheet
  const outputCols = [
    colIndex('Product URL'),
    colIndex('Vet Registration Variant ID'),
    colIndex('Early Registration Variant ID'),
    colIndex('Open Registration Variant ID'),
    colIndex('Waitlist Registration Variant ID'),
  ].filter(function(c) { return c !== -1; });

  for (const col of outputCols) {
    sheet.getRange(rowNumber, col).clearContent();
  }

  Logger.log(`✅ Deleted product ${productGid} and cleared row ${rowNumber} output columns`);
}

/**
 * Update product for a given row — stub
 */
export function sidebarUpdateProduct(rowNumber) {
  SpreadsheetApp.getUi().alert(`Update not yet implemented for row ${rowNumber}.`);
}
