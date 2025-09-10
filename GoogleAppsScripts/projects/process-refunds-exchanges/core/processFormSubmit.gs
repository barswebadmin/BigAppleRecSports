/**
 * ========================================================================
 * UNIFIED FORM SUBMISSION HANDLER
 * ========================================================================
 * 
 * 🔧 CONFIGURATION: Change MODE in Utils.gs to switch between modes
 * 
 * ⚠️ IMPORTANT: All modes only send to Slack for manual processing.
 *    Actual refund processing happens through Slack button interactions.
 * ========================================================================
 */

function processFormSubmit(e) {
  try {
    const health = UrlFetchApp.fetch(`${API_URL}/health`);
    Logger.log(`health check: \n ${JSON.stringify(health,null,2)}`)
    
    // ========================================================================
    // EXTRACT FORM DATA (common for all modes)
    // ========================================================================
    
    const getFieldValueByKeyword = (keyword) => {
      const entry = Object.entries(e.namedValues).find(([key]) =>
        key.toLowerCase().includes(keyword.toLowerCase())
      );
      return entry?.[1]?.[0]?.trim() || "";
    };

    const requestorName = {
      first: getFieldValueByKeyword("first name"),
      last: getFieldValueByKeyword("last name")
    };

    const requestorEmail = getFieldValueByKeyword("email");
    const rawOrderNumber = getFieldValueByKeyword("order number");
    const refundAnswer = getFieldValueByKeyword("do you want a refund");
    const refundOrCredit = refundAnswer.toLowerCase().includes("refund") ? "refund" : "credit";
    const requestNotes = getFieldValueByKeyword("note");
    
    // Normalize order number (add # if missing) - using function from Utils.gs
    const formattedOrderNumber = normalizeOrderNumber(rawOrderNumber);
    
    Logger.log(`🔍 [MODE='${MODE}'] Form Data Extracted: \n
      - Requestor: ${requestorName.first} ${requestorName.last} \n
      - Email: ${requestorEmail} \n
      - Order: ${rawOrderNumber} → ${formattedOrderNumber} \n
      - Type: ${refundOrCredit} \n
      - Notes: ${requestNotes}
    `);


    processWithBackendAPI(
        formattedOrderNumber,
        rawOrderNumber,
        requestorName,
        requestorEmail,
        refundOrCredit,
        requestNotes,
        MODE === 'debugApi'
      );

  } catch (error) {
    const errorMessage = `Unexpected error in processFormSubmit [${MODE}]: ${error.toString()}`;
    Logger.log(`⚠️ ${errorMessage}`);
    
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `⚠️ BARS Refund Form - Unexpected Error [${MODE}]`,
      htmlBody: `
        <h3>⚠️ Unexpected Error in Form Processing</h3>
        <p><strong>Mode:</strong> ${MODE}</p>
        <p><strong>Error:</strong> ${errorMessage}</p>
        <p><strong>Stack:</strong> <pre>${error.stack || 'No stack trace available'}</pre></p>
        <p><strong>Form Data:</strong> <pre>${JSON.stringify(e.namedValues, null, 2)}</pre></p>
        <p><strong>⚠️ Action Required:</strong> Check logs and process manually</p>
      `
    });
  }
}




// ========================================================================
// BACKEND API PROCESSING
// ========================================================================

