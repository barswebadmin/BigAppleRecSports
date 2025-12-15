// ✅ **Send Emails in batches of <50 with All Veterans in BCC**
function sendVeteranEmail(veteransList, sport, day, division, season, year, leadershipEmailAddress) {
  const subject = `Big Apple ${sport} - Veteran Eligibility for: ${season} ${year} - ${day} - ${division} Division`;

  const barsLogoUrl = "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/122824_BARS_Logo_Full-Black.png?v=1741951481";
  const barsLogoBlob = UrlFetchApp
                      .fetch(barsLogoUrl)
                      .getBlob()
                      .setName("barsLogo");

  const batchSize = 45;

  for (let i = 0; i < veteransList.length; i += batchSize) {
    const bccChunk = veteransList.slice(i, i + batchSize);
    const uniqueBcc = [...new Set(bccChunk.map(playerEmail => playerEmail.trim().toLowerCase()))].join(",");
    const isLastBatch = i + batchSize >= veteransList.length;

    const body = `<p>Hello!</p>
      <p>You are receiving this email because you met the attendance requirements to register as a veteran for the <b>${season} ${year} season of ${sport} - ${day} - ${division} Division</b>. In order to register during the veteran registration window, you <i>must</i> <a href='https://shopify.com/55475535966/account?locale=en&region_country=US' target='_blank'>Sign In to the BARS website</a> using this email address (you will typically get a code emailed or texted to you and use that to validate your sign in) - if you don't, you will not be able to add the Registration product to your cart. (If you haven't before, we recommend signing in <i>before</i> your registration period starts in case you have any trouble; we may not be able to help right at registration time.)</p>

      <p>Please note that veteran status does not guarantee your registration - you must register successfully during the Veteran Registration window in order to secure your spot.</p>
      
      <p>If you have any questions, please reach out to <a style='color:blue' href='mailto:${leadershipEmailAddress}'>${leadershipEmailAddress}</a></p>
      
      --<br>
      <p>Warmly,<br>
      <b>BARS Leadership</b></p>
      <img src="cid:barsLogo" style="width:225px; height:auto;">
    `;

    const emailOptions = {
      subject,
      to: 'undisclosed-recipients:;',
      bcc: uniqueBcc,
      htmlBody: body,
      inlineImages: { barsLogo: barsLogoBlob },
      replyTo: leadershipEmailAddress,
      name: "BARS Web Admin" 
    };

    if (isLastBatch) {
      emailOptions.cc = leadershipEmailAddress;
    }

    Logger.log(`📤 Sending batch ${i / batchSize + 1} with ${bccChunk.length} recipients`);

    try {
      MailApp.sendEmail(emailOptions);
    } catch (error) {
      Logger.log(`❌ Error sending veteran email batch: ${error.message}`);
    }
  }
}
