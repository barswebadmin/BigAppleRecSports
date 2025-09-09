// Helper functions for secrets (copy these to scripts that need them)
function getSecret(key) {
  const value = PropertiesService.getScriptProperties().getProperty(key);
  if (!value) {
    throw new Error(`Secret '${key}' not found. Make sure setupSecrets() was run in this project.`);
  }
  return value;
}

function getSlackBotToken(purpose = 'general') {
  const tokenMap = {
    'refunds': 'SLACK_BOT_TOKEN_REFUNDS',
    'leadership': 'SLACK_BOT_TOKEN_LEADERSHIP', 
    'payment': 'SLACK_BOT_TOKEN_PAYMENT',
    'general': 'SLACK_BOT_TOKEN_GENERAL'
  };
  const secretKey = tokenMap[purpose] || 'SLACK_BOT_TOKEN_GENERAL';
  return getSecret(secretKey);
}

const getOrderUrl = (orderId,orderName) => {
  const orderIdDigitsOnly = orderId?.split('/')?.at(-1) ?? '';
  return `<https://admin.shopify.com/store/09fe59-3/orders/${orderIdDigitsOnly}|${normalizeOrderNumber(orderName)}>`
}

const getProductUrl = product => {
  const productId = product.productId.split("/").pop();
  return `https://admin.shopify.com/store/09fe59-3/products/${productId}`;
}

const slackRefundsChannel = MODE.includes('prod') ? 
  {
    name: '#refunds',
    channelId: getSecret('SLACK_CHANNEL_REFUNDS_PROD'),
    bearerToken: getSlackBotToken('refunds')
  } 
  :
  { 
    name: '#joe-test',
    channelId: getSecret('SLACK_CHANNEL_JOE_TEST'),
    bearerToken: getSlackBotToken('refunds')
  }

const getSlackGroupId = productTitle => {
  const title = productTitle.toLowerCase();

  if (title.includes('kickball')) return '<!subteam^S08L2521XAM>';
  if (title.includes('bowling')) return '<!subteam^S08KJJ02738>';
  if (title.includes('pickleball')) return '<!subteam^S08KTJ33Z9R>';
  if (title.includes('dodgeball')) return '<!subteam^S08KJJ5CL4W>';

  return '@here'; // fallback so it doesn't return undefined
}

const createConfirmButton = ({ emailMatches, requestorName, refundOrCredit, refundAmount, rawOrderNumber, orderId }) => {
  const formattedAmount = Number.isInteger(refundAmount) ? Number.parseInt(refundAmount) : formatTwoDecimalPoints(refundAmount)

  const button = {
    type: "button",
    text: {
      type: "plain_text",
      text: `✅ ${refundOrCredit === "refund" ? `Process $${formattedAmount} Refund` : `Issue $${formattedAmount} Store Credit`}`
    },
    action_id: "approve_refund",
    value: `rawOrderNumber=${rawOrderNumber}|orderId=${orderId}|refundAmount=${refundAmount}`,
    confirm: {
      title: {
        type: "plain_text",
        text: "Confirm Approval"
      },
      text: {
        type: "plain_text",
        text: `You are about to issue ${requestorName.first} ${requestorName.last} a ${refundOrCredit} for $${formattedAmount}. Proceed?`
      },
      confirm: {
        type: "plain_text",
        text: "Yes, confirm"
      },
      deny: {
        type: "plain_text",
        text: "Cancel"
      }
    }      
  }
  
  if (emailMatches) {
    button.style = "primary";
  }

  return button
}

