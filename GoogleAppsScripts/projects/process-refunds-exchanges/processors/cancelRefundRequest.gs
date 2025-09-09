function cancelRefundRequest(requestData, channelId, threadTs, slackUserName) {
  try {
    const { rawOrderNumber } = requestData;
    const formattedRawOrderNumber = rawOrderNumber.replace('+',' ')
    const rowData = getRequestDetailsFromOrderNumber(formattedRawOrderNumber);
    // if (!rowData) throw new Error(`Row data not found for order: ${rawOrderNumber}`);
    const sheetLink = getRowLink(formattedRawOrderNumber, SHEET_ID, SHEET_GID);

    const { requestorFirstName, requestorLastName, requestorEmail } = rowData

    const formattedOrderNumber = normalizeOrderNumber(rawOrderNumber);

    const updatedBlocks = [
      { type: "divider" },
      {
        type: "section",
        text: {
          type: "mrkdwn",
          text: `❌ *Request to refund Order ${formattedRawOrderNumber} for ${requestorFirstName} ${requestorLastName} (${requestorEmail}) has been canceled by ${slackUserName}* \n🔗 *<${sheetLink}|View Request in Google Sheets>*`
        }
      },
      { type: "divider" }
    ];

    const updatedPayload = {
      channel: channelId,
      ts: threadTs,
      blocks: updatedBlocks,
      text: `❌ Request for Order ${formattedOrderNumber} canceled by ${slackUserName}`
    };

    const result = updateSlackMessage(getSlackRefundsChannel(), updatedPayload);

    if (!result?.ok) {
      throw new Error(result?.error || "Unknown error during Slack update");
    }

    try {
      markOrderAsProcessed(rawOrderNumber);
    } catch (e) {
      const message = [
        `<b>Error marking order as processed</b>`,
        `<pre>${e.message || e.toString()}</pre>`,
        `<b>Stack trace:</b><pre>${e.stack || 'No stack trace available'}</pre>`,
        `<b>Order:</b> ${rawOrderNumber}`
      ].join('<br><br>');

      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: "❌ Refunds - Error marking order as processed",
        htmlBody: message
      });
    }

  } catch (error) {
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: "❌ Failed to cancel Slack refund request",
      htmlBody: `
        <p><strong>Error:</strong> ${error.message}</p>
        <p><strong>Request Data:</strong></p>
        <pre>${JSON.stringify(requestData, null, 2)}</pre>
      `
    });
  }
}