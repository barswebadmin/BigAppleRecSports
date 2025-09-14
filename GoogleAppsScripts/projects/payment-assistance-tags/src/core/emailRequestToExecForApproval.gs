function emailRequestToExecForApproval({playerDetails, discountDetails, currentUserEmail}) {
  const ui = SpreadsheetApp.getUi();

  const { discountPercentage, season, year, tag } = discountDetails;
  const { fullName, email } = playerDetails;

  const execRecipient = 'executive-board'

  const scriptUrl = "https://script.google.com/a/macros/bigapplerecsports.com/s/AKfycbywEaTZ5tj5d-rfhalRysMGcon6Dv_blhqk2Dq8EKnf0lCIPy20e3oUFuSD7hK8Vuj64A/exec";

  const approvalUrl = `${scriptUrl}?name=${encodeURIComponent(fullName)}&email=${encodeURIComponent(email)}&tag=${encodeURIComponent(tag)}&discount=${encodeURIComponent(discountPercentage)}&season=${encodeURIComponent(season)}&year=${encodeURIComponent(year)}&action=approve&type=discount&senderEmail=${encodeURIComponent(currentUserEmail)}`;
  const denialUrl = `${scriptUrl}?name=${encodeURIComponent(fullName)}&email=${encodeURIComponent(email)}&tag=${encodeURIComponent(tag)}&discount=${encodeURIComponent(discountPercentage)}&season=${encodeURIComponent(season)}&year=${encodeURIComponent(year)}&action=deny&type=discount`;

  const subject = "🚨 Payment Assistance Approval Required";
  const body = `
    <p>A payment assistance request has been submitted through Google Sheets by ${currentUserEmail}.</p>
    <p><b>Player Name:</b> ${playerDetails.fullName}</p>
    <p><b>Player Email:</b> ${playerDetails.email}</p>
    <p><b>Discount Amount:</b> ${discountDetails.discountPercentage}%</p>
    <p><b>Season:</b> ${discountDetails.season} ${discountDetails.year}</p>
    <p><b>Tag to be added:</b> ${discountDetails.tag}</p>
    <p>
      <a href="${approvalUrl}" style="background-color:green;color:white;padding:10px;text-decoration:none;border-radius:5px;">✅ Approve</a>
      <a href="${denialUrl}" style="background-color:red;color:white;padding:10px;text-decoration:none;border-radius:5px;margin-left:10px;">❌ Deny</a>
    </p>
  `;

  MailApp.sendEmail({
    to: `${execRecipient}@bigapplerecsports.com`,
    subject: subject,
    htmlBody: body
  });

  ui.alert(`📧 Approval email sent to ${execRecipient}@bigapplerecsports.com`);
}
