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
  try {
    Logger.log("🚀 doPost called");
    Logger.log("📨 Request object: " + JSON.stringify(e, null, 2));

    if (!e.postData || !e.postData.contents) {
      Logger.log("❌ Missing postData or contents");
      throw new Error("Missing postData or contents in request");
    }

    const raw = decodeURIComponent(e.postData.contents);
    Logger.log("📝 Raw contents: " + raw);

    // Check if this is a Slack webhook (contains "payload=")
    if (raw.startsWith("payload=")) {
      // This is a Slack webhook - should go to backend instead
      Logger.log("🔄 Slack webhook detected - redirecting to backend");

      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: "⚠️ Slack Webhook Received by GAS",
        htmlBody: `
          <h3>⚠️ Slack webhook was sent to Google Apps Script</h3>
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
      const jsonData = JSON.parse(raw);
      if (jsonData.action) {
        Logger.log(`🔧 Backend action detected: ${jsonData.action}`);

        if (jsonData.action === "send_denial_email") {
          const result = sendDenialEmail(jsonData);
          return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
        } else {
          Logger.log(`❌ Unknown action: ${jsonData.action}`);
          return ContentService.createTextOutput(JSON.stringify({
            success: false,
            message: `Unknown action: ${jsonData.action}`
          })).setMimeType(ContentService.MimeType.JSON);
        }
      }
    } catch (parseError) {
      // Not JSON, continue to form submission processing
      Logger.log("📝 Not JSON, assuming form submission");
    }

    // If we get here, this should be a Google Form submission
    Logger.log("📝 Form submission detected - processing with backend API");

    // Process form submission by calling the existing form handler
    return processFormSubmitViaDoPost(e);

  } catch (error) {
    const errorMessage = `Error in doPost: ${error.toString()}`;
    Logger.log(`❌ ${errorMessage}`);

    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `❌ BARS doPost Error`,
      htmlBody: `
        <h3>❌ Error in doPost Function</h3>
        <p><strong>Error:</strong> ${errorMessage}</p>
        <p><strong>Stack:</strong> <pre>${error.stack || 'No stack trace available'}</pre></p>
        <p><strong>Raw Request Data:</strong> <pre>${raw?.substring(0, 1000) || 'No data'}</pre></p>
      `
    });

    return ContentService.createTextOutput("Error processing request").setMimeType(ContentService.MimeType.TEXT);
  }
}

/**
 * Process Google Form submission (called by doPost)
 * Extracts form data and sends to backend API
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
    const refundOrCredit = refundAnswer.toLowerCase().includes("refund") ? "refund" : "credit";
    const requestNotes = getFieldValueByKeyword("note");

    Logger.log(`📋 Form submission data extracted for order: ${rawOrderNumber}`);

    // Call the existing backend processing function
    processWithBackendAPI(
      normalizeOrderNumber(rawOrderNumber),
      rawOrderNumber,
      requestorName,
      requestorEmail,
      refundOrCredit,
      requestNotes,
      MODE === 'debugApi'
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
