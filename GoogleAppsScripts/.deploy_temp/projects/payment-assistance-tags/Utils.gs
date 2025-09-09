const SHOPIFY_ACCESS_TOKEN = "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";
const SHOPIFY_GRAPHQL_URL = "https://09fe59-3.myshopify.com/admin/api/2025-01/graphql.json"
const SHEET_ID = "1j_nZjp3zU2cj-3Xgv1uX-velcfr9vmGu7SIpwNbhRPQ";
const SHEET_URL = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/edit#gid=794849966&range=`;

function generateUid() {
    var allChars = "0123456789abcdefghijklmnopqrstuvwxyz";
    var id = "";
    for (var i = 0; i < 8; i++) {
      id += allChars.charAt(Math.floor(Math.random() * allChars.length));
    }
    return id;
}

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


function updateSlackMessage(updatedMessage) {
  const slackApiUrl = "https://slack.com/api/chat.update";

  const options = {
    method: "post",
    headers: { Authorization: `Bearer ${financialAssistanceSlackChannel.bearerToken}` },
    contentType: "application/json",
    payload: JSON.stringify(updatedMessage)
  };

  try {

    const response = UrlFetchApp.fetch(slackApiUrl, options);
    const responseText = response.getContentText();
    const responseJson = JSON.parse(responseText);

    if (!responseJson.ok) {
      throw new Error(`Slack API Error: ${responseJson.error}`);
    }

  } catch (error) {
    // ❌ If an error occurs, send an email with the error message
    MailApp.sendEmail({
      to: "joe@bigapplerecsports.com",
      subject: "❌ Debug: Error Updating Slack Message",
      body: `Error message: ${error.message}\n\nSlack API Response:\n\n${JSON.stringify(updatedMessage, null, 2)}`
    });
  }
}








const fetchShopify = (query = {}) => {
  try {
    const options = {
      method: "POST",
      contentType: "application/json",
      headers: { "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN },
      payload: JSON.stringify(query)
    };
    const response = UrlFetchApp.fetch(SHOPIFY_GRAPHQL_URL, options);
    const jsonResponse = JSON.parse(response.getContentText());

    if (jsonResponse.errors) {
      Logger.log(`❌ Shopify API Errors: ${JSON.stringify(jsonResponse.errors)}`);
    }

    return jsonResponse.data;
  } catch (error) {
    Logger.log(`❌ Shopify Fetch Error: ${error.message}`);
    return null;
  }
};

const capitalize = string => {
  return string[0].toUpperCase(0) + string.slice(1)
}

const formatDate = (date) => {
  if (!(date instanceof Date) || isNaN(date)) {
    return "Invalid Date"; // Handle incorrect date inputs
  }

  const month = date.getMonth() + 1; // Months are 0-indexed in JS
  const day = date.getDate();
  const year = date.getFullYear().toString().slice(-2); // Get last 2 digits of year

  return `${month}/${day}/${year}`;
};

const generateRepaymentDetails = ({ planDetails, matchingProductRow }) => {
    const { seasonStartDate, seasonEndDate, price } = matchingProductRow || {};
    const { numOfPayments } = planDetails || {};

    let repaymentDetails = []

    if (!seasonStartDate || !seasonEndDate || !price || !numOfPayments) {
        Logger.log("❌ Missing required values for repayment calculation.");
        return []; // ✅ Always return an array, even if empty
    }

    if (numOfPayments === 2) {
        // Calculate halfway date
        const halfwayDate = new Date(seasonStartDate.getTime() + (seasonEndDate - seasonStartDate) / 2);
        const paymentAmount = (price / numOfPayments).toFixed(2);

        Logger.log(`half: ${halfwayDate}, end: ${seasonEndDate}, paymentAmount: ${paymentAmount}`)
        repaymentDetails.push(`Payment 1: $${paymentAmount} due on ${formatDate(halfwayDate)}`);
        repaymentDetails.push(`Payment 2: $${paymentAmount} due on ${formatDate(seasonEndDate)}`);
    } 
    
    else if (numOfPayments === 3) {
        const paymentAmount = (price / numOfPayments).toFixed(2);
        let paymentDate = new Date(); // Start with today

        for (let i = 1; i <= numOfPayments; i++) {
            // Move to the first of the next month
            paymentDate.setMonth(paymentDate.getMonth() + 1, 1);
            Logger.log(`payment: ${paymentDate}, amount: ${paymentAmount}`)
            repaymentDetails.push(`Payment ${i}: $${paymentAmount} due on ${formatDate(paymentDate)}`);
        }
    }
    if (repaymentDetails.length > 0) {
        Logger.log("✅ Repayment Details:", repaymentDetails.join(", "));
    } else {
        Logger.log("❌ Repayment details were not generated. Check input values.");
    }

    return repaymentDetails;
};