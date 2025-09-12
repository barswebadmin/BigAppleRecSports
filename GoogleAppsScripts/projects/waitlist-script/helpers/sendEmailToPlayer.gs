

const sendEmailToPlayer = (email, firstName, isMultiplePlayersAdded, league, season, year) => {
  Logger.log("sending email")
  const {leadershipEmail, barsProductUrl} = getLeagueInfo(league, season, year)

  Logger.log(`multiple? type: ${typeof isMultiplePlayersAdded}, value: ${isMultiplePlayersAdded}`)
  const urgencyText = isMultiplePlayersAdded
    ? `This email was sent to the first 3 people on the waitlist for one available spot (in case anyone has changed their mind). Therefore, please act quickly and don't share this information with anyone else. <br><br>`
    : "";

  const barsLogoUrl = "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/122824_BARS_Logo_Full-Black.png?v=1741951481";
  const barsLogoBlob = UrlFetchApp
                      .fetch(barsLogoUrl)
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
        
        --<br>
          <p>Warmly,<br>
          <b>BARS Leadership</b>
          </p>
          <img src="cid:barsLogo" style="width:225px; height:auto;">
        `,
      inlineImages: { barsLogo: barsLogoBlob },
    })
    Logger.log(`📧 Email sent to ${email}`);
  } catch(e) {
    MailApp.sendEmail({
      to: leadershipEmail,
      cc: DEBUG_EMAIL,
      subject: "Error emailing player to notify pulling off waitlist",
      htmlBody: `There was an error emailing player(s) notifying them they have come off the waitlist: \n
        ${e.stack.trace}
        `,
      inlineImages: { barsLogo: barsLogoBlob },
    })
  }
}