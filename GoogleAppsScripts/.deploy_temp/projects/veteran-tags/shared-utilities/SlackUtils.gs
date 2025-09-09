// =============================================================================
// Slack Utilities - Comprehensive Slack functionality for all Google Apps Script projects
// =============================================================================

// =============================================================================
// CORE SECRET MANAGEMENT
// =============================================================================

/**
 * Get a secret from PropertiesService
 * @param {string} key - Secret key name
 * @returns {string} - Secret value
 * @throws {Error} - If secret not found
 */
function getSecret(key) {
  const value = PropertiesService.getScriptProperties().getProperty(key);
  if (!value) {
    throw new Error(`Secret '${key}' not found. Make sure setupSecrets() was run in this project.`);
  }
  return value;
}

/**
 * Get Slack Bot Token from properties
 * @param {string} purpose - Purpose of the token (defaults to 'general')
 * @returns {string} - Slack bot token
 */
function getSlackBotToken(purpose = 'general') {
  const tokenMap = {
    'refunds': 'SLACK_BOT_TOKEN_REFUNDS',
    'leadership': 'SLACK_BOT_TOKEN_LEADERSHIP', 
    'payment': 'SLACK_BOT_TOKEN_PAYMENT',
    'general': 'SLACK_BOT_TOKEN_GENERAL',
    'waitlist': 'SLACK_BOT_TOKEN_WAITLIST'
  };
  const secretKey = tokenMap[purpose] || 'SLACK_BOT_TOKEN_GENERAL';
  
  try {
    const value = PropertiesService.getScriptProperties().getProperty(secretKey);
    if (!value) {
      Logger.log(`⚠️ Secret '${secretKey}' not found. Using fallback SLACK_BOT_TOKEN.`);
      return PropertiesService.getScriptProperties().getProperty('SLACK_BOT_TOKEN');
    }
    return value;
  } catch (error) {
    Logger.log(`💥 Error getting Slack token: ${error.message}`);
    return null;
  }
}

// =============================================================================
// CHANNEL CONFIGURATIONS
// =============================================================================

/**
 * Get Slack refunds channel configuration (MODE-aware for process-refunds-exchanges)
 * @returns {Object} - Channel configuration {name, channelId, bearerToken}
 */
function getSlackRefundsChannel() {
  // Check if MODE is defined (for process-refunds-exchanges project)
  if (typeof MODE !== 'undefined') {
    return MODE.includes('prod') ? 
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
      };
  }
  
  // Fallback for projects without MODE
  return {
    name: '#refunds',
    channelId: getSecret('SLACK_CHANNEL_REFUNDS_PROD'),
    bearerToken: getSlackBotToken('refunds')
  };
}

/**
 * Get joe-test channel configuration
 * @returns {Object} - Channel configuration
 */
function getJoeTestChannel() {
  try {
    const channelId = PropertiesService.getScriptProperties().getProperty('SLACK_CHANNEL_JOE_TEST');
    const bearerToken = getSlackBotToken('waitlist');
    
    if (!channelId) {
      Logger.log("⚠️ SLACK_CHANNEL_JOE_TEST not found in properties");
      // Fallback to a default channel ID if available
      return {
        name: '#joe-test',
        channelId: 'C08EXAMPLE', // Replace with actual channel ID
        bearerToken: bearerToken
      };
    }
    
    return {
      name: '#joe-test',
      channelId: channelId,
      bearerToken: bearerToken
    };
  } catch (error) {
    Logger.log(`💥 Error getting joe-test channel config: ${error.message}`);
    return null;
  }
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Get formatted order URL for Slack messages
 * @param {string} orderId - Order ID from Shopify
 * @param {string} orderName - Order name/number  
 * @returns {string} - Formatted Slack link
 */
const getOrderUrl = (orderId, orderName) => {
  const orderIdDigitsOnly = orderId?.split('/')?.at(-1) ?? '';
  return `<https://admin.shopify.com/store/09fe59-3/orders/${orderIdDigitsOnly}|${normalizeOrderNumber(orderName)}>`;
}

/**
 * Get formatted product URL for Slack messages
 * @param {Object} product - Product object with productId
 * @returns {string} - Product URL
 */
const getProductUrl = product => {
  const productId = product.productId.split("/").pop();
  return `https://admin.shopify.com/store/09fe59-3/products/${productId}`;
}

/**
 * Get Slack group ID for product notifications
 * @param {string} productTitle - Product title to check
 * @returns {string} - Slack group mention string
 */
const getSlackGroupId = productTitle => {
  const title = productTitle.toLowerCase();

  if (title.includes('kickball')) return '<!subteam^S08L2521XAM>';
  if (title.includes('bowling')) return '<!subteam^S08KJJ02738>';
  if (title.includes('pickleball')) return '<!subteam^S08KTJ33Z9R>';
  if (title.includes('dodgeball')) return '<!subteam^S08KJJ5CL4W>';

  return '@here'; // fallback so it doesn't return undefined
}

// =============================================================================
// CORE MESSAGING FUNCTIONS
// =============================================================================

/**
 * Send a message to Slack
 * @param {Object} destination - Channel configuration {channelId, bearerToken, threadTs}
 * @param {Object} message - Message object {text, blocks}
 * @returns {Object} - Response from Slack API
 */
function sendSlackMessage(destination, message) {
  if (!destination || !destination.channelId || !destination.bearerToken) {
    Logger.log("❌ Invalid Slack destination configuration");
    return { success: false, error: "Invalid destination configuration" };
  }

  const slackApiUrl = "https://slack.com/api/chat.postMessage";

  const payload = {
    channel: destination.channelId,
    text: message.text,
    blocks: message.blocks,
    thread_ts: destination.threadTs || message.thread_ts // Reply in the same thread if specified
  };

  const options = {
    method: "post",
    headers: { Authorization: `Bearer ${destination.bearerToken}` },
    contentType: "application/json",
    payload: JSON.stringify(payload)
  };

  try {
    const response = UrlFetchApp.fetch(slackApiUrl, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    const responseJson = JSON.parse(responseText);

    Logger.log(`📤 Slack API Response (${responseCode}): ${responseText}`);

    if (responseCode === 200 && responseJson.ok) {
      Logger.log(`✅ Message sent via Slack to ${destination.name}!`);
      return { success: true, data: responseJson };
    } else {
      const slackError = responseJson.error || "Unknown Slack API error";
      Logger.log(`❌ Slack API error: ${slackError}`);
      return { success: false, error: slackError };
    }
  } catch (error) {
    Logger.log(`💥 Error sending Slack message: ${error.message}`);
    return { success: false, error: error.message };
  }
}

/**
 * Update an existing Slack message
 * @param {Object} destination - Channel configuration {bearerToken}
 * @param {Object} updatedPayload - Updated message payload
 * @returns {Object} - Response object {ok, data?, error?}
 */
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
    if (typeof DEBUG_EMAIL !== 'undefined') {
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: "❌ Debug: Error Updating Slack Message",
        body: `Error message: ${error.message}\n\nSlack API Response:\n\n Updated Payload: ${JSON.stringify(updatedPayload, null, 2)}`
      });
    }
    return { ok: false, error: error.message };
  }
}

