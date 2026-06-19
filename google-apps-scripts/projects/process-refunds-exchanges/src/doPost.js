/**
 * ========================================================================
 * SIMPLIFIED doPost HANDLER - BACKEND-DRIVEN WORKFLOW
 * ========================================================================
 *
 * 🔄 NEW WORKFLOW:
 * 1. GAS handles ONLY form submissions → sends JSON to backend
 * 2. Backend creates Slack messages with buttons
 * 3. Slack webhooks go DIRECTLY to backend (not GAS)
 * 4. Backend handles all button interactions and updates Slack
 *
 * ⚠️ IMPORTANT: Slack app webhook URL should point to backend:
 *    ${API_URL}/slack/interactions
 * ========================================================================
 */

/**
 * Handle GET requests for debugging
 */
function doGet(e) {
  Logger.log("⚠️ doGet called - this should be doPost for denial emails");
  Logger.log("📨 GET Request object: " + JSON.stringify(e, null, 2));

  return MailApp.sendEmail({
    to: DEBUG_EMAIL,
    subject: "⚠️ Slack Webhook Received by GAS but was GET request",
    htmlBody: `
      ${JSON.stringify(e.postData, null, 2)}
    `
  });
}

function doPost(e) {
  const functionName = 'doPost';
  const startTime = new Date().getTime();
  const timestamp = new Date().toISOString();
  
  Logger.log(`🚀 [${timestamp}] === ENTERING ${functionName} ===`);
  Logger.log(`   Request received at: ${timestamp}`);
  
  let requestContext = {
    hasPostData: !!e.postData,
    hasContents: !!(e.postData && e.postData.contents),
    contentType: e.postData?.type || 'unknown',
    rawLength: 0,
    requestType: null
  };
  
  try {
    Logger.log(`📨 [${timestamp}] Request object received`);
    Logger.log(`   Has postData: ${requestContext.hasPostData}`);
    Logger.log(`   Has contents: ${requestContext.hasContents}`);
    Logger.log(`   Content type: ${requestContext.contentType}`);

    if (!e.postData || !e.postData.contents) {
      const errorMsg = "Missing postData or contents in request";
      Logger.log(`❌ [${timestamp}] === VALIDATION ERROR in ${functionName} ===`);
      Logger.log(`   Operation: Validating request structure`);
      Logger.log(`   Error: ${errorMsg}`);
      Logger.log(`   Has postData: ${requestContext.hasPostData}`);
      Logger.log(`   Has contents: ${requestContext.hasContents}`);
      Logger.log(`   Full request: ${JSON.stringify(e, null, 2)}`);
      
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `🚨 ${functionName}: Missing Request Data`,
        htmlBody: `
          <h2>🚨 Missing Request Data in ${functionName}</h2>
          <p><strong>Timestamp:</strong> ${timestamp}</p>
          <p><strong>Error:</strong> ${errorMsg}</p>
          <p><strong>Has postData:</strong> ${requestContext.hasPostData}</p>
          <p><strong>Has contents:</strong> ${requestContext.hasContents}</p>
          <h3>Full Request:</h3>
          <pre>${JSON.stringify(e, null, 2)}</pre>
        `
      });
      
      throw new Error(errorMsg);
    }

    const raw = decodeURIComponent(e.postData.contents);
    requestContext.rawLength = raw.length;
    Logger.log(`📝 [${timestamp}] Raw contents decoded`);
    Logger.log(`   Length: ${raw.length} characters`);
    Logger.log(`   Preview: ${raw.substring(0, 200)}${raw.length > 200 ? '...' : ''}`);

    // Check if this is a Slack webhook (contains "payload=")
    if (raw.startsWith("payload=")) {
      requestContext.requestType = 'slack_webhook';
      Logger.log(`🔄 [${timestamp}] Slack webhook detected - redirecting to backend`);
      Logger.log(`   This should go to backend, not GAS`);

      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: "⚠️ Slack Webhook Received by GAS",
        htmlBody: `
          <h3>⚠️ Slack webhook was sent to Google Apps Script</h3>
          <p><strong>Timestamp:</strong> ${timestamp}</p>
          <p><strong>Expected:</strong> Slack should send directly to backend</p>
          <p><strong>Current Slack URL:</strong> This Google Apps Script</p>
          <p><strong>Correct Slack URL:</strong> ${API_URL}/slack/interactions</p>
          <p><strong>Action Required:</strong> Update Slack app webhook URL to point to backend</p>
          <p><strong>Payload Preview:</strong></p>
          <pre>${raw.substring(0, 500)}...</pre>
        `
      });

      return ContentService.createTextOutput(JSON.stringify({
        "text": "⚠️ Please update Slack webhook URL to point to backend"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // Check if this is a backend request (JSON with action)
    try {
      Logger.log(`🔍 [${timestamp}] Attempting to parse as JSON...`);
      const jsonData = JSON.parse(raw);
      Logger.log(`✅ [${timestamp}] Successfully parsed as JSON`);
      Logger.log(`   Keys: ${Object.keys(jsonData).join(', ')}`);
      
      if (jsonData.action) {
        requestContext.requestType = 'backend_action';
        Logger.log(`🔧 [${timestamp}] Backend action detected: ${jsonData.action}`);

        const errorMsg = `Unknown action: ${jsonData.action}`;
          Logger.log(`❌ [${timestamp}] ${errorMsg}`);
          return ContentService.createTextOutput(JSON.stringify({
            success: false,
            message: errorMsg,
          })).setMimeType(ContentService.MimeType.JSON);
      } else {
        Logger.log(`📝 [${timestamp}] JSON parsed but no action field - assuming form submission`);
      }
    } catch (parseError) {
      // Not JSON, continue to form submission processing
      Logger.log(`📝 [${timestamp}] Not valid JSON, assuming form submission`);
      Logger.log(`   Parse error: ${parseError.message}`);
    }

    // If we get here, this should be a Google Form submission
    requestContext.requestType = 'form_submission';
    Logger.log(`📝 [${timestamp}] Form submission detected - posting to lambda`);

    // Process form submission by calling the existing form handler
    try {
      return processFormSubmitViaDoPost(e);
    } catch (formError) {
      const errorContext = {
        function: functionName,
        operation: 'processing_form_submission',
        requestType: requestContext.requestType,
        error: formError.message,
        errorName: formError.name,
        stack: formError.stack
      };
      
      Logger.log(`❌ [${timestamp}] === ERROR processing form submission ===`);
      Logger.log(`   Operation: Processing form submission`);
      Logger.log(`   Error: ${formError.message}`);
      Logger.log(`   Stack: ${formError.stack || 'No stack trace'}`);
      
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `🚨 ${functionName}: Form Submission Error`,
        htmlBody: `
          <h2>🚨 Form Submission Error in ${functionName}</h2>
          <p><strong>Timestamp:</strong> ${timestamp}</p>
          <p><strong>Operation:</strong> Processing form submission</p>
          <p><strong>Error:</strong> ${formError.message}</p>
          <h3>Stack Trace:</h3>
          <pre>${formError.stack || 'No stack trace'}</pre>
        `
      });
      
      throw formError;
    }

  } catch (error) {
    const duration = new Date().getTime() - startTime;
    const errorContext = {
      function: functionName,
      operation: 'unexpected_error',
      durationMs: duration,
      requestContext: requestContext,
      error: error.message,
      errorName: error.name,
      stack: error.stack
    };
    
    const errorMessage = `Error in ${functionName}: ${error.toString()}`;
    Logger.log(`💥 [${timestamp}] === UNEXPECTED ERROR in ${functionName} ===`);
    Logger.log(`   Duration: ${duration}ms`);
    Logger.log(`   Error: ${error.message}`);
    Logger.log(`   Error type: ${error.name}`);
    Logger.log(`   Stack trace: ${error.stack || 'No stack trace available'}`);
    Logger.log(`   Request context: ${JSON.stringify(requestContext, null, 2)}`);

    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `🚨 ${functionName}: Unexpected Error`,
      htmlBody: `
        <h2>🚨 Unexpected Error in ${functionName}</h2>
        <p><strong>Timestamp:</strong> ${timestamp}</p>
        <p><strong>Duration:</strong> ${duration}ms</p>
        <p><strong>Error:</strong> ${errorMessage}</p>
        <p><strong>Error Type:</strong> ${error.name}</p>
        <h3>Stack Trace:</h3>
        <pre>${error.stack || 'No stack trace available'}</pre>
        <h3>Request Context:</h3>
        <pre>${JSON.stringify(requestContext, null, 2)}</pre>
        <h3>Raw Request Data:</h3>
        <pre>${requestContext.rawLength > 0 ? raw?.substring(0, 1000) || 'No data' : 'No raw data available'}</pre>
      `
    });

    return ContentService.createTextOutput(JSON.stringify({
      status: 'error',
      message: errorMessage,
      context: errorContext
    })).setMimeType(ContentService.MimeType.JSON);
  } finally {
    const duration = new Date().getTime() - startTime;
    const endTimestamp = new Date().toISOString();
    Logger.log(`🏁 [${endTimestamp}] === EXITING ${functionName} ===`);
    Logger.log(`   Duration: ${duration}ms`);
    Logger.log(`   Request type: ${requestContext.requestType || 'unknown'}`);
  }
}

