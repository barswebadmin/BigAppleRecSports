/**
 * Enhanced Google Sheets client for direct product tab management
 * Uses pre-defined column indexes for maximum performance
 */

import { CONFIG, getFieldIndex } from '../config.js';
import { SlackClient } from './SlackClient.js';

export class SheetsClient {
  constructor(spreadsheetId, columnMap, headerRow = 1) {
    this.spreadsheetId = spreadsheetId;
    this.columnMap = columnMap; // Raw header -> {dataField, index}
    this.headerRow = headerRow;
    this.spreadsheet = null; // Lazy load
    this.productDataCache = new Map();
  }

  /**
   * Initialize the spreadsheet connection (lazy loading)
   */
  getSpreadsheet() {
    if (!this.spreadsheet) {
      this.spreadsheet = SpreadsheetApp.openById(this.spreadsheetId);
    }
    return this.spreadsheet;
  }


  /**
   * Get the sheet for a specific product using static mapping
   * @param {string} productId - Product ID
   * @returns {GoogleAppsScript.Spreadsheet.Sheet} The product sheet
   */
  getProductSheet(productId) {
    const spreadsheet = this.getSpreadsheet();

    const tabName = CONFIG.PRODUCT_TAB_MAPPING[productId];
    if (!tabName) {
      throw new Error(`No tab mapping found for productId: ${productId}. Add to CONFIG.PRODUCT_TAB_MAPPING`);
    }

    const sheet = spreadsheet.getSheetByName(tabName);
    if (!sheet) {
      throw new Error(`Tab "${tabName}" not found for productId: ${productId}`);
    }

    return sheet;
  }

  /**
   * Get structured data for a specific product using direct column access
   * @param {string} productId - Product ID to get data for
   * @returns {Object} {entries: Array, byEmail: Map, byCustomerId: Map}
   */
  getProductData(productId) {
    const slackClient = new SlackClient();

    // Check cache first
    if (this.productDataCache.has(productId)) {
      slackClient.sendVariableState('SheetsClient.getProductData Cache Hit', {
        productId,
        cached: true
      });
      return this.productDataCache.get(productId);
    }

    slackClient.sendStepStart('SheetsClient.getProductData', {
      productId,
      spreadsheetId: this.spreadsheetId,
      cached: false
    });

    try {
      // Step 1: Get the sheet
      slackClient.sendStepStart('Get Product Sheet', { productId });

      const sheet = this.getProductSheet(productId);
      const tabName = CONFIG.PRODUCT_TAB_MAPPING[productId];

      slackClient.sendStepSuccess('Get Product Sheet',
        { tabName, sheetExists: !!sheet },
        { productId }
      );

      // Step 2: Get raw data
      slackClient.sendStepStart('Get Sheet Data Range', { productId, tabName });

      const rawData = sheet.getDataRange().getValues();

      slackClient.sendStepSuccess('Get Sheet Data Range',
        { totalRows: rawData?.length || 0, totalColumns: rawData?.[0]?.length || 0 },
        { productId, tabName }
      );

      if (!rawData || rawData.length <= this.headerRow) {
        const emptyData = { entries: [], byEmail: new Map(), byCustomerId: new Map() };
        this.productDataCache.set(productId, emptyData);

        slackClient.sendStepSuccess('SheetsClient.getProductData',
          { result: 'empty_sheet', cached: true },
          { productId, tabName, totalRows: rawData?.length || 0 }
        );

        return emptyData;
      }

      // Step 3: Parse data
      slackClient.sendStepStart('Parse Sheet Data', {
        productId,
        totalRows: rawData.length,
        headerRow: this.headerRow
      });

      // Parse data using direct column access - no header mapping needed!
      const entries = [];
      const byEmail = new Map();
      const byCustomerId = new Map();

      for (let rowIndex = this.headerRow + 1; rowIndex < rawData.length; rowIndex++) {
        const rawRow = rawData[rowIndex];

        // Stop when first column (ID) is empty
        const idIndex = getFieldIndex('id');
        if (!rawRow[idIndex] || rawRow[idIndex] === '') {
          break;
        }

        // Dynamic array access using field mapping
        const parsedRow = { _rowIndex: rowIndex + 1 };
        for (const [, { dataField }] of Object.entries(this.columnMap)) {
          const index = getFieldIndex(dataField);
          parsedRow[dataField] = rawRow[index] || null;
        }

        entries.push(parsedRow);

        // Build lookup maps for performance
        if (parsedRow.email) {
          const emailLower = parsedRow.email.toString().toLowerCase().trim();
          byEmail.set(emailLower, parsedRow);
        }

        if (parsedRow.customerId) {
          const customerIdTrim = parsedRow.customerId.toString().trim();
          byCustomerId.set(customerIdTrim, parsedRow);
        }
      }

      slackClient.sendStepSuccess('Parse Sheet Data',
        {
          entriesParsed: entries.length,
          emailLookupSize: byEmail.size,
          customerIdLookupSize: byCustomerId.size
        },
        { productId, tabName }
      );

      const productData = { entries, byEmail, byCustomerId };
      this.productDataCache.set(productId, productData);

      slackClient.sendStepSuccess('SheetsClient.getProductData',
        {
          entriesCount: entries.length,
          emailLookups: byEmail.size,
          customerIdLookups: byCustomerId.size,
          cached: true
        },
        { productId, tabName }
      );

      return productData;

    } catch (error) {
      slackClient.sendStepFailure('SheetsClient.getProductData', error,
        { productId, spreadsheetId: this.spreadsheetId },
        { step: 'get_product_data' }
      );
      throw new Error(`Failed to get data for product ${productId}: ${error.message}`);
    }
  }

