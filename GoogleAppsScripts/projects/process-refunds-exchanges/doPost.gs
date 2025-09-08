function doPost(e) {

  try {
    if (!e.postData || !e.postData.contents) {
      throw new Error("Missing postData or contents in request");
    }

    // Slack sends payload as x-www-form-urlencoded
    const raw = decodeURIComponent(e.postData.contents);
    
    const payloadStr = raw.startsWith("payload=") ? raw.slice("payload=".length) : raw;
    const payload = JSON.parse(payloadStr);
    const payloadType = payload.type;

    const slackUserId = payload.user.id;
    const slackUserName = `<@${slackUserId}>`;

    const requestData = {}
    let action
    let actionId
    let threadTs;
    let channelId;

    if (payloadType === "block_actions") {
      action = payload.actions[0]
      actionId = action.action_id;

      const buttonValues = action.value.split('|');
      for (const buttonValue of buttonValues) {
        const [key, value] = buttonValue.split('=');
        requestData[key] = value;
      }

      threadTs = payload.message?.ts;
      channelId = payload.channel?.id || payload.container?.channel_id;
    }

    if (payloadType === "view_submission" && payload.view.callback_id === "update_refund_amount_modal") {
      const values = payload.view.state.values;
      const newRefundAmount = values.order_block.new_refund_amount.value.trim();
      const metadata = JSON.parse(payload.view.private_metadata);
      const threadTs = metadata.threadTs;
      const channelId = metadata.channelId;

      // MailApp.sendEmail({
      //   to: DEBUG_EMAIL,
      //   subject: "Debug doPost 3",
      //   htmlBody: `updating refund amount from modal with: \n
      //   values: ${JSON.stringify(values,null,2)} \n
      //   newRefundAmount: ${JSON.stringify(newRefundAmount,null,2)} \n
      //   metadata: ${JSON.stringify(metadata,null,2)} \n
      //   threadTs: ${JSON.stringify(threadTs,null,2)} \n
      //   channelId: ${JSON.stringify(channelId,null,2)} \n`
      // });

      const slackResponse = ContentService
      .createTextOutput(JSON.stringify({ response_action: "clear" }))
      .setMimeType(ContentService.MimeType.JSON);

      const oldRefundAmount = requestData.refundAmount

      const updatedRequestData = {...metadata.originalRequestData, refundAmount: newRefundAmount, oldRefundAmount}

      if (MODE.include('prod')) {
        approveRefundRequest( updatedRequestData, channelId, threadTs, slackUserName )

        // ✅ Defer background work to ensure modal closes first
        Utilities.sleep(3); // Let Slack process the response

        // ✅ Continue work in background
        // updateRefundRequestAfterModalSubmit({
        //   ...metadata,
        //   newOrderNumber,
        //   newEmail,
        //   rawOrderNumber: metadata.originalRequestData.rawOrderNumber,
        //   channelId: metadata.channelId,
        //   threadTs: metadata.threadTs
        // });

        return slackResponse
      }
      else {
        approveRefundRequestDebugVersion(requestData, channelId, threadTs, slackUserName);
        Utilities.sleep(3); // Let Slack process the response
      }
    }

    if (payloadType === "view_submission" && payload.view.callback_id === "update_order_details_modal") {
      const values = payload.view.state.values;
      const newOrderNumber = values.order_block.new_order_number.value.trim();
      const newEmail = values.email_block.new_email.value.trim().toLowerCase();
      const metadata = JSON.parse(payload.view.private_metadata);

      const slackResponse = ContentService
      .createTextOutput(JSON.stringify({ response_action: "clear" }))
      .setMimeType(ContentService.MimeType.JSON);

      // ✅ Defer background work to ensure modal closes first
      Utilities.sleep(5); // Let Slack process the response

      // ✅ Continue work in background
      updateRefundRequestDetailsAfterModalSubmit({
        ...metadata,
        newOrderNumber,
        newEmail,
        rawOrderNumber: metadata.originalRequestData.rawOrderNumber,
        channelId: metadata.channelId,
        threadTs: metadata.threadTs
      });

      return slackResponse
    }

    if (actionId === "approve_refund") {
      try {
        if (MODE.includes('prod')) {
          approveRefundRequest(requestData, channelId, threadTs, slackUserName)
        }
        else {
          approveRefundRequestDebugVersion(requestData, channelId, threadTs, slackUserName);
        }
      } catch (error) {
        MailApp.sendEmail({
          to: DEBUG_EMAIL,
          subject: "❌ Error inside approveRefundRequest()",
          htmlBody: `<pre>${error.stack}</pre>`
        });
        return ContentService.createTextOutput(""); // exit gracefully
      }

    } else if (actionId === "deny_refund") {
      try {
        denyRefundRequest(requestData, channelId, threadTs, slackUserName);
      } catch (error) {
        MailApp.sendEmail({
          to: DEBUG_EMAIL,
          subject: "❌ Error inside denyRefundRequest()",
          htmlBody: `<pre>${error.stack}</pre>`
        });
        return ContentService.createTextOutput(""); // exit gracefully
      }

    } else if (actionId === 'update_order_details') {
      const triggerId = payload.trigger_id;
      
      updateSlackMessage(slackRefundsChannel,{
        channel: channelId,
        ts: threadTs,
        text: "Refund request is being updated",
        blocks: [
          {
            type: "context",
            elements: [
              {
                type: "mrkdwn",
                text: `🔄 *Request is being updated with new order/email by ${slackUserName}*`
              }
            ]
          }
        ]
      });

      updateRefundRequestOrderDetails({ requestData, channelId, threadTs, slackUserName, triggerId })

    } else if (actionId === 'refund_different_amount') {
      const triggerId = payload.trigger_id;

      const modalResponse = updateRefundRequestAmount({
        requestData,
        channelId,
        threadTs,
        slackUserName,
        triggerId
      });
      if (modalResponse?.ok) {
        Utilities.sleep(4); // Allow Slack time to process modal

        // updateSlackMessage(slackRefundsChannel, {
        //   channel: channelId,
        //   ts: threadTs,
        //   text: "Refund request is being updated",
        //   blocks: [
        //     {
        //       type: "context",
        //       elements: [
        //         {
        //           type: "mrkdwn",
        //           text: `🔄 *Request is being processed for a different amount by ${slackUserName}*`
        //         }
        //       ]
        //     }
        //   ]
        // });
      } else {
        MailApp.sendEmail({
          to: DEBUG_EMAIL,
          subject: "❌ Slack Modal Failed to Open for Refund Adjustment",
          htmlBody: `<pre>${JSON.stringify(modalResponse, null, 2)}</pre>`
        });
      }

    } else if (actionId === 'cancel_refund_request') {
      cancelRefundRequest(requestData, channelId, threadTs, slackUserName)

    } else if (actionId.includes('restock')) {
      try {
        restockInventory({requestData, actionId, channelId, threadTs, slackUserName})
      } catch (error) {
        MailApp.sendEmail({
          to: DEBUG_EMAIL,
          subject: "❌ Error inside restockInventory()",
          htmlBody: `<pre>${error.stack}</pre>`
        });
        return ContentService.createTextOutput(""); // exit gracefully
      }
      
    } else {
      Logger.log(`⚠️ Unknown action_id: ${actionId}`);
    }

    return ContentService.createTextOutput(""); // just return empty

  } catch (error) {
    const fallback = e?.postData?.contents || "[no postData]";
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `❌ Error in doPost() - Slack Refund`,
      htmlBody: `
        <p><strong>Error refunding order:</strong> ${error.message}</p>
        <p>Request details: ${JSON.stringify(requestDetails,null,2)}</p>
        <p><strong>Raw Payload:</strong></p>
        <pre>${decodeURIComponent(fallback)}</pre>
      `
    });
  }
}