/**
 * Process Google Form submission (called by doPost)
 * Extracts form data and posts to the refund lambda
 */
function processFormSubmitViaDoPost(e) {
  try {
    // Extract form fields from Google Form submission
    const getFieldValueByKeyword = (keyword) => {
      const entry = Object.entries(e.namedValues || {}).find(([key]) =>
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
    // Map the raw form answer to the canonical refund_to at this set-point.
    const refundType = refundAnswer.toLowerCase().includes("refund") ? "original_method" : "store_credit";
    const requestNotes = getFieldValueByKeyword("note");

    const requestSubmittedAt = tryParseIso(getFieldValueByKeyword("timestamp"));
    const formattedOrderNumber = normalizeOrderNumber(rawOrderNumber);

    Logger.log(`📋 Form submission data extracted for order: ${rawOrderNumber}`);

    sendLambdaWebhook(
      buildLambdaRefundPayload(
        formattedOrderNumber,
        rawOrderNumber,
        requestorName,
        requestorEmail,
        refundType,
        requestNotes,
        requestSubmittedAt,
      )
    );

    return ContentService.createTextOutput("Form submitted successfully").setMimeType(ContentService.MimeType.TEXT);

  } catch (error) {
    Logger.log(`❌ Error processing form submission: ${error.toString()}`);
    throw error; // Re-throw to be handled by main doPost
  }
}

/**
 * ========================================================================
 * REMOVED: Legacy Slack button handling code
 * ========================================================================
 *
 * The following functions are no longer needed in doPost since all
 * Slack interactions now go directly to the backend:
 *
 * - All actionId handlers (approve_refund, deny_refund, cancel_order, etc.)
 * - View submission handlers (modals)
 * - Button value parsing logic
 * - Slack webhook processing
 *
 * 🎯 New flow: Slack → Backend → Slack (GAS not involved in Slack interactions)
 * ========================================================================
 */
