const processDiscountApproval = (params) => {
  requiredParams = []

  if (requiredParams.some(param => !params[param])) {
    return HtmlService.createHtmlOutput("<h3>❌ Invalid Request123</h3>");
  }
    
  const fullName = name
  const email = params.email;
  const tag = params.tag;
  const discount = params.discount;
  const season = params.season;
  const year = params.year;
  const action = params.action;

  let responseMessage;

  if (action === "approve") {
    addTagToCustomerProfile({ playerDetails: {email}, discountDetails });

    var barsLogoUrl = "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/122824_BARS_Logo_Full-Black.png?v=1741951481";
    var barsLogoBlob = UrlFetchApp
                        .fetch(barsLogoUrl)
                        .getBlob()
                        .setName("barsLogo");

    MailApp.sendEmail({
      to: email, 
      replyTo: 'executive-board@bigapplerecsports.com',
      subject: "✅ Payment Assistance Approved!", 
      htmlBody: `Hi ${firstName}, 
      <br> 
      <br> 
      <p>We are very happy to inform you that have been approved for <u>Financial Assistance</u> of ${discountPercentage}% off one registration this <u>${season}</u> season!</p>
      <p>Please use the discount code <b><u>Financial${discountPercentage}Assistance${season}${year.slice(-2)}</u></b> to register for any season - it is not case sensitive.</p>
      
      <p>Please also note: 
      <ul><li>You will need to log in with your BARS account in order to use the code, as it's tied to the email address you provided</li>
      <li>It is only valid for this upcoming season and will expire if not used.</li> 
      </ul>
      Let us know if you have any questions.</p>
      <br>
      Warmly,<br>
      <h3>BARS Leadership</h3>
      <br><img src="cid:barsLogo" style="width:225px; height:auto;">
      `,
      inlineImages: {barsLogo: barsLogoBlob}});
    responseMessage = `<p><h1>✅ Approved!</h1></p>
    <p>Tag \`${tag}\` enabled for <b>${fullName} (${email})</b>, which allows them to use the discount code: <b>Financial${discountPercentage}Assistance${season}${year.slice(-2)}</b> (It is not case sensitive).</p> 
    <p>They have been emailed with details, and the exec-board alias has been CC'd!</p>`;
  } else {
    responseMessage = `<h3>❌ Denied! No tag was added.</h3>`;
  }

  return HtmlService.createHtmlOutput(responseMessage);
}
