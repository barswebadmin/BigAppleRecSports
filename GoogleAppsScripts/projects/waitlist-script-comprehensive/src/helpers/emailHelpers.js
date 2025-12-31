/**
 * Email Helper Functions
 * Sending emails to players and admins
 */

import { BARS_LOGO_URL, DEBUG_EMAIL, WAITLIST_WEB_APP_URL } from '../config/constants';
import { capitalize } from '../shared-utilities/formatters';
import { getLeadershipEmailForLeague, getLeagueInfo } from './utils';

const emailFooterWithLinks = `
<div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
      <p>Warmly,<br>
      <b>BARS Leadership</b></p>
      <img src="cid:barsLogo" style="width:225px; height:auto; margin-top: 15px;">
        <p><strong>Big Apple Rec Sports</strong><br>
        Follow us: <a href="https://www.instagram.com/bigapplerecsports/">Instagram</a> | <a href="https://www.facebook.com/groups/bigapplerecsports">Facebook</a></p>
      </div>
      `


/**
 * Send waitlist confirmation email with interactive position checker
 * @param {string} email - Customer email
 * @param {string} league - League name
 * @param {number} waitlistSpot - Position on waitlist
 * @param {string} firstName - Customer's first name (optional, defaults to email prefix)
 * @returns {boolean} - Success
 */
export function sendWaitlistConfirmationEmail(email, league, waitlistSpot, firstName) {
  try {
    Logger.log(`📧 === SENDING WAITLIST CONFIRMATION EMAIL ===`);
    Logger.log(`📧 Email: ${email} (type: ${typeof email})`);
    Logger.log(`📊 League: ${league} (type: ${typeof league})`);
    Logger.log(`📊 Waitlist Spot: ${waitlistSpot} (type: ${typeof waitlistSpot})`);
    Logger.log(`👤 First Name: ${firstName} (type: ${typeof firstName})`);
    
    // Use provided first name or fallback to email prefix
    const nameToUse = firstName || email.split('@')[0];
    const capitalizedFirstName = capitalize(nameToUse);
    
    const encodedEmail = encodeURIComponent(email);
    const encodedLeague = encodeURIComponent(league);
    const baseUrl = WAITLIST_WEB_APP_URL;
    Logger.log(`📍 Using web app URL: ${baseUrl}`);
    
    const spotCheckUrl = `${baseUrl}?email=${encodedEmail}&league=${encodedLeague}`;
    
    const barsLogoBlob = UrlFetchApp
      .fetch(BARS_LOGO_URL)
      .getBlob()
      .setName("barsLogo");
    
    const replyToEmail = getLeadershipEmailForLeague(league);
    
    const subject = `🏳️‍🌈 Your Waitlist Spot for Big Apple ${league}`;
    
    const htmlBody = `
      <p>Hi ${capitalizedFirstName},</p>
      <p>You have successfully joined the waitlist for <strong>${league}</strong></p>
      <h3>You are currently <strong><u>#${waitlistSpot}</u></strong> on the waitlist.</h3>
      <p>We'll reach out if a spot opens up!</p>
      <p></p>
      <p>*Please note: The provided waitlist position may not be 100% accurate, depending on unavoidable factors like concurrent submission times (when multiple people join the waitlist very close to one another). We apologize if the number is not exactly as expected, but we promise it is <i>very close</i>.</p>

      <div style="background-color: #e8f5e8; border: 2px solid #4CAF50; border-radius: 10px; padding: 20px; margin: 20px 0; text-align: center;">
        <h3 style="margin: 0 0 15px 0; color: #2e7d32;">🔍 Check Your Waitlist Position</h3>
        <p style="margin: 15px 0; color: #333;">View your position for <strong>${league}</strong> and switch between all your leagues:</p>
        <a href="${spotCheckUrl}" style="display: inline-block; background: #4CAF50; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; margin: 10px 0;">Check Your Current Waitlist Position</a>
      </div>

      <div style="background-color: #ffebee; border: 2px solid #f44336; border-radius: 8px; padding: 15px; margin: 20px 0;">
        <p style="margin: 0; color: #d32f2f; font-weight: bold;">⚠️ <strong>Important Note for Safari Users:</strong></p>
        <p style="margin: 10px 0 0 0; color: #c62828; font-size: 14px;">
          This waitlist checker does not work in Safari due to browser restrictions.
          Please use <strong>Chrome, Firefox, or Edge</strong> for the best experience.
        </p>
      </div>

      ${emailFooterWithLinks}
    `;
    
    MailApp.sendEmail({
      to: email,
      replyTo: replyToEmail,
      subject: subject,
      htmlBody: htmlBody,
      inlineImages: { barsLogo: barsLogoBlob }
    });
    
    Logger.log("✅ Waitlist confirmation email sent successfully");
    return true;
    
  } catch (error) {
    Logger.log(`💥 Error sending waitlist confirmation email: ${error.message}`);
    return false;
  }
}



/**
 * Send email to player pulled off waitlist
 * @param {string} email - Player email
 * @param {string} firstName - Player first name
 * @param {boolean} isMultiplePlayersAdded - Multiple players pulled for one spot
 * @param {string} league - League name
 * @param {string} season - Season
 * @param {string} year - Year
 */
