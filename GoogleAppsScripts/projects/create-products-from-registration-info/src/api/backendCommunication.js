/**
 * Backend API communication functions
 * Handles all communication with the backend API for product creation and go-live requests
 *
 * @fileoverview Backend API integration
 * @requires ../shared-utilities/secretsUtils.gs
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
      goLiveTime: goLiveTime.toISOString() // Convert to ISO string for backend
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
    
    // Parse response body to extract message
    let responseMessage = 'No message provided';
    try {
      if (responseText && responseText.trim()) {
        const responseData = JSON.parse(responseText);
        responseMessage = responseData.message || responseMessage;
      }
    } catch (parseError) {
      Logger.log(`Warning: Could not parse response as JSON: ${parseError.message}`);
      responseMessage = responseText || responseMessage;
    }
    
    if (responseCode >= 200 && responseCode < 300) {
      // Success response
      SpreadsheetApp.getUi().alert('Success!', responseMessage, SpreadsheetApp.getUi().ButtonSet.OK);
    } else if (responseCode >= 400) {
      // Error response - uncheck checkbox and show error
      const sheet = SpreadsheetApp.getActiveSheet();
      const range = sheet.getActiveRange();
      range.setValue(false);
      
      SpreadsheetApp.getUi().alert('Error', responseMessage, SpreadsheetApp.getUi().ButtonSet.OK);
    } else {
      // Other response codes (300-399) - treat as error
      const sheet = SpreadsheetApp.getActiveSheet();
      const range = sheet.getActiveRange();
      range.setValue(false);
      
      SpreadsheetApp.getUi().alert('Error', `Unexpected response code ${responseCode}: ${responseMessage}`, SpreadsheetApp.getUi().ButtonSet.OK);
    }
    
  } catch (error) {
    Logger.log(`Error sending go-live request: ${error.message}`);
    
    // Uncheck the checkbox on error
    const sheet = SpreadsheetApp.getActiveSheet();
    const range = sheet.getActiveRange();
    range.setValue(false);
    
    SpreadsheetApp.getUi().alert('Error', `Failed to send go-live request: ${error.message}`, SpreadsheetApp.getUi().ButtonSet.OK);
  }
}
