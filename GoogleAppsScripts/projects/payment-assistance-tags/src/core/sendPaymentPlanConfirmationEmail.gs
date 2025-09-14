function sendPaymentPlanConfirmationEmail({ playerDetails, planDetails, repaymentDetails }) {

  const { year, season, sport, dayOfPlay, numOfPayments, code, tag, type } = planDetails
  const repaymentList = repaymentDetails.map(item => `<li>${item}</li>`).join("");
  const repaymentHtml = `<ul>${repaymentList}</ul>`;

  var barsLogoUrl = "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/122824_BARS_Logo_Full-Black.png?v=1741951481";
  var barsLogoBlob = UrlFetchApp
                      .fetch(barsLogoUrl)
                      .getBlob()
                      .setName("barsLogo.png");
  try {
    MailApp.sendEmail({
      to: `${playerDetails.email}`,
      cc: 'executive-board@bigapplerecsports.com',
      noReply:true,
      subject: `✅ Big Apple ${dayOfPlay} ${sport} - ${season} ${year} - Payment Plan Confirmed`,
      htmlBody: `Hi ${playerDetails.firstName},<br><br>
        <p>You have been set up with a <u>Payment Plan - for ${numOfPayments} payments</u>. When your applicable registration period begins, please use the Discount Code: <br>
        <h2>${code}</h2>
        to register for a season at $0 up front. The code is not case sensitive.</p>

        <p>Your repayment schedule is:
          ${repaymentHtml}
          We will be in touch in the coming weeks with instructions on how to pay at that time. You may use the code for any sport, but of course, different sports will carry different repayment amounts, so the amounts above are subject to change.</p>

        <p><b>Notes:</b>
        <ul>
            ${playerDetails.newOrReturning === 'new' ? '<li><b>You have been set up with an account on our website. Please use your email to sign in, and update your personal details accordingly.</b></li>' : ''}
            <li>You will need to be <a href='https://www.bigapplerecsports.com/customer_authentication/redirect?locale=en&region_country=US' target='_blank'>signed in to the BARS site</a> in order to use the code, as it's tied to the email address you provided.</li>
            <li>Sign in is typically done with a code sent to your email, so you shouldn't need a password.</li>
            <li>Lastly, <i>please note that using this discount code to register for a payment plan signifies your commitment to repay according to the schedule above</i>. <b>Please reach out to us in advance</b> if you anticipate any difficulty making payment(s) or need an extension, because failure to make scheduled payments may impact your ability to register for future season(s).</li>
          </ul>
            Please email <a href="mailto:executive-board@bigapplerecsports.com">executive-board@bigapplerecsports.com</a> if you have any questions. We look forward to seeing you this ${capitalize(season)} season!</p>
        Warmly,
        <br>
        <h3>BARS Leadership</h3>
        <img src="cid:barsLogo" style="width:225px; height:auto;">
      `,
      inlineImages: {"barsLogo": barsLogoBlob}
    });
    return {
      success: true,
      message: `✅ Processed successfully: ${playerDetails.fullName} (${playerDetails.email}) has been provided with a ${planDetails.type}, which allows them to use the discount code: \n
      *${planDetails.code}* \n
      They have been emailed with details, and the executive-board@ alias has been CC'd`
    }
  } catch {
    return {
      success: false,
      message: `Email could not be sent to ${playerDetails.email}. Please check details and try again!`
    }
  }
}

function sendDenialEmail(firstName, email) {
  var barsLogoUrl = "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/122824_BARS_Logo_Full-Black.png?v=1741951481";
  var barsLogoBlob = UrlFetchApp
                      .fetch(barsLogoUrl)
                      .getBlob()
                      .setName("barsLogo.png");
  try {
    MailApp.sendEmail({
      to: email,
      noReply:true,
      cc: 'executive-board@bigapplerecsports.com',
      subject: `❌ Payment Plan Request Denied`,
      htmlBody: `Hi ${firstName},\n\nSorry, but we were not able to approve you for a payment plan at this time. Please reach out to <a href="mailto:executive-board@bigapplerecsports.com">executive-board@bigapplerecsports.com</a> with any questions.\n\n
      Sincerely,
        <br>
        <h3>BARS Leadership</h3>
        <img src="cid:barsLogo" style="width:225px; height:auto;">
      `,
      inlineImages: {"barsLogo": barsLogoBlob}
    });

    return {
      success: true,
      message: `❌ Denied payment plan for ${firstName} (${email}). Email sent.`
    };
  } catch (error) {
    Logger.log(`❌ Error sending denial email: ${error.message}`);
    return {
      success: false,
      message: `⚠️ Failed to send denial email to ${email}.`
    };
  }
}