function processWithBackendAPI(formattedOrderNumber, rawOrderNumber, requestorName, requestorEmail, refundOrCredit, requestNotes, isDebug) {
  try {
    
    const sheetLink = getRowLink(formattedOrderNumber, SHEET_ID, SHEET_GID);
    if (isDebug && sheetLink) {
      Logger.log(`🔗 [debugApi] Generated sheet link: ${sheetLink}`);
    }
    
    const payload = {
      order_number: rawOrderNumber,
      requestor_name: requestorName,
      requestor_email: requestorEmail,
      refund_type: refundOrCredit,
      notes: requestNotes,
      sheet_link: sheetLink
    };
    
    // Enhanced request logging
    Logger.log(`🚀 === BACKEND API REQUEST ===`);
    Logger.log(`🌐 Target URL: ${API_URL}/refunds/send-to-slack`);
    Logger.log(`📦 Request Payload:`);
    Logger.log(JSON.stringify(payload, null, 2));
    
    const options = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true  // Prevent exceptions on non-200 status codes
    };
    
    Logger.log(`🔧 Request Options:`);
    Logger.log(`   Method: ${options.method}`);
    Logger.log(`   Headers: ${JSON.stringify(options.headers)}`);
    Logger.log(`   Payload Size: ${options.payload.length} characters`);
    
    Logger.log(`📡 Sending request to backend...`);
    const response = UrlFetchApp.fetch(`${API_URL}/refunds/send-to-slack`, options);
    
    // Enhanced response logging
    Logger.log(`📥 === BACKEND API RESPONSE ===`);
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
      
      // Handle API errors based on status codes
      const errorDetail = responseData.detail || responseData;
      const errorType = errorDetail.error || 'unknown_error';
      const errorMessage = errorDetail.message || 'Unknown error occurred';
      const statusCode = response.getResponseCode();
      
      Logger.log(`❌ Error Detail: ${JSON.stringify(errorDetail)}`);
      Logger.log(`❌ Error Type: ${errorType}`);
      Logger.log(`❌ Error Message: ${errorMessage}`);
      
      // Get BARS logo for email
      const barsLogoUrl = "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/122824_BARS_Logo_Full-Black.png?v=1741951481";
      const barsLogoBlob = UrlFetchApp
                          .fetch(barsLogoUrl)
                          .getBlob()
                          .setName("barsLogo");
      
      let emailSubject = '';
      let emailBody = '';
      let shouldSendToRequestor = false;
      
      if (statusCode === 406 || errorType === 'order_not_found') {
        // 406: Order Not Found - Send email to requestor using template from getSlackMessageText
        shouldSendToRequestor = true;
        emailSubject = `Big Apple Rec Sports - Error with Refund Request for Order ${rawOrderNumber}`;
        emailBody = `<p>Hi ${requestorName.first},</p>
          <p>Your request for a ${refundOrCredit} has <b>not</b> been processed successfully. Your provided order number could not be found in our system - remember to please enter only <i>one</i> order number (submit each request separately) and ensure there are only digits. Please confirm you submitted your request using the same email address as is associated with your order - <a href="${SHOPIFY_LOGIN_URL}">Sign In to see your order history</a> to find the correct order number if necessary - and try again.
          <br><br>
          If you believe this is in error, please reach out to <b>refunds@bigapplerecsports.com</b>.</p>
          
          --<br>
          <p>
            Warmly,<br>
            <b>BARS Leadership</b>
          </p>
          <img src="cid:barsLogo" style="width:225px; height:auto;">`;
        
        if (isDebug) {
          Logger.log(`❌ [debugApi] Order not found (406): ${errorMessage}`);
        }

        // Update spreadsheet with cancellation note (step 3)
        try {
          updateOrderNotesColumn(rawOrderNumber, requestorEmail, "Canceled - Order Not Found. Requestor has been emailed.");
          Logger.log(`✅ Updated Notes column for order ${rawOrderNumber}`);
        } catch (updateError) {
          Logger.log(`❌ Failed to update Notes column: ${updateError.message}`);
          MailApp.sendEmail({
            to: DEBUG_EMAIL,
            subject: "❌ BARS Refunds - Failed to update Notes column",
            htmlBody: `Failed to update Notes column for order ${rawOrderNumber}: ${updateError.message}`
          });
        }
        
      } else if (statusCode === 409 || errorType === 'email_mismatch') {
        // 409: Email Mismatch - Send email to requestor using template from getSlackMessageText
        shouldSendToRequestor = true;
        emailSubject = `Big Apple Rec Sports - Error with Refund Request for Order ${rawOrderNumber}`;
        emailBody = `<p>Hi ${requestorName.first},</p>
          <p>Your request for a ${refundOrCredit} has <b>not</b> been processed successfully. The email associated with the order number did not match the email you provided in the request. Please confirm you submitted your request using the same email address as is associated with your order - <a href="${SHOPIFY_LOGIN_URL}">Sign In to see your order history</a> to find the correct order number - and try again.
          <br><br>
          If you believe this is in error, please reach out to <b>refunds@bigapplerecsports.com</b>.</p>
          
          --<br>
          <p>
            Warmly,<br>
            <b>BARS Leadership</b>
          </p>
          <img src="cid:barsLogo" style="width:225px; height:auto;">`;
        
        if (isDebug) {
          Logger.log(`❌ [debugApi] Email mismatch (409): ${errorMessage}`);
          Logger.log(`❌ [debugApi] Order customer email: ${errorDetail.order_customer_email || 'Unknown'}`);
        }
        
      } else {
        // Other errors - Send debug email to admin
        emailSubject = `❌ BARS Refund Form - API Error [${isDebug ? 'debugApi' : 'prodApi'}]`;
        emailBody = `
          <h3>❌ Backend API Error</h3>
          <p><strong>Mode:</strong> ${isDebug ? 'debugApi' : 'prodApi'}</p>
          <p><strong>Status Code:</strong> ${statusCode}</p>
          <p><strong>Error Type:</strong> ${errorType}</p>
          <p><strong>Error Message:</strong> ${errorMessage}</p>
          <p><strong>Order:</strong> ${rawOrderNumber}</p>
          <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last} (${requestorEmail})</p>
          <p><strong>⚠️ Action Required:</strong> Check backend API logs and process manually</p>
        `;
        
        if (isDebug) {
          Logger.log(`❌ [debugApi] Backend API error (${statusCode}): ${errorMessage}`);
        }
      }
      
      // Send email to appropriate recipient
      if (shouldSendToRequestor) {
        MailApp.sendEmail({
          to: requestorEmail,
          replyTo: 'refunds@bigapplerecsports.com',
          subject: emailSubject,
          htmlBody: emailBody,
          inlineImages: { barsLogo: barsLogoBlob }
        });
        
        if (isDebug) {
          Logger.log(`📧 [debugApi] Sent error email to requestor: ${requestorEmail}`);
        }
      } else {
        MailApp.sendEmail({
          to: DEBUG_EMAIL,
          subject: emailSubject,
          htmlBody: emailBody
        });
        
        if (isDebug) {
          Logger.log(`📧 [debugApi] Sent error email to admin: ${isDebug ? DEBUG_EMAIL_2 : DEBUG_EMAIL_2}`);
        }
      }
      
      return;
    }
    
    // ✅ STEP 2: Success - API handled validation and sent to Slack
    Logger.log(`✅ === BACKEND API SUCCESS ===`);
    Logger.log(`✅ Successfully sent to Slack via backend API`);
    Logger.log(`✅ Response data keys: ${Object.keys(responseData).join(', ')}`);
    if (responseData.data) {
      Logger.log(`✅ Response data fields: ${Object.keys(responseData.data).join(', ')}`);
      Logger.log(`✅ Refund amount: $${responseData.data.refund_amount || 0}`);
      Logger.log(`✅ Refund calculation success: ${responseData.data.refund_calculation_success || 'Unknown'}`);
    }
    
    if (isDebug) {
      Logger.log(`✅ [debugApi] Successfully sent to Slack via backend API`);
      
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `✅ BARS Refund Form - API Processing Complete [debugApi]`,
        htmlBody: `
          <h3>✅ Debug Processing Complete - Backend API Mode</h3>
          <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last}</p>
          <p><strong>Email:</strong> ${requestorEmail}</p>
          <p><strong>Order:</strong> ${rawOrderNumber}</p>
          <p><strong>Refund Type:</strong> ${refundOrCredit}</p>
          <p><strong>Notes:</strong> ${requestNotes}</p>
          <p><strong>✅ Status:</strong> Successfully validated and sent to Slack via backend API</p>
          <p><strong>💰 Refund Amount:</strong> $${responseData.data.refund_amount || 0}</p>
          <p><strong>📝 Note:</strong> No automatic refund processing - awaiting Slack button interaction</p>
          <p><strong>🤖 Approach:</strong> Full backend API processing</p>
        `
      });
    }
    
  } catch (error) {
    const errorMessage = `Error in backend API processing: ${error.toString()}`;
    Logger.log(`❌ ${errorMessage}`);
    
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `❌ BARS Refund Form - API Processing Error [${isDebug ? 'debugApi' : 'prodApi'}]`,
      htmlBody: `
        <h3>❌ Backend API Processing Error</h3>
        <p><strong>Mode:</strong> ${isDebug ? 'debugApi' : 'prodApi'}</p>
        <p><strong>Error:</strong> ${errorMessage}</p>
        <p><strong>Order:</strong> ${rawOrderNumber}</p>
        <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last} (${requestorEmail})</p>
        <p><strong>⚠️ Action Required:</strong> Check backend API connection and process manually</p>
      `
    });
  }
} 