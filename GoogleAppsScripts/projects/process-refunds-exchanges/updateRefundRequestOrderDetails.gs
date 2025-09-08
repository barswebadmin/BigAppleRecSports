const updateRefundRequestAmount = ({ requestData, channelId, threadTs, slackUserName, triggerId }) => {
  try {
    const { orderId, refundAmount, rawOrderNumber } = requestData
    const rowData = getRequestDetailsFromOrderNumber(rawOrderNumber);
    const { requestorEmail, requestorFirstName, requestorLastName } = rowData;
    const formattedOrderNumber = normalizeOrderNumber(rawOrderNumber);

    const modalViewPayload = {
      trigger_id: triggerId,
      view: {
        type: "modal",
        callback_id: "update_refund_amount_modal",
        title: {
          type: "plain_text",
          text: "Update Refund Amount"
        },
        submit: {
          type: "plain_text",
          text: "Submit"
        },
        close: {
          type: "plain_text",
          text: "Cancel"
        },
        private_metadata: JSON.stringify({
          threadTs,
          channelId,
          originalRequestData: requestData
        }),
        blocks: [
          {
            type: "input",
            block_id: "order_block",
            element: {
              type: "plain_text_input",
              action_id: "new_refund_amount",
              initial_value: refundAmount
            },
            label: {
              type: "plain_text",
              text: "Updated Refund Amount"
            }
          }
        ]
      }
    };

    const modalOptions = {
      method: "POST",
      contentType: "application/json",
      headers: {
        Authorization: `Bearer ${slackRefundsChannel.bearerToken}`
      },
      payload: JSON.stringify(modalViewPayload)
    };

    const response = UrlFetchApp.fetch("https://slack.com/api/views.open", modalOptions);
    const responseText = response.getContentText();
    const jsonResponse = JSON.parse(response.getContentText());
    // MailApp.sendEmail({
    //   to: DEBUG_EMAIL,
    //   subject: "Log Slack Response",
    //   htmlBody: `🧪 views.open response: ${responseText}`
    // });
    
    return jsonResponse

  } catch (error) {
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: "❌ Slack Modal Error in BARS Refund Request",
      htmlBody: `<pre>${error.stack}</pre>`
    });
  }
}

function updateRefundRequestOrderDetails({ requestData, channelId, threadTs, slackUserName, triggerId }) {
  try {
    const rowData = getRequestDetailsFromOrderNumber(requestData.rawOrderNumber);
    const { requestorEmail, requestorFirstName, requestorLastName } = rowData;
    const formattedOrderNumber = normalizeOrderNumber(requestData.rawOrderNumber);

    const modalViewPayload = {
      trigger_id: triggerId,
      view: {
        type: "modal",
        callback_id: "update_order_details_modal",
        title: {
          type: "plain_text",
          text: "Update Order Details"
        },
        submit: {
          type: "plain_text",
          text: "Submit"
        },
        close: {
          type: "plain_text",
          text: "Cancel"
        },
        private_metadata: JSON.stringify({
          threadTs,
          channelId,
          originalRequestData: requestData
        }),
        blocks: [
          {
            type: "input",
            block_id: "order_block",
            element: {
              type: "plain_text_input",
              action_id: "new_order_number",
              initial_value: formattedOrderNumber
            },
            label: {
              type: "plain_text",
              text: "Updated Order Number"
            }
          },
          {
            type: "input",
            block_id: "email_block",
            element: {
              type: "plain_text_input",
              action_id: "new_email",
              initial_value: requestorEmail
            },
            label: {
              type: "plain_text",
              text: "Updated Requestor Email"
            }
          }
        ]
      }
    };

    const modalOptions = {
      method: "POST",
      contentType: "application/json",
      headers: {
        Authorization: `Bearer ${slackRefundsChannel.bearerToken}`
      },
      payload: JSON.stringify(modalViewPayload)
    };

    const response = UrlFetchApp.fetch("https://slack.com/api/views.open", modalOptions);
    const responseText = response.getContentText();

  } catch (error) {
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: "❌ Slack Modal Error in BARS Refund Request",
      htmlBody: `<pre>${error.stack}</pre>`
    });
  }
}

function updateRefundRequestDetailsAfterModalSubmit({ newOrderNumber, newEmail, threadTs, channelId, rawOrderNumber }) {
  const formattedNewOrderNumber = normalizeOrderNumber(newOrderNumber);
  const formattedRawOrderNumber = normalizeOrderNumber(rawOrderNumber);

  const sheet = getSheet()
  const data = getSheetData()
  const headers = getSheetHeaders()

  const orderColIndex = headers.findIndex(h =>
    h.toLowerCase().includes("order number")
  );
  const emailColIndex = headers.findIndex(h =>
    h.toLowerCase().includes("email address")
  );

  const rowIndex = data.findIndex((row, i) => {
    if (i === 0) return false;
    const cellValue = row[orderColIndex];
    return normalizeOrderNumber(cellValue?.toString().trim()) === formattedRawOrderNumber;
  });

  if (rowIndex === -1) {
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: "❌ Could not update Google Sheet row for BARS Refund Request",
      htmlBody: `rawOrderNumber: ${rawOrderNumber}<br>formattedRawOrderNumber: ${formattedRawOrderNumber}`
    });
    return;
  }

  // ✅ Update the cell values in the sheet
  const sheetRow = rowIndex; // 0-indexed array, but 1-based sheet
  sheet.getRange(sheetRow + 1, orderColIndex + 1).setValue(formattedNewOrderNumber);
  sheet.getRange(sheetRow + 1, emailColIndex + 1).setValue(newEmail);

  // ✅ Now the sheet is updated, continue with refund logic
  const rowData = getRequestDetailsFromOrderNumber(formattedNewOrderNumber)
  const { requestSubmittedAt, requestorEmail, refundOrCredit, requestorFirstName, requestorLastName, requestNotes } = rowData
  const requestorName = { first: requestorFirstName, last: requestorLastName };

  const fetchedOrder = fetchShopifyOrderDetails({ orderName: formattedNewOrderNumber, email: null });

  const slackMessage = getSlackMessageText({ 
    requestorName,
    requestorEmail: newEmail,
    refundOrCredit,
    requestNotes,
    fetchedOrder,
    rawOrderNumber: formattedNewOrderNumber
  })

  const result = updateSlackMessage(slackRefundsChannel, {
    channel: channelId,
    ts: threadTs,
    blocks: slackMessage.blocks,
    text: slackMessage.text
  });

  if (!result || !result.ok) {
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: "❌ Slack update failed inside updateRefundRequestAfterModalSubmit in BARS Refund Request",
      htmlBody: `<pre>Channel: ${channelId}\nThread: ${threadTs}\nPayload:\n${JSON.stringify(slackMessage, null, 2)}</pre>`
    });
  }

}