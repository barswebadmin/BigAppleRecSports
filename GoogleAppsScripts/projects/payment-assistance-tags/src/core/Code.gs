function doGet(e) {
  Logger.log(`🔍 Executing as: ${Session.getEffectiveUser().getEmail()}`);
  const params = e.parameter;

  if (!params.type) {
    return HtmlService.createHtmlOutput("<h3>❌ Invalid Request: Missing 'type' parameter</h3>");
  }

  switch (params.type) {
    case "discount":
      return processDiscountApproval(params.action, params.rowId);

    case "paymentPlan":
      return processPaymentPlanRequest(params.action, params.rowId);

    default:
      return HtmlService.createHtmlOutput("<h3>❌ Unknown request type</h3>");
  }

}

function doPost(e) {
  try {
    const payload = JSON.parse(e.parameters.payload);
    const { rowId, requestName, requestEmail } = JSON.parse(payload.actions[0].value);
    const actionType = payload.actions[0].action_id;
    const channelId = payload.channel?.id || payload.container?.channel_id;
    const threadTs = payload.message.ts;
    const slackUserId = payload.user.id
    const slackUserName = `<@${slackUserId}>`

    if (!actionType || !rowId || !channelId || !threadTs) {
        throw new Error(`Missing required values: actionType=${actionType}, rowId=${rowId}, channelId=${channelId}, threadTs=${threadTs}`);
    }

    // ✅ Process the request
    let result = processPaymentPlanRequest(actionType, rowId, requestName, requestEmail);

    if (result.success) {
        // ✅ Success → Remove buttons and update Slack message
        const updatedMessage = {
          channel: channelId,
          ts: threadTs,
          text: `📌 *Payment Plan Request ${actionType === "approve_payment_plan" ? "Approved ✅" : "Denied ❌"} by ${requestName}*`,
          blocks: [
            {
              type: "section",
              text: {
                type: "mrkdwn",
                text: `*Request Status:* ${actionType === "approve_payment_plan" ? "✅ Approved" : "❌ Denied"}\n
                *Processed by:* ${slackUserName}\n \n
                ${result.message}`
              }
            }
          ]
        };
        updateSlackMessage(updatedMessage);
    } else {
        // ❌ Failure → Keep buttons active, update Slack message with error
        const failedMessage = {
          channel: channelId,
          ts: threadTs,
          text: `📌 *Payment Plan Request Failed ❌*`,
          blocks: [
            {
              type: "section",
              text: {
                type: "mrkdwn",
                text: `⚠️ *Request Processing Failed* \n
                *Attempted by:* ${slackUserName} \n
                *Email:* ${requestEmail} \n
                ❌ *Error:* ${result.message} \n \n
                Please check the details and try again. The buttons remain active for another attempt.`
              }
            }
          ]
        };
        updateSlackMessage(failedMessage);
    }

  } catch (error) {
    Logger.log(`❌ Error handling Slack request: ${error.message}`);
    MailApp.sendEmail({
        to: "web@bigapplerecsports.com",
        subject: "❌ Slack Webhook Error",
        htmlBody: `⚠️ Error processing Slack button click: ${error.message}. Attempted to send:
        - actionType: ${e.parameters?.payload ? JSON.parse(e.parameters.payload)?.actions?.[0]?.action_id : "N/A"}
        - channelId: ${e.parameters?.payload ? JSON.parse(e.parameters.payload)?.channel?.id || JSON.parse(e.parameters.payload)?.container?.channel_id : "N/A"}
        - threadTs: ${e.parameters?.payload ? JSON.parse(e.parameters.payload)?.message?.ts : "N/A"}`
    });
  }
}