const createDenyButton = ({ rawOrderNumber }) => {
  return {
    type: "button",
    text: {
      type: "plain_text",
      text: "❌ Deny"
    },
    style: "danger",
    action_id: "deny_refund",
    value: `rawOrderNumber=${rawOrderNumber}`,
    confirm: {
      title: {
        type: "plain_text",
        text: "Confirm Denial"
      },
      text: {
        type: "plain_text",
        text: "Are you sure? The requestor will be notified."
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
}

const createRefundDifferentAmountButton = ({ orderId, orderName, requestorName, requestorEmail, refundOrCredit, refundAmount, rawOrderNumber }) => ({
  type: "button",
  text: {
    type: "plain_text",
    text: `✏️ ${refundOrCredit.toLowerCase() === "refund" ? "Process custom Refund amt" : "Issue custom Store Credit amt"}`
  },
  action_id: "refund_different_amount",
  value: `orderId=${orderId}|refundAmount=${refundAmount}|rawOrderNumber=${rawOrderNumber}`,
});

const createCancelButton = ({ rawOrderNumber }) => ({
  type: "button",
  text: {
    type: "plain_text",
    text: "❌ Cancel and Close Request"
  },
  style: "danger",
  action_id: "cancel_refund_request",
  value: `rawOrderNumber=${rawOrderNumber}`,
  confirm: {
    title: {
      type: "plain_text",
      text: "Confirm Cancellation"
    },
    text: {
      type: "plain_text",
      text: "Are you sure you want to cancel and close this request?"
    },
    confirm: {
      type: "plain_text",
      text: "Yes, cancel and close it"
    },
    deny: {
      type: "plain_text",
      text: "No, keep it"
    }
  }
});

function sendSlackMessage(destination, message) {
  const channelId = destination.channelId
  const threadTs = destination.threadTs
  const slackApiUrl = "https://slack.com/api/chat.postMessage";

  const payload = {
    channel: channelId,
    text: message.text,
    blocks: message.blocks,
    thread_ts: threadTs // Reply in the same thread
  };

  const botToken = destination.bearerToken || slackExecChannel.bearerToken;

  const options = {
    method: "post",
    headers: { Authorization: `Bearer ${botToken}` },
    contentType: "application/json",
    payload: JSON.stringify(payload)
  };

  try {
    const response = UrlFetchApp.fetch(slackApiUrl, options);
    const responseCode = response.getResponseCode(); // Get HTTP status code
    const responseText = response.getContentText(); // Get response as text
    const responseJson = JSON.parse(responseText); // Parse response

    if (responseCode >= 200 && responseCode < 300 && responseJson.ok) {
      Logger.log(`✅ Message sent via Slack to ${destination.name}! Response: ${responseText}`);
      return;
    }

    // Log Slack API error messages if any
    const slackError = responseJson.error || "Unknown Slack API error";
    throw new Error(`❌ Failed to send Slack message to ${destination.name}. Slack Error: ${slackError}`);
  
  } catch (error) {
    Logger.log(`❌ Error sending message to Slack: ${error.message}`);
    throw new Error(`⚠️ The 'Process Payment Assistance and Payment Plans' workflow failed to send a Slack message: ${error.message}`);
  }
}

const createRestockInventoryButtons = ({ orderId, refundAmount, formattedOrderNumber, inventoryList, inventoryOrder, slackUserName }) => {

  const buttons = inventoryOrder
    .filter(key => inventoryList[key]?.variantId)
    .map(key => {
      const variant = inventoryList[key];
      const nameWithoutRegistration = variant.name.replace(/ Registration/i, '').trim();
      return {
        type: "button",
        text: {
          type: "plain_text",
          text: `Restock ${nameWithoutRegistration}`
        },
        action_id: `restock_${nameWithoutRegistration.toLowerCase()}`,
        value: [
          `inventoryItemId=${variant.inventoryId}`,
          `orderId=${orderId}`,
          `refundAmount=${refundAmount}`,
          `orderNumber=${formattedOrderNumber}`,
          `approverName=${slackUserName}`
        ].join('|'),
        confirm: {
          title: {
            type: "plain_text",
            text: `Confirm Restocking ${nameWithoutRegistration}`
          },
          text: {
            type: "plain_text",
            text: `You are about to restock 1 spot to ${nameWithoutRegistration}. Confirm?`
          },
          confirm: {
            type: "plain_text",
            text: "Yes, confirm"
          },
          deny: {
            type: "plain_text",
            text: "No, go back"
          }
        }  
      };
    });

  // Add the "Do not restock" option
  buttons.push({
    type: "button",
    text: {
      type: "plain_text",
      text: "Do not restock - all done!"
    },
    action_id: "do_not_restock",
    value: [
      `orderId=${orderId}`,
      `refundAmount=${refundAmount}`,
      `orderNumber=${formattedOrderNumber}`
    ].join('|'),
    confirm: {
      title: {
        type: "plain_text",
        text: "Confirm No Restocking"
      },
      text: {
        type: "plain_text",
        text: `Are you sure you do not want to restock inventory?`
      },
      confirm: {
        type: "plain_text",
        text: "Yes, confirm"
      },
      deny: {
        type: "plain_text",
        text: "No, go back"
      }
    }  
  });

  return buttons;
};


function updateSlackMessage(destination, updatedPayload) {
  const slackApiUrl = "https://slack.com/api/chat.update";

  const options = {
    method: "post",
    headers: { Authorization: `Bearer ${destination.bearerToken}` },
    contentType: "application/json",
    payload: JSON.stringify(updatedPayload)
  };

  try {
    const response = UrlFetchApp.fetch(slackApiUrl, options);
    const responseText = response.getContentText();
    const responseJson = JSON.parse(responseText);

    if (!responseJson.ok) {
      throw new Error(`Slack API Error: ${responseJson.error}`);
    }

    return {ok: true, data: responseJson};

  } catch (error) {
    // ❌ If an error occurs, send an email with the error message
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: "❌ Debug: Error Updating Slack Message",
      body: `Error message: ${error.message}\n\nSlack API Response:\n\n Updated Payload: ${JSON.stringify(updatedPayload, null, 2)}`
    });
    return { ok: false, error: error.message };
  }
}