/**
 * Core Shopify product creation logic ported from product-variant-creation
 * This handles the actual API calls to create products and variants
 *
 * @fileoverview Shopify API integration for product and variant creation
 * @requires ../../shared-utilities/secretsUtils.gs
 * @requires ../../shared-utilities/ShopifyUtils.gs
 */

/**
 * Main function to create Shopify product from parsed data
 * Sends request to backend API instead of calling Shopify directly
 */
function sendProductInfoToBackendForCreation(productData) {
  try {
    Logger.log(`Creating Shopify product from data: ${JSON.stringify(productData, null, 2)}`);


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
      payload: JSON.stringify(productData),
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