  /**
   * Get all data across all products (for admin/debugging use)
   * @returns {Map<string, Object>} Map of productId -> product data
   */
  getAllProductsData() {
    const allData = new Map();

    for (const productId of Object.keys(CONFIG.PRODUCT_TAB_MAPPING)) {
      try {
        const productData = this.getProductData(productId);
        allData.set(productId, productData);
      } catch (error) {
        console.warn(`Failed to load data for product ${productId}: ${error.message}`);
      }
    }

    return allData;
  }

  /**
   * Insert a new waitlist entry using direct column access
   * @param {string} productId - Product ID
   * @param {Object} entryData - The entry data to insert
   * @returns {Object} {position: number, rowNumber: number}
   */
  insertWaitlistEntry(productId, entryData) {
    const slackClient = new SlackClient();

    slackClient.sendStepStart('SheetsClient.insertWaitlistEntry', {
      productId,
      entryData: {
        firstName: entryData.firstName,
        lastName: entryData.lastName,
        email: entryData.email ? '[REDACTED]' : null,
        phone: entryData.phone ? '[REDACTED]' : null,
        customerId: entryData.customerId,
        productId: entryData.productId,
        productName: entryData.productName
      }
    });

    try {
      // Step 1: Get the sheet
      slackClient.sendStepStart('Get Product Sheet for Insert', { productId });

      const sheet = this.getProductSheet(productId);
      const tabName = CONFIG.PRODUCT_TAB_MAPPING[productId];

      slackClient.sendStepSuccess('Get Product Sheet for Insert',
        { tabName, sheetExists: !!sheet },
        { productId }
      );

      // Step 2: Get current data to determine position
      slackClient.sendStepStart('Get Current Product Data for Position', { productId });

      const productData = this.getProductData(productId);
      const currentEntries = productData.entries;

      slackClient.sendStepSuccess('Get Current Product Data for Position',
        { currentEntriesCount: currentEntries.length },
        { productId, tabName }
      );

      // Step 3: Calculate position and row
      const position = currentEntries.length + 1;
      const nextRowNumber = this.headerRow + 1 + currentEntries.length + 1;

      slackClient.sendVariableState('Position Calculation', {
        currentEntries: currentEntries.length,
        calculatedPosition: position,
        nextRowNumber,
        headerRow: this.headerRow
      });

      // Step 4: Build row data
      slackClient.sendStepStart('Build Row Data', {
        productId,
        position,
        columnMapSize: Object.keys(this.columnMap).length
      });

      const allIndexes = Object.values(this.columnMap).map(col => col.index);
      const maxIndex = Math.max(...allIndexes);
      const rowData = new Array(maxIndex + 1).fill(null);

      // Auto-generate ID (position)
      entryData.id = position;

      // Dynamic column assignment using field mapping
      let fieldsAssigned = 0;
      for (const [field, value] of Object.entries(entryData)) {
        const index = getFieldIndex(field);
        if (index !== -1) {
          rowData[index] = value || null;
          fieldsAssigned++;
        }
      }

      slackClient.sendStepSuccess('Build Row Data',
        {
          maxIndex,
          rowDataLength: rowData.length,
          fieldsAssigned,
          totalFields: Object.keys(entryData).length
        },
        { productId, position }
      );

      // Step 5: Insert the row
      slackClient.sendStepStart('Insert Row to Sheet', {
        productId,
        tabName,
        nextRowNumber,
        rowDataLength: rowData.length,
        position
      });

      const range = sheet.getRange(nextRowNumber, 1, 1, rowData.length);
      range.setValues([rowData]);

      slackClient.sendStepSuccess('Insert Row to Sheet',
        { success: true, rowInserted: nextRowNumber },
        { productId, tabName, position }
      );

      // Step 6: Clear cache
      slackClient.sendStepStart('Clear Product Cache', { productId });

      this.productDataCache.delete(productId);

      slackClient.sendStepSuccess('Clear Product Cache', { success: true }, { productId });

      const result = { position, rowNumber: nextRowNumber };

      slackClient.sendStepSuccess('SheetsClient.insertWaitlistEntry',
        { result },
        { productId, tabName }
      );

      return result;

    } catch (error) {
      slackClient.sendStepFailure('SheetsClient.insertWaitlistEntry', error,
        {
          productId,
          entryData: {
            firstName: entryData.firstName,
            lastName: entryData.lastName,
            hasEmail: !!entryData.email,
            hasPhone: !!entryData.phone,
            customerId: entryData.customerId,
            productName: entryData.productName
          }
        },
        { step: 'insert_waitlist_entry' }
      );
      throw new Error(`Failed to insert entry for product ${productId}: ${error.message}`);
    }
  }