export function sendWaitlistProcessedEmailToPlayer(email, firstName, isMultiplePlayersAdded, league, season, year) {
  Logger.log("📧 Sending email to player...");
  
  const { leadershipEmail, barsProductUrl } = getLeagueInfo(league, season, year);

  Logger.log(`Multiple players? ${typeof isMultiplePlayersAdded}, value: ${isMultiplePlayersAdded}`);
  
  const urgencyText = isMultiplePlayersAdded
    ? `This email was sent to the first 3 people on the waitlist for one available spot (in case anyone has changed their mind). Therefore, please act quickly and don't share this information with anyone else. <br><br>`
    : "";

  const barsLogoBlob = UrlFetchApp
    .fetch(BARS_LOGO_URL)
    .getBlob()
    .setName("barsLogo");
    
  try {
    MailApp.sendEmail({
      to: email,
      cc: leadershipEmail,
      replyTo: leadershipEmail,
      subject: "Big Apple Rec Sports – You're Next On The Waitlist!",
      htmlBody: `Hi ${firstName}! <br><br>

        Congrats, you're next on the waitlist for <b>${league} - ${season}</b> with Big Apple Rec Sports! Please read this email carefully. <br><br>

        To register, please ensure you are signed into our site with the same email address you used to sign up for the waitlist. You <i>must</i> sign in <i>before</i> adding the registration product to your cart, otherwise you will see an error message pop up and not be able to register. <a href="https://shopify.com/55475535966/account">Here is a link straight to the sign in page</a>. After signing in, click <b>Shop</b> near the top of the page, click <b>Registration</b> in the nav bar at the top, and go back to your desired sport/day. <br><br>

        ${urgencyText}

        Please reply to this email, either to let us know 1) you've registered successfully, or 2) you're no longer interested in registering (so we can let the next person off the waitlist.) Thanks!

        ${emailFooterWithLinks}
        `,
      inlineImages: { barsLogo: barsLogoBlob },
    });
    
    Logger.log(`✅ Email sent to ${email}`);
  } catch (e) {
    Logger.log(`❌ Error sending email: ${e.message}`);
    
    const errorLogoBlob = UrlFetchApp
      .fetch(BARS_LOGO_URL)
      .getBlob()
      .setName("barsLogo");
      
    MailApp.sendEmail({
      to: leadershipEmail,
      cc: DEBUG_EMAIL,
      subject: "Error emailing player to notify pulling off waitlist",
      htmlBody: `There was an error emailing player(s) notifying them they have come off the waitlist: \n
        ${e.message}\n\n
        ${e.stack}
        `,
      inlineImages: { barsLogo: errorLogoBlob },
    });
  }
}


/**
 * Send validation error email to admin when product validation fails
 * @param {string} league - League name
 * @param {string} userEmail - User's email address
 * @param {string} reason - Validation failure reason
 * @param {string} productHandle - Constructed product handle
 * @returns {boolean} - True if email sent successfully
 */
export function sendValidationErrorEmailToAdmin(league, userEmail, reason, productHandle) {
  try {
    Logger.log("📧 === SENDING ADMIN VALIDATION ERROR EMAIL ===");
    
    const errorIcon = reason.includes("No product found") ? "🚫" : "📦";
    const title = reason.includes("No product found") ? "Product Not Found" : "Inventory Available";
    const subject = `${errorIcon} Waitlist Validation Error: ${title}`;

    const htmlBody = `
      <div style="font-family: Arial, sans-serif; max-width: 600px;">
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
          <h2 style="color: #dc3545; margin: 0;">${errorIcon} Waitlist Validation Error</h2>
        </div>

        <div style="background: white; padding: 20px; border: 1px solid #dee2e6; border-radius: 8px;">
          <h3 style="color: #495057; margin-top: 0;">Error Details</h3>
          <table style="width: 100%; border-collapse: collapse;">
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Error Type:</td>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">${title}</td>
            </tr>
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">League:</td>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">${league}</td>
            </tr>
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">User Email:</td>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">${userEmail}</td>
            </tr>
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Product Handle:</td>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><code>${productHandle}</code></td>
            </tr>
            <tr>
              <td style="padding: 8px; font-weight: bold;">Timestamp:</td>
              <td style="padding: 8px;">${new Date().toLocaleString()}</td>
            </tr>
          </table>
        </div>

        <div style="background: #e9ecef; padding: 15px; border-radius: 8px; margin-top: 20px;">
          <h4 style="margin: 0 0 10px 0;">Next Steps:</h4>
          <ul style="margin: 0; padding-left: 20px;">
            <li>User has NOT been added to the waitlist</li>
            <li>Row has been marked as "Canceled" in the spreadsheet</li>
          </ul>
        </div>
      </div>
    `;

    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: subject,
      htmlBody: htmlBody
    });

    Logger.log("✅ Admin validation error email sent successfully");
    return true;
  } catch (error) {
    Logger.log(`💥 Error sending admin validation email: ${error.message}`);
    return false;
  }
}
