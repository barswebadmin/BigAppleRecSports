/**
 * LEGACY: Backend API communication functions
 * This file is kept for reference but is NOT included in the build/deployment
 * The project now sends directly to Shopify instead of using a backend API
 *
 * @fileoverview Legacy backend API integration (not deployed)
 */

/**
 * Send go-live request to backend API
 */
function sendGoLiveRequest_(productUrl, goLiveTime) {
  try {
    let apiUrl;
    
    if (ENVIRONMENT.toLowerCase() === 'prod') {
      apiUrl = getSecret('BACKEND_API_URL');
    } else {
      apiUrl = NGROK_URL;
    }
    
    apiUrl += '/products/setGoLive/create';
    
    const payload = {
      productUrl: productUrl,
      goLiveTime: goLiveTime.toISOString()
    };
    
    Logger.log(`Sending go-live request to: ${apiUrl}`);
    Logger.log(`Payload: ${JSON.stringify(payload, null, 2)}`);
    
    const response = UrlFetchApp.fetch(apiUrl, {
      method: 'POST',
      contentType: 'application/json',
      headers: {
        'Accept': 'application/json'
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });
    
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    Logger.log(`Go-live API response code: ${responseCode}`);
    Logger.log(`Go-live API response: ${responseText}`);
    
    let responseMessage = 'No message provided';
    try {
      if (responseText?.trim()) {
        const responseData = JSON.parse(responseText);
        responseMessage = responseData.message || responseMessage;
      }
    } catch (parseError) {
      Logger.log(`Warning: Could not parse response as JSON: ${parseError.message}`);
      responseMessage = responseText || responseMessage;
    }
    
    if (responseCode >= 200 && responseCode < 300) {
      SpreadsheetApp.getUi().alert('Success!', responseMessage, SpreadsheetApp.getUi().ButtonSet.OK);
    } else if (responseCode >= 400) {
      const sheet = SpreadsheetApp.getActiveSheet();
      const range = sheet.getActiveRange();
      range.setValue(false);
      
      SpreadsheetApp.getUi().alert('Error', responseMessage, SpreadsheetApp.getUi().ButtonSet.OK);
    } else {
      const sheet = SpreadsheetApp.getActiveSheet();
      const range = sheet.getActiveRange();
      range.setValue(false);
      
      SpreadsheetApp.getUi().alert('Error', `Unexpected response code ${responseCode}: ${responseMessage}`, SpreadsheetApp.getUi().ButtonSet.OK);
    }
    
  } catch (error) {
    Logger.log(`Error sending go-live request: ${error.message}`);
    
    const sheet = SpreadsheetApp.getActiveSheet();
    const range = sheet.getActiveRange();
    range.setValue(false);
    
    SpreadsheetApp.getUi().alert('Error', `Failed to send go-live request: ${error.message}`, SpreadsheetApp.getUi().ButtonSet.OK);
  }
}

/**
 * Transform flat productData to structured format expected by backend
 */
function transformProductDataForBackend(productData) {
  const emptyToNull = (value) => (value === "" || value === undefined) ? null : value;

  const structuredData = {
    sportName: productData.sportName,
    regularSeasonBasicDetails: {
      year: productData.year,
      season: productData.season,
      dayOfPlay: productData.dayOfPlay,
      division: productData.division,
      location: productData.location,
      leagueStartTime: productData.leagueStartTime,
      leagueEndTime: productData.leagueEndTime,
      leagueAssignmentTypes: productData.optionalLeagueInfo?.types || [],
      sportSubCategory: emptyToNull(productData.optionalLeagueInfo?.sportSubCategory),
      socialOrAdvanced: emptyToNull(productData.optionalLeagueInfo?.socialOrAdvanced),
      alternativeStartTime: emptyToNull(productData.alternativeStartTime),
      alternativeEndTime: emptyToNull(productData.alternativeEndTime)
    },
    optionalLeagueInfo: {
      socialOrAdvanced: emptyToNull(productData.optionalLeagueInfo?.socialOrAdvanced),
      sportSubCategory: emptyToNull(productData.optionalLeagueInfo?.sportSubCategory),
      types: productData.optionalLeagueInfo?.types || []
    },
    importantDates: productData.importantDates || {},
    inventoryInfo: productData.inventoryInfo || {}
  };

  Logger.log(`Transformed productData for backend: ${JSON.stringify(structuredData, null, 2)}`);
  return structuredData;
}

/**
 * Send product info to backend for creation
 */
function sendProductInfoToBackendForCreation(productData) {
  try {
    Logger.log(`Creating Shopify product from data: ${JSON.stringify(productData, null, 2)}`);

    const structuredProductData = transformProductDataForBackend(productData);

    let apiUrl;

    if (ENVIRONMENT.toLowerCase() === 'prod') {
      apiUrl = getSecret('BACKEND_API_URL');
    } else {
      apiUrl = NGROK_URL;
    }

    apiUrl += '/products/create';

    Logger.log(`Sending request to API: ${apiUrl} (environment: ${ENVIRONMENT})`);

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
      let responseData = null;
      if (responseText?.trim()) {
        try {
          responseData = JSON.parse(responseText);
        } catch (parseError) {
          Logger.log(`Warning: Could not parse response as JSON: ${parseError.message}`);
        }
      }

      Logger.log(`✅ Product created successfully: ${JSON.stringify(responseData, null, 2)}`);
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
