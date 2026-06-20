/**
 * ========================================================================
 * UNIFIED FORM SUBMISSION HANDLER
 * ========================================================================
 *
 * Posts the refund request to the ShopifyRefundHandler lambda, which fetches
 * the order, validates, estimates, and posts the review to Slack. Actual
 * refund processing happens through the Slack review's button interactions.
 * ========================================================================
 */


// biome-ignore lint/correctness/noUnusedVariables: <this is triggered when the form is submitted>
function  processFormSubmit(e) {
  try {
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
    // Map the raw form answer to the canonical refund_to at this set-point so
    // no legacy "refund"/"credit" value reaches any outbound payload.
    const refundType = refundAnswer.toLowerCase().includes("refund") ? "original_method" : "store_credit";
    const requestNotes = getFieldValueByKeyword("note");

    const requestSubmittedAt = tryParseIso(getFieldValueByKeyword("timestamp"));

    // Normalize order number (add # if missing) - using function from Utils.gs
    const formattedOrderNumber = normalizeOrderNumber(rawOrderNumber);

    Logger.log(`🔍 Form Data Extracted: \n
      - Requestor: ${requestorName.first} ${requestorName.last} \n
      - Email: ${requestorEmail} \n
      - Order: ${rawOrderNumber} → ${formattedOrderNumber} \n
      - Type: ${refundType} \n
      - Notes: ${requestNotes} \n
      - Submitted At: ${requestSubmittedAt}
    `);

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

  } catch (error) {
    const errorMessage = `Unexpected error in processFormSubmit: ${error.toString()}`;
    Logger.log(`⚠️ ${errorMessage}`);

    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `⚠️ BARS Refund Form - Unexpected Error`,
      htmlBody: `
        <h3>⚠️ Unexpected Error in Form Processing</h3>
        <p><strong>Error:</strong> ${errorMessage}</p>
        <p><strong>Stack:</strong> <pre>${error.stack || 'No stack trace available'}</pre></p>
        <p><strong>Form Data:</strong> <pre>${JSON.stringify(e.namedValues, null, 2)}</pre></p>
        <p><strong>⚠️ Action Required:</strong> Check logs and process manually</p>
      `
    });
  }
}