  /**
   * Update a cell value in a specific product sheet
   * @param {string} productId - Product ID
   * @param {number} row - Row number (1-based)
   * @param {number} column - Column number (1-based)
   * @param {any} value - Value to set
   */
  updateCell(productId, row, column, value) {

    try {
      const sheet = this.getProductSheet(productId);
      sheet.getRange(row, column).setValue(value);

      // Clear cache for this product
      this.productDataCache.delete(productId);
    } catch (error) {
      throw new Error(`Failed to update cell for product ${productId}: ${error.message}`);
    }
  }

  /**
   * Update status of a specific entry using direct column access
   * @param {string} productId - Product ID
   * @param {number} rowIndex - Row index (1-based)
   * @param {string} status - New status value
   */
  updateEntryStatus(productId, rowIndex, status) {

    try {
      const sheet = this.getProductSheet(productId);

      // Dynamic column access using field mapping
      const statusColumnIndex = getFieldIndex('status') + 1; // Convert to 1-based

      sheet.getRange(rowIndex, statusColumnIndex).setValue(status);

      // Clear cache for this product
      this.productDataCache.delete(productId);

    } catch (error) {
      throw new Error(`Failed to update status for product ${productId}: ${error.message}`);
    }
  }

  /**
   * Get product tab mapping for debugging
   * @returns {Map<string, string>} productId -> tabName mapping
   */
  getProductTabMapping() {
    return new Map(Object.entries(CONFIG.PRODUCT_TAB_MAPPING));
  }

  /**
   * Clear all caches
   */
  clearCache() {
    this.productDataCache.clear();
  }
}