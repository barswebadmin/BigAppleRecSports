/**
 * Main product creation orchestrator
 * Coordinates the entire product creation workflow from parsing to creation
 *
 * @fileoverview Main orchestrator for product creation workflow
 * @requires ../data/productDataProcessing.gs
 * @requires ../ui/productCreationDialogs.gs
 * @requires ../sheet/cellMapping.gs
 * @requires ../api/backendCommunication.gs
 * @requires ../core/portedFromProductCreateSheet/shopifyProductCreation.gs
 * @requires ../helpers/normalizers.gs
 */

/**
 * Main function to create Shopify product from a selected row
 * This is the entry point called from the menu
 */
function createShopifyProductFromRow_(sourceSheet, selectedRow) {
  const ui = SpreadsheetApp.getUi();

  // Read and parse the row data
  const parseResult = parseRowDataForProductCreation_(sourceSheet, selectedRow);
  if (!parseResult || !parseResult.parsedData) {
    ui.alert('Failed to parse row data for product creation.');
    return;
  }

  const { parsedData, cellMapping, sourceSheet: sheet, rowNumber } = parseResult;
  const unresolvedFields = calculateUnresolvedFieldsForParsedData(parsedData);

  // Show confirmation dialog with editable fields
  Logger.log(`About to show confirmation dialog with product data: ${JSON.stringify(parsedData, null, 2)}`);
  const confirmedData = showProductCreationConfirmationDialog_(parsedData, unresolvedFields, cellMapping, sheet, rowNumber);
  if (!confirmedData) {
    return; // User cancelled
  }

  // Create the product and variants
  try {
    // Validate and canonicalize nested request structure just before sending
    const validNested = validProductCreateRequest_(confirmedData);
    Logger.log(`About to send confirmed data to backend (nested): ${JSON.stringify(validNested, null, 2)}`);
    const result = sendProductInfoToBackendForCreation(validNested);

    if (result.success) {
      // Write the results back to the sheet
      writeProductCreationResults_(sheet, rowNumber, result);

      ui.alert(`✅ Product created successfully!\n\nProduct URL: ${result.data?.productUrl || 'N/A'}\n\nVariants created:\n${result.data ? Object.keys(result.data).filter(k => k.includes('Variant')).join(', ') : 'N/A'}`);
    } else {
      ui.alert(`❌ Product creation failed:\n\n${result.error}`);
    }

  } catch (error) {
    Logger.log(`Error in sendProductInfoToBackendForCreation: ${error}`);
    ui.alert('Error', `Failed to create product: ${error.message}`, ui.ButtonSet.OK);
  }
}
