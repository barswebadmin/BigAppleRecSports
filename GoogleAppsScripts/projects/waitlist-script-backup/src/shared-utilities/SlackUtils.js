/**
 * Slack Utilities for Waitlist System
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

function getJoeTestChannel() {
  try {
    const channelId = PropertiesService.getScriptProperties().getProperty('SLACK_CHANNEL_JOE_TEST');
    const bearerToken = getSlackBotToken('waitlist');

    if (!channelId) {
      Logger.log("⚠️ SLACK_CHANNEL_JOE_TEST not found in properties");
      return null;
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
    thread_ts: destination.threadTs || message.thread_ts
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
              text: `⏰ ${new Date().toLocaleString()} | 🤖 Waitlist System`
            }
          ]
        }
      ]
    };

    const result = sendSlackMessage(channel, message);
    return result.success;
  } catch (error) {
    Logger.log(`💥 Error in sendWaitlistValidationError: ${error.message}`);
    return false;
  }
}

