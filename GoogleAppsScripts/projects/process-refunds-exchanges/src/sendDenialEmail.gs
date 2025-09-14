/**
 * Send denial email to requestor
 * Called by backend when a refund request is denied via Slack
 *
 * @fileoverview Handles sending denial emails to requestors
 * @requires config.gs for constants
 */

/**
 * Send denial email to requestor for denied refund request
 * @param {Object} data - The denial data from backend
 * @param {string} data.order_number - Order number
 * @param {string} data.requestor_email - Requestor's email
 * @param {string} data.first_name - Requestor's first name
 * @param {string} data.last_name - Requestor's last name
 * @param {string} data.custom_message - Custom denial message (optional)
 * @param {boolean} data.include_staff_info - Whether to include staff info
 * @param {string} data.slack_user_name - Slack user name who denied
 * @param {string} data.slack_user_id - Slack user ID who denied
 */
function sendDenialEmail(data) {
  try {
    Logger.log(`📧 === SENDING DENIAL EMAIL ===`);
    Logger.log(`📦 Data: ${JSON.stringify(data, null, 2)}`);

    const {
      order_number,
      requestor_email,
      first_name,
      last_name,
      custom_message,
      include_staff_info,
      slack_user_name,
      slack_user_id
    } = data;

    // Get BARS logo for email
    const barsLogoBlob = UrlFetchApp
                        .fetch(BARS_LOGO_URL)
                        .getBlob()
                        .setName("barsLogo");

    // Build email subject
    const subject = `Big Apple Rec Sports - Order ${order_number} - Refund Request Denied`;

    // Build email body
    // let htmlBody = `<p>Hi ${first_name},</p>`;

    if (custom_message && custom_message.trim()) {
      // Use custom message if provided
      htmlBody += `<p>${custom_message.replace(/\n/g, '<br>')}</p>`;
    } else {
      // Use default message
      htmlBody += `
        <p>We're sorry, but we were not able to approve your refund request for Order ${order_number}.</p>
        <p>Please <a href="${SHOPIFY_LOGIN_URL}">sign in to view your orders</a> and try again if needed.</p>
      `;
    }

    // Add additional info section if custom message was provided
    // if (custom_message && custom_message.trim()) {
    //   htmlBody += `
    //     <p><strong>Additional Info:</strong> ${custom_message.replace(/\n/g, '<br>')}</p>
    //   `;
    // }

    // Add staff contact info if requested
    // if (include_staff_info) {
    //   htmlBody += `
    //     <br>
    //     <p>If you have any questions about this decision, you can reach out to ${slack_user_name} who processed your request.</p>
    //   `;
    // }

    // Add general contact info
    htmlBody += `
      <p>If you have any questions, please reach out to <a href="mailto:refunds@bigapplerecsports.com">refunds@bigapplerecsports.com</a></p>
    `;

    // Add BARS signature
    htmlBody += `
      --<br>
      <p>
        Warmly,<br>
        <b>BARS Leadership</b>
      </p>
      <img src="cid:barsLogo" style="width:225px; height:auto;">
    `;

    // Send the email
    MailApp.sendEmail({
      to: requestor_email,
      replyTo: 'refunds@bigapplerecsports.com',
      subject: subject,
      htmlBody: htmlBody,
      inlineImages: { barsLogo: barsLogoBlob }
    });

    Logger.log(`✅ Denial email sent successfully to ${requestor_email}`);

    // Send confirmation email to debug address
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `✅ BARS Denial Email - Sent Successfully`,
      htmlBody: `
        <h3>✅ Denial Email Sent Successfully</h3>
        <p><strong>Order:</strong> ${order_number}</p>
        <p><strong>Requestor:</strong> ${first_name} ${last_name} (${requestor_email})</p>
        <p><strong>Processed by:</strong> ${slack_user_name}</p>
        <p><strong>Custom Message:</strong> ${custom_message ? 'Yes' : 'No'}</p>
        <p><strong>Staff Info Included:</strong> ${include_staff_info ? 'Yes' : 'No'}</p>
        <hr>
        <h4>Email Content Sent:</h4>
        ${htmlBody}
      `
    });

    return {
      success: true,
      message: `Denial email sent successfully to ${requestor_email}`
    };

  } catch (error) {
    const errorMessage = `Error sending denial email: ${error.toString()}`;
    Logger.log(`❌ ${errorMessage}`);

    // Send error notification
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `❌ BARS Denial Email - Error`,
      htmlBody: `
        <h3>❌ Error Sending Denial Email</h3>
        <p><strong>Error:</strong> ${errorMessage}</p>
        <p><strong>Order:</strong> ${data.order_number || 'Unknown'}</p>
        <p><strong>Requestor:</strong> ${data.requestor_email || 'Unknown'}</p>
        <p><strong>Stack:</strong> <pre>${error.stack || 'No stack trace available'}</pre></p>
      `
    });

    return {
      success: false,
      message: errorMessage
    };
  }
}
