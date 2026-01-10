/**
 * Core Shopify product creation logic ported from product-variant-creation
 * This handles the actual API calls to create products and variants
 *
 * @fileoverview Shopify API integration for product and variant creation
 * @requires ../../shared-utilities/secretsUtils.gs
 * @requires ../../shared-utilities/ShopifyUtils.gs
 */

/**
 * Transform flat productData to structured format expected by backend
 * Must match the exact ProductCreationRequest model structure:
 * - sportName: SportName (required)
 * - regularSeasonBasicDetails: RegularSeasonBasicDetails (required)
 * - optionalLeagueInfo: OptionalLeagueInfo (required)
 * - importantDates: ImportantDates (required)
 * - inventoryInfo: InventoryInfo (required)
 */
function transformProductDataForBackend(productData) {
  // Helper function to convert empty strings to null
  const emptyToNull = (value) => (value === "" || value === undefined) ? null : value;

  // Create the structured payload that matches backend ProductCreationRequest model
  const structuredData = {
    // Required: SportName enum
    sportName: productData.sportName,

    // Required: RegularSeasonBasicDetails object
    regularSeasonBasicDetails: {
      // Required fields
      year: productData.year,
      season: productData.season,
      dayOfPlay: productData.dayOfPlay,
      division: productData.division,
      location: productData.location,
      leagueStartTime: productData.leagueStartTime,
      leagueEndTime: productData.leagueEndTime,

      // Optional fields (convert empty strings to null)
      leagueAssignmentTypes: productData.optionalLeagueInfo?.types || [],
      sportSubCategory: emptyToNull(productData.optionalLeagueInfo?.sportSubCategory),
      socialOrAdvanced: emptyToNull(productData.optionalLeagueInfo?.socialOrAdvanced),
      alternativeStartTime: emptyToNull(productData.alternativeStartTime),
      alternativeEndTime: emptyToNull(productData.alternativeEndTime)
    },

    // Required: OptionalLeagueInfo object
    optionalLeagueInfo: {
      socialOrAdvanced: emptyToNull(productData.optionalLeagueInfo?.socialOrAdvanced),
      sportSubCategory: emptyToNull(productData.optionalLeagueInfo?.sportSubCategory),
      types: productData.optionalLeagueInfo?.types || []
    },

    // Required: ImportantDates object
    importantDates: productData.importantDates || {},

    // Required: InventoryInfo object
    inventoryInfo: productData.inventoryInfo || {}
  };

  Logger.log(`Transformed productData for backend: ${JSON.stringify(structuredData, null, 2)}`);
  return structuredData;
}

/**
 * Main function to create Shopify product from parsed data
 * Sends request to backend API instead of calling Shopify directly
 */
function sendProductInfoToBackendForCreation(productData) {
  try {
    Logger.log(`Creating Shopify product from data: ${JSON.stringify(productData, null, 2)}`);

    // Transform the flat structure to the nested structure expected by backend
    const structuredProductData = transformProductDataForBackend(productData);

    let apiUrl;

    if (ENVIRONMENT.toLowerCase() === 'prod') {
      apiUrl = getSecret('BACKEND_API_URL');
    } else {
      apiUrl = NGROK_URL;
    }

    apiUrl += '/products/create';

    Logger.log(`Sending request to API: ${apiUrl} (environment: ${ENVIRONMENT})`);

    // Send POST request to backend API
    const response = UrlFetchApp.fetch(apiUrl, {
      method: 'POST',
      contentType: 'application/json',
      headers: {
        'Accept': 'application/json'
      },
      payload: JSON.stringify(structuredProductData),
      muteHttpExceptions: true
    });

    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();

    Logger.log(`Backend API response code: ${responseCode}`);
    Logger.log(`Backend API response: ${responseText}`);

    if (responseCode < 300) {
      // Success response (200, 201, 204, etc.)
      let responseData = null;
      if (responseText?.trim()) {
        try {
          responseData = JSON.parse(responseText);
        } catch (parseError) {
          Logger.log(`Warning: Could not parse response as JSON: ${parseError.message}`);
        }
      }

      Logger.log(`✅ Product created successfully: ${JSON.stringify(responseData, null, 2)}`);

      // Show success UI alert
      SpreadsheetApp.getUi().alert('Success! Product created successfully');

      return {
        success: true,
        data: responseData,
        message: 'Product created successfully'
      };
    } else {
      const errorMessage = `Request was sent to back-end server but failed with response code: ${responseCode} \n\n${responseText}`;
      Logger.log(`❌ ${errorMessage}`);
      Logger.log(`Error response: ${responseText}`);

      // Show UI alert with error details
      SpreadsheetApp.getUi().alert(
        `Request was sent to back-end server but failed\n\n${JSON.stringify({
          responseCode: responseCode,
          responseBody: responseText
        }, null, 2)}`
      );

      return {
        success: false,
        error: errorMessage,
        responseCode: responseCode,
        responseBody: responseText
      };
    }

  } catch (error) {
    Logger.log(`Error in sendProductInfoToBackendForCreation: ${error}`);

    // Show UI alert for network/parsing errors
    SpreadsheetApp.getUi().alert(
      `Request was sent to back-end server but failed\n\n${JSON.stringify({
        error: error.message,
        stack: error.stack
      }, null, 2)}`
    );

    return {
      success: false,
      error: error.message
    };
  }
}