// =============================================================================
// REFUND-SPECIFIC BUTTON BUILDERS
// =============================================================================

/**
 * Create confirm refund button
 * @param {Object} params - Button parameters
 * @returns {Object} - Slack button object
 */
const createConfirmButton = ({ emailMatches, requestorName, refundOrCredit, refundAmount, rawOrderNumber, orderId }) => {
  const formattedAmount = Number.isInteger(refundAmount) ? Number.parseInt(refundAmount) : formatTwoDecimalPoints(refundAmount);

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
  };
  
  if (emailMatches) {
    button.style = "primary";
  }

  return button;
}

/**
 * Create deny refund button
 * @param {Object} params - Button parameters
 * @returns {Object} - Slack button object
 */
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
  };   
}

/**
 * Create custom refund amount button
 * @param {Object} params - Button parameters
 * @returns {Object} - Slack button object
 */
const createRefundDifferentAmountButton = ({ orderId, orderName, requestorName, requestorEmail, refundOrCredit, refundAmount, rawOrderNumber }) => ({
  type: "button",
  text: {
    type: "plain_text",
    text: `✏️ ${refundOrCredit.toLowerCase() === "refund" ? "Process custom Refund amt" : "Issue custom Store Credit amt"}`
  },
  action_id: "refund_different_amount",
  value: `orderId=${orderId}|refundAmount=${refundAmount}|rawOrderNumber=${rawOrderNumber}`,
});

/**
 * Create cancel request button
 * @param {Object} params - Button parameters
 * @returns {Object} - Slack button object
 */
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

/**
 * Create inventory restock buttons
 * @param {Object} params - Button parameters
 * @returns {Array} - Array of Slack button objects
 */
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

// =============================================================================
// SPECIALIZED MESSAGE FUNCTIONS
// =============================================================================

/**
 * Send waitlist validation error to joe-test channel
 * @param {string} league - League name
 * @param {string} email - User email
 * @param {string} reason - Validation failure reason
 * @param {string} productHandle - Product handle that was checked
 */
function sendWaitlistValidationError(league, email, reason, productHandle) {
  try {
    const channel = getJoeTestChannel();
    if (!channel) {
      Logger.log("❌ Could not get joe-test channel configuration");
      return false;
    }

    const errorIcon = reason.includes("No product found") ? "🚫" : "📦";
    const title = reason.includes("No product found") ? "Product Not Found" : "Inventory Available";
    
    const message = {
      text: `${errorIcon} Waitlist Validation Error: ${title}`,
      blocks: [
        {
          type: "header",
          text: {
            type: "plain_text",
            text: `${errorIcon} Waitlist Validation Error`
          }
        },
        {
          type: "section",
          fields: [
            {
              type: "mrkdwn",
              text: `*Error Type:*\n${title}`
            },
            {
              type: "mrkdwn", 
              text: `*League:*\n${league}`
            },
            {
              type: "mrkdwn",
              text: `*User Email:*\n${email}`
            },
            {
              type: "mrkdwn",
              text: `*Product Handle:*\n\`${productHandle}\``
            }
          ]
        },
        {
          type: "section",
          text: {
            type: "mrkdwn",
            text: `*Reason:* ${reason}`
          }
        },
        {
          type: "context",
          elements: [
            {
              type: "mrkdwn",
              text: `⏰ ${new Date().toLocaleString()} | 🤖 Waitlist Script Validation`
            }
          ]
        }
      ]
    };

    const result = sendSlackMessage(channel, message);
    if (result.success) {
      Logger.log(`✅ Sent waitlist validation error to #joe-test for ${email}`);
      return true;
    } else {
      Logger.log(`❌ Failed to send waitlist validation error: ${result.error}`);
      return false;
    }
  } catch (error) {
    Logger.log(`💥 Error in sendWaitlistValidationError: ${error.message}`);
    return false;
  }
}