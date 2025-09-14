function sendPaymentPlanRequest(e,rowId) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const sheetHeaders = data[0];

  const requestName = e.namedValues["Name"][0]
  const requestTimestamp = e.namedValues["Timestamp"][0]
  const requestEmail = e.namedValues["Email Address"][0]
  const requestSport = e.namedValues["What sport do you want a payment plan for?"][0]
  const requestSeason = e.namedValues["What season are you requesting assistance for?"][0]
  const requestDayOfWeek = e.namedValues["What day of play are you registering for? (Payment Plan)"][0]
  const requestNumOfPayments = e.namedValues["Would you like to split your payments into 2 or 3 payments?"][0][0]

  Logger.log(`✅ New Payment Plan request detected for ${requestName}`);
  const fullNameIndex = sheetHeaders.indexOf("Name")
  const rowIdIndex = sheetHeaders.indexOf("Unique Row ID")

  // 📩 Prepare the Slack message
  const getColumnNumber = index => {
      let column = "";
      while (index >= 0) {
          column = String.fromCharCode((index % 26) + 65) + column;
          index = Math.floor(index / 26) - 1;
      }
      return column;
  };

  const getRowNumber = rowId => {
    const rowIndex = data.slice(1).findIndex(row => row[rowIdIndex] === rowId);

    // If not found, return null
    if (rowIndex === -1) return null;

    // Convert 0-based index to 1-based row number in the sheet
    return rowIndex + 2; // +2 to account for the header row (row 1)
};

  const SHEET_ID = "1j_nZjp3zU2cj-3Xgv1uX-velcfr9vmGu7SIpwNbhRPQ";
  const SHEET_URL = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/edit#gid=794849966&range=`;
  const rowLink = `${SHEET_URL}${getColumnNumber(fullNameIndex)}${getRowNumber(rowId)}`;

  const slackMessage = {
    text: `📌 *New Payment Plan Request Received!*`,
    blocks: [
      {
        type: "section",
        text: {
          type: "mrkdwn",
          text: `\n
          *New Payment Plan Request!* \n\n
          *Submitted on:* ${new Date(requestTimestamp).toLocaleString("en-US", {
              year: "2-digit",
              month: "numeric",
              day: "numeric",
              hour: "numeric",
              minute: "2-digit",
              hour12: true
            })} \n
          *Player Name:* ${requestName}\n
          *Email:* ${requestEmail}\n
          *Sport:* ${requestSport}\n
          *Season:* ${requestSeason}\n
          *Day of Play:* ${requestDayOfWeek}\n
          *Number of Payments:* ${requestNumOfPayments}\n
          \n
          🔗 *View Request Details in Google Sheets:* \n
          <${rowLink}|BARS Payment Assistance and Payment Plan Request Form (Responses)>`
        }
      },
      {
        type: "actions",
        elements: [
          {
            type: "button",
            text: {
              type: "plain_text",
              text: "✅ Approve"
            },
            style: "primary",
            action_id: "approve_payment_plan",
            value: JSON.stringify({ rowId, requestName, requestEmail }),
            confirm: {
              title: {
                type: "plain_text",
                text: "Confirm Approval"
              },
              text: {
                type: "mrkdwn",
                text: "Are you sure? The player will be notified of your decision."
              },
              confirm: {
                type: "plain_text",
                text: "Yes,  Approve"
              },
              deny: {
                type: "plain_text",
                text: "Cancel"
              }
            }
          },
          {
            type: "button",
            text: {
              type: "plain_text",
              text: "❌ Deny"
            },
            style: "danger",
            action_id: "deny_payment_plan",
            value: JSON.stringify({ rowId, requestName, requestEmail }),
            confirm: {
              title: {
                type: "plain_text",
                text: "Confirm Denial"
              },
              text: {
                type: "mrkdwn",
                text: "Are you sure? The player will be notified of your decision."
              },
              confirm: {
                type: "plain_text",
                text: "Yes, Deny"
              },
              deny: {
                type: "plain_text",
                text: "Cancel"
              }
            }
          }
        ]
      }
    ]
  };
  try {
    sendSlackMessage(financialAssistanceSlackChannel, slackMessage);
  } catch (e) {
    Logger.log(`❌ Error sending Slack message: ${e.message}`);
    sendSlackMessage(financialAssistanceSlackChannel, { text: `⚠️ Slack Error: ${e.message}` });
  }

}
