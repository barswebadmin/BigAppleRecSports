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


// biome-ignore lint/correctness/noUnusedVariables: <this is triggered when the form is submitted>
function  processFormSubmit(e) {
  try {
    const health = UrlFetchApp.fetch(`${getApiUrl()}/health`);
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

    // Capture the timestamp when the form was submitted
    const timestampValue = getFieldValueByKeyword("timestamp");
    let requestSubmittedAt = null;
    if (timestampValue) {
      try {
        // Convert to ISO 8601 format for the backend
        const timestamp = new Date(timestampValue);
        requestSubmittedAt = timestamp.toISOString();
        Logger.log(`📅 Form submission timestamp: ${requestSubmittedAt}`);
      } catch (error) {
        Logger.log(`⚠️ Failed to parse timestamp '${timestampValue}': ${error.message}`);
      }
    } else {
      Logger.log(`⚠️ No timestamp found in form submission`);
    }

    // Normalize order number (add # if missing) - using function from Utils.gs
    const formattedOrderNumber = normalizeOrderNumber(rawOrderNumber);

    Logger.log(`🔍 [MODE='${MODE}'] Form Data Extracted: \n
      - Requestor: ${requestorName.first} ${requestorName.last} \n
      - Email: ${requestorEmail} \n
      - Order: ${rawOrderNumber} → ${formattedOrderNumber} \n
      - Type: ${refundOrCredit} \n
      - Notes: ${requestNotes} \n
      - Submitted At: ${requestSubmittedAt}
    `);


    processWithBackendAPI(
        formattedOrderNumber,
        rawOrderNumber,
        requestorName,
        requestorEmail,
        refundOrCredit,
        requestNotes,
        requestSubmittedAt,
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

function processWithBackendAPI(formattedOrderNumber, rawOrderNumber, requestorName, requestorEmail, refundOrCredit, requestNotes, requestSubmittedAt) {
  try {

    const sheetLink = getRowLink(formattedOrderNumber, SHEET_ID, SHEET_GID);

    const payload = {
      order_number: rawOrderNumber,
      requestor_name: requestorName,
      requestor_email: requestorEmail,
      refund_type: refundOrCredit,
      notes: requestNotes,
      sheet_link: sheetLink,
      request_submitted_at: requestSubmittedAt
    };

    // Configure Slack routing parameters
    const slackChannelName = 'joetest';
    const mentionStrategy = 'user|joe';

    // Build URL with proper encoding for query parameters
    const queryParams = `?slackChannelName=${encodeURIComponent(slackChannelName)}&mentionStrategy=${encodeURIComponent(mentionStrategy)}`;
    const targetUrl = `${getApiUrl()}/refunds/send-to-slack${queryParams}`;

    // Enhanced request logging
    Logger.log(`🚀 === BACKEND API REQUEST ===`);
    Logger.log(`🌐 Target URL: ${targetUrl}`);
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
    const response = UrlFetchApp.fetch(targetUrl, options);

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

      Logger.log(`❌ === BACKEND API ERROR HANDLING ===`);
      Logger.log(`❌ Status Code: ${statusCode}`);
      Logger.log(`❌ Error Detail: ${JSON.stringify(errorDetail)}`);
      Logger.log(`❌ Error Type: ${errorType}`);
      Logger.log(`❌ Error Message: ${errorMessage}`);

      // Log specific error fields for debugging
      if (errorDetail.errors) {
        Logger.log(`❌ Shopify Errors Field: ${errorDetail.errors}`);
      }
      if (errorDetail.user_message) {
        Logger.log(`❌ User Message Field: ${errorDetail.user_message}`);
      }
      if (errorDetail.error) {
        Logger.log(`❌ Error Field: ${errorDetail.error}`);
      }

      // Get BARS logo for email
      const barsLogoUrl = "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/122824_BARS_Logo_Full-Black.png?v=1741951481";
      const barsLogoBlob = UrlFetchApp
                          .fetch(barsLogoUrl)
                          .getBlob()
                          .setName("barsLogo");

      let emailSubject = '';
      let emailBody = '';
      let shouldSendToRequestor = false;

      if (statusCode === 401) {
        // 401: Shopify Authentication Error - Don't email customer, admin notification only
        shouldSendToRequestor = false;
        const shopifyErrors = errorDetail.errors || errorMessage;
        const userMessage = errorDetail.user_message || 'There is a system configuration issue. Please contact support or try again later.';

        Logger.log(`🚨 [${isDebug ? 'debugApi' : 'prodApi'}] Shopify authentication error (401): ${shopifyErrors}`);

        // Update spreadsheet with config error note
        try {
          updateOrderNotesColumn(rawOrderNumber, requestorEmail, `⚙️ Auth Error (401): ${shopifyErrors}. No email sent to customer.`);
          Logger.log(`✅ Updated Notes column for order ${rawOrderNumber} with auth error`);
        } catch (updateError) {
          Logger.log(`❌ Failed to update Notes column: ${updateError.message}`);
        }

        // Send admin notification only
        emailSubject = `🚨 BARS Refund Form - Shopify Auth Error (401) [${isDebug ? 'debugApi' : 'prodApi'}]`;
        emailBody = `
          <h3>🚨 Shopify Authentication Error (401)</h3>
          <p><strong>Mode:</strong> ${isDebug ? 'debugApi' : 'prodApi'}</p>
          <p><strong>Status Code:</strong> ${statusCode}</p>
          <p><strong>Shopify Errors:</strong> ${shopifyErrors}</p>
          <p><strong>Order:</strong> ${rawOrderNumber}</p>
          <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last} (${requestorEmail})</p>
          <p><strong>⚠️ Action Required:</strong> Check Shopify API token/credentials</p>
          <p><strong>📧 Customer Status:</strong> No email sent to customer (configuration error)</p>
          <p><strong>💬 User Message Shown:</strong> ${userMessage}</p>
        `;

        Logger.log(`💬 === USER MESSAGE FOR FORM ===`);
        Logger.log(`💬 ${userMessage}`);
        Logger.log(`💬 === END USER MESSAGE ===`);

      } else if (statusCode === 404) {
        // 404: Shopify Store Not Found - Don't email customer, admin notification only
        shouldSendToRequestor = false;
        const shopifyErrors = errorDetail.errors || errorMessage;
        const userMessage = errorDetail.user_message || 'There is a system configuration issue. Please contact support or try again later.';

        Logger.log(`🚨 [${isDebug ? 'debugApi' : 'prodApi'}] Shopify store error (404): ${shopifyErrors}`);

        // Update spreadsheet with config error note
        try {
          updateOrderNotesColumn(rawOrderNumber, requestorEmail, `⚙️ Store Error (404): ${shopifyErrors}. No email sent to customer.`);
          Logger.log(`✅ Updated Notes column for order ${rawOrderNumber} with store error`);
        } catch (updateError) {
          Logger.log(`❌ Failed to update Notes column: ${updateError.message}`);
        }

        // Send admin notification only
        emailSubject = `🚨 BARS Refund Form - Shopify Store Error (404) [${isDebug ? 'debugApi' : 'prodApi'}]`;
        emailBody = `
          <h3>🚨 Shopify Store Not Found (404)</h3>
          <p><strong>Mode:</strong> ${isDebug ? 'debugApi' : 'prodApi'}</p>
          <p><strong>Status Code:</strong> ${statusCode}</p>
          <p><strong>Shopify Errors:</strong> ${shopifyErrors}</p>
          <p><strong>Order:</strong> ${rawOrderNumber}</p>
          <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last} (${requestorEmail})</p>
          <p><strong>⚠️ Action Required:</strong> Check Shopify store URL configuration</p>
          <p><strong>📧 Customer Status:</strong> No email sent to customer (configuration error)</p>
          <p><strong>💬 User Message Shown:</strong> ${userMessage}</p>
        `;

        Logger.log(`💬 === USER MESSAGE FOR FORM ===`);
        Logger.log(`💬 ${userMessage}`);
        Logger.log(`💬 === END USER MESSAGE ===`);

      } else if (statusCode === 406 || errorType === 'order_not_found') {
        // 406: Order Not Found - COMMENTED OUT: Don't send email to requestor per new requirements
        shouldSendToRequestor = false; // Changed from true to false

        Logger.log(`🔍 [${isDebug ? 'debugApi' : 'prodApi'}] Order not found (406): ${errorMessage}`);
        Logger.log(`📧 CUSTOMER EMAIL DISABLED: Not sending email to customer for order not found`);

        /* COMMENTED OUT: Customer email for order not found
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
        */

        // Update spreadsheet with cancellation note (step 3)
        try {
          updateOrderNotesColumn(rawOrderNumber, requestorEmail, "Order Not Found - Slack notification sent, no customer email per new policy.");
          Logger.log(`✅ Updated Notes column for order ${rawOrderNumber}`);
        } catch (updateError) {
          Logger.log(`❌ Failed to update Notes column: ${updateError.message}`);
          MailApp.sendEmail({
            to: DEBUG_EMAIL,
            subject: "❌ BARS Refunds - Failed to update Notes column",
            htmlBody: `Failed to update Notes column for order ${rawOrderNumber}: ${updateError.message}`
          });
        }

        // Send admin notification about order not found
        emailSubject = `🔍 BARS Refund Form - Order Not Found (406) [${isDebug ? 'debugApi' : 'prodApi'}]`;
        emailBody = `
          <h3>🔍 Order Not Found (406)</h3>
          <p><strong>Mode:</strong> ${isDebug ? 'debugApi' : 'prodApi'}</p>
          <p><strong>Status Code:</strong> ${statusCode}</p>
          <p><strong>Order:</strong> ${rawOrderNumber}</p>
          <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last} (${requestorEmail})</p>
          <p><strong>📧 Customer Status:</strong> No email sent to customer (new policy - Slack handles notification)</p>
          <p><strong>💬 Note:</strong> Backend sent Slack notification which will email customer to check order number</p>
        `;

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

      } else if (statusCode === 503 || errorType === 'shopify_connection_error') {
        // 503: Service Unavailable - Shopify connection error, don't email customer, just log and show user message
        shouldSendToRequestor = false;
        const userMessage = errorDetail.user_message || 'There was a technical issue connecting to our system. Please try submitting your refund request again in a few minutes.';

        Logger.log(`📋 User message: ${userMessage}`);

        // Update spreadsheet with technical error note
        try {
          updateOrderNotesColumn(rawOrderNumber, requestorEmail, "Technical Error - Shopify connection failed. No email sent to customer.");
          Logger.log(`✅ Updated Notes column for order ${rawOrderNumber} with technical error`);
        } catch (updateError) {
          Logger.log(`❌ Failed to update Notes column: ${updateError.message}`);
        }

        // Send admin notification only
        const errorTypeDisplay = errorType === 'shopify_config_error' ? 'Configuration Error' : 'Connection Error';
        emailSubject = `🚨 BARS Refund Form - Shopify ${errorTypeDisplay}`;
        emailBody = `
          <h3>🚨 Shopify ${errorTypeDisplay}</h3>
          <p><strong>Status Code:</strong> ${statusCode}</p>
          <p><strong>Error Type:</strong> ${errorType}</p>
          <p><strong>Error Message:</strong> ${errorMessage}</p>
          <p><strong>Order:</strong> ${rawOrderNumber}</p>
          <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last} (${requestorEmail})</p>
          <p><strong>⚠️ Action Required:</strong> ${errorType === 'shopify_config_error' ? 'Check Shopify API credentials and store configuration' : 'Check Shopify API connectivity and backend logs'}</p>
          <p><strong>📧 Customer Status:</strong> No email sent to customer (technical error)</p>
          <p><strong>💬 User Message Shown:</strong> ${userMessage}</p>
        `;

        // Log the user-friendly message that would be shown
        Logger.log(`💬 === USER MESSAGE FOR FORM ===`);
        Logger.log(`💬 ${userMessage}`);
        Logger.log(`💬 === END USER MESSAGE ===`);

      } else if (statusCode === 401 || statusCode === 404 || errorType === 'shopify_config_error') {
        // 401/404: Shopify configuration errors - don't email customer, just log and show user message
        shouldSendToRequestor = false;
        const shopifyErrors = errorDetail.errors || errorMessage;
        const userMessage = errorDetail.user_message || 'There is a system configuration issue. Please contact support or try again later.';

        Logger.log(`🚨 Shopify config error (${statusCode}): ${shopifyErrors}`);

        // Update spreadsheet with technical error note
        try {
          const notesMessage = `⚙️ Config Error (${statusCode}): ${shopifyErrors}`;
          updateNotesColumn(rawOrderNumber, notesMessage);
          Logger.log(`✅ Updated Notes column for order ${rawOrderNumber} with config error`);
        } catch (updateError) {
          Logger.log(`❌ Failed to update Notes column: ${updateError.message}`);
        }

        // Send admin notification only
        emailSubject = `⚙️ BARS Refund Form - Shopify Config Error (${statusCode})`;
        emailBody = `
          <h3>⚙️ Shopify Configuration Error (${statusCode})</h3>
          <p><strong>Status Code:</strong> ${statusCode}</p>
          <p><strong>Error Type:</strong> ${errorType}</p>
          <p><strong>Shopify Errors:</strong> ${shopifyErrors}</p>
          <p><strong>Order:</strong> ${rawOrderNumber}</p>
          <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last} (${requestorEmail})</p>
          <p><strong>⚠️ Action Required:</strong> ${statusCode === 401 ? 'Check Shopify API token/credentials' : 'Check Shopify store URL configuration'}</p>
          <p><strong>📧 Customer Status:</strong> No email sent to customer (configuration error)</p>
          <p><strong>💬 User Message Shown:</strong> ${userMessage}</p>
        `;

        // Log the user-friendly message that would be shown
        Logger.log(`💬 === USER MESSAGE FOR FORM ===`);
        Logger.log(`💬 ${userMessage}`);
        Logger.log(`💬 === END USER MESSAGE ===`);

      } else {
        // Other errors - Send debug email to admin
        emailSubject = `❌ BARS Refund Form - API Error`;
        emailBody = `
          <h3>❌ Backend API Error</h3>
          <p><strong>Status Code:</strong> ${statusCode}</p>
          <p><strong>Error Type:</strong> ${errorType}</p>
          <p><strong>Error Message:</strong> ${errorMessage}</p>
          <p><strong>Order:</strong> ${rawOrderNumber}</p>
          <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last} (${requestorEmail})</p>
          <p><strong>⚠️ Action Required:</strong> Check backend API logs and process manually</p>
        `;
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


      } else {
        MailApp.sendEmail({
          to: DEBUG_EMAIL,
          subject: emailSubject,
          htmlBody: emailBody
        });


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
    }

  } catch (error) {
    const errorMessage = `Error in backend API processing: ${error.toString()}`;
    Logger.log(`❌ ${errorMessage}`);

    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `❌ BARS Refund Form - API Processing Error`,
      htmlBody: `
        <h3>❌ Backend API Processing Error</h3>
        <p><strong>Error:</strong> ${errorMessage}</p>
        <p><strong>Order:</strong> ${rawOrderNumber}</p>
        <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last} (${requestorEmail})</p>
        <p><strong>⚠️ Action Required:</strong> Check backend API connection and process manually</p>
      `
    });
  }
}
