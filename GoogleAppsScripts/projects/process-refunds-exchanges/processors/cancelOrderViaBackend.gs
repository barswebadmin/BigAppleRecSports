/**
 * Send cancel order request to backend API
 * This function sends JSON payload to the backend for complete order cancellation processing
 * 
 * @param {Object} requestData - Data from Slack button click
 * @param {string} channelId - Slack channel ID  
 * @param {string} threadTs - Slack thread timestamp
 * @param {string} slackUserName - User who clicked the button
 */
function cancelOrderViaBackend(requestData, channelId, threadTs, slackUserName) {
  try {
    Logger.log(`🚀 === CANCEL ORDER VIA BACKEND ===`);
    Logger.log(`📋 Request Data: ${JSON.stringify(requestData, null, 2)}`);
    Logger.log(`👤 Slack User: ${slackUserName}`);
    Logger.log(`📍 Channel: ${channelId}, Thread: ${threadTs}`);

    // Extract data from Slack button click
    const { 
      rawOrderNumber, 
      refundType, 
      requestorEmail,
      first: requestorFirstName,
      last: requestorLastName,
      email,
      requestSubmittedAt 
    } = requestData;

    // Construct requestor name object
    const requestorName = {
      first: requestorFirstName || 'Unknown',
      last: requestorLastName || 'User'
    };

    // Get sheet link for reference
    const formattedOrderNumber = normalizeOrderNumber(rawOrderNumber);
    const sheetLink = getRowLink(formattedOrderNumber, SHEET_ID, SHEET_GID);

    // Construct Slack webhook payload format (matching real Slack webhooks)
    const slackPayload = {
      type: "block_actions",
      user: {
        id: "U_GAS_USER", // Placeholder since this comes from Google Apps Script
        name: slackUserName.replace('<@', '').replace('>', '') // Clean up user name
      },
      actions: [{
        action_id: "cancel_order",
        value: `rawOrderNumber=${rawOrderNumber}|refundType=${refundType}|requestorEmail=${requestorEmail || email}|first=${requestorFirstName}|last=${requestorLastName}|requestSubmittedAt=${requestSubmittedAt}`
      }],
      channel: {
        id: channelId
      },
      message: {
        ts: threadTs
      }
    };

    // Enhanced request logging
    Logger.log(`🚀 === BACKEND API REQUEST (CANCEL ORDER) ===`);
    Logger.log(`🌐 Target URL: ${API_URL}/slack/interactions`);
    Logger.log(`📦 Slack Payload:`);
    Logger.log(JSON.stringify(slackPayload, null, 2));
    
    // Format as form data (like real Slack webhooks)
    const formPayload = `payload=${encodeURIComponent(JSON.stringify(slackPayload))}`;
    
    const options = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'ngrok-skip-browser-warning': 'true'  // For local tunnel testing
      },
      payload: formPayload,
      muteHttpExceptions: true  // Prevent exceptions on non-200 status codes
    };
    
    Logger.log(`🔧 Request Options:`);
    Logger.log(`   Method: ${options.method}`);
    Logger.log(`   Headers: ${JSON.stringify(options.headers)}`);
    Logger.log(`   Form Payload Size: ${options.payload.length} characters`);
    Logger.log(`   Form Payload Preview: ${formPayload.substring(0, 200)}...`);
    
    Logger.log(`📡 Sending cancel order request to backend...`);
    const response = UrlFetchApp.fetch(`${API_URL}/slack/interactions`, options);
    
    // Enhanced response logging
    Logger.log(`📥 === BACKEND API RESPONSE (CANCEL ORDER) ===`);
    Logger.log(`📊 Response Code: ${response.getResponseCode()}`);
    Logger.log(`📋 Response Headers: ${JSON.stringify(response.getHeaders())}`);
    
    const responseText = response.getContentText();
    Logger.log(`📄 Raw Response Text (${responseText.length} chars): ${responseText}`);
    
    let responseData;
    try {
      responseData = JSON.parse(responseText);
      Logger.log(`📦 Parsed Response Data:`);
      Logger.log(JSON.stringify(responseData, null, 2));
    } catch (parseError) {
      Logger.log(`❌ Failed to parse response as JSON: ${parseError.message}`);
      Logger.log(`📄 Raw response: ${responseText}`);
      responseData = { error: "invalid_json", raw_response: responseText };
    }
    
    if (response.getResponseCode() !== 200) {
      // Enhanced error logging
      Logger.log(`❌ === BACKEND API ERROR HANDLING ===`);
      Logger.log(`❌ Status Code: ${response.getResponseCode()}`);
      
      const errorDetail = responseData.detail || responseData;
      const errorType = errorDetail.error || 'unknown_error';
      const errorMessage = errorDetail.message || 'Unknown error occurred';
      const statusCode = response.getResponseCode();
      
      Logger.log(`❌ Error Detail: ${JSON.stringify(errorDetail)}`);
      Logger.log(`❌ Error Type: ${errorType}`);
      Logger.log(`❌ Error Message: ${errorMessage}`);
      
      // Send error email with full context
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `❌ BARS Cancel Order - Backend API Error`,
        htmlBody: `
          <h3>❌ Backend API Error - Cancel Order</h3>
          <p><strong>Order:</strong> ${rawOrderNumber}</p>
          <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last} (${requestorEmail})</p>
          <p><strong>Slack User:</strong> ${slackUserName}</p>
          <p><strong>Status Code:</strong> ${statusCode}</p>
          <p><strong>Error Type:</strong> ${errorType}</p>
          <p><strong>Error Message:</strong> ${errorMessage}</p>
          <p><strong>Request Payload:</strong></p>
          <pre>${JSON.stringify(payload, null, 2)}</pre>
          <p><strong>Response Details:</strong></p>
          <pre>${JSON.stringify(errorDetail, null, 2)}</pre>
          <p><strong>Raw Response:</strong></p>
          <pre>${responseText}</pre>
        `
      });
      
      throw new Error(`Backend API error: ${errorMessage} (Status: ${statusCode})`);
    }
    
    // Success - backend handled everything
    Logger.log(`✅ === CANCEL ORDER SUCCESS ===`);
    Logger.log(`✅ Backend successfully handled order cancellation`);
    Logger.log(`📊 Response: ${JSON.stringify(responseData, null, 2)}`);
    
    // Optional: Send success notification email
    if (MODE === 'debug') {
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `✅ BARS Cancel Order - Success`,
        htmlBody: `
          <h3>✅ Order Cancellation Successful</h3>
          <p><strong>Order:</strong> ${rawOrderNumber}</p>
          <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last} (${requestorEmail})</p>
          <p><strong>Slack User:</strong> ${slackUserName}</p>
          <p><strong>Backend Response:</strong></p>
          <pre>${JSON.stringify(responseData, null, 2)}</pre>
          <p><strong>Request Payload:</strong></p>
          <pre>${JSON.stringify(payload, null, 2)}</pre>
        `
      });
    }
    
    return responseData;
    
  } catch (error) {
    Logger.log(`❌ Error in cancelOrderViaBackend: ${error.toString()}`);
    Logger.log(`❌ Stack trace: ${error.stack}`);
    
    // Send error email
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `❌ BARS Cancel Order - Unexpected Error`,
      htmlBody: `
        <h3>❌ Unexpected Error in Cancel Order</h3>
        <p><strong>Order:</strong> ${requestData.rawOrderNumber || 'Unknown'}</p>
        <p><strong>Slack User:</strong> ${slackUserName}</p>
        <p><strong>Error:</strong> ${error.message}</p>
        <p><strong>Stack Trace:</strong></p>
        <pre>${error.stack || 'No stack trace available'}</pre>
        <p><strong>Request Data:</strong></p>
        <pre>${JSON.stringify(requestData, null, 2)}</pre>
        <p><strong>Channel ID:</strong> ${channelId}</p>
        <p><strong>Thread TS:</strong> ${threadTs}</p>
      `
    });
    
    throw error; // Re-throw so doPost.gs can handle it
  }
}
