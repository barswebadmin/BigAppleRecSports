function onOpen() {
  const ui = SpreadsheetApp.getUi()

  ui.createMenu("🏳️‍🌈 BARS Workflows")
    .addItem("✅ Pull Someone Off Waitlist", "pullOffWaitlist")
    .addItem("📘 View Instructions", "showWaitlistInstructions")
    .addToUi();

  showWaitlistInstructions();

}

function showWaitlistInstructions() {
  SpreadsheetApp.getUi().alert(
    "To use this workflow:\n\n" +
    "1. Click 'BARS Workflows' in the menu at the top of the page\n" +
    "2. Click 'Pull Someone Off Waitlist'\n" +
    "3. Enter the NUMBER of the row (before column A) and click OK\n\n" +
    "This will find (or create) the customer by email, tag them, and give you the option to email them (you can stop at this point if you want).\n\n" +
    "If you decide to email them, it will ask if you pulled multiple people off for one spot. If so, the email will include urgency language."
  );
    // const html = HtmlService.createHtmlOutput(`
    //   <div style="font-family: Arial, sans-serif;">
    //     <p>To use this workflow:</p>
    //     <ul>
    //       <li style="line-height: 1.5;">Click <b>Workflows</b> in the menu at the top</li>
    //       <li style="line-height: 1.5;">Click <b>Pull someone off waitlist</b></li>
    //       <li style="line-height: 1.5;">Enter the number of the <b>row</b> (far left of the spreadsheet, <i>before</i> column A)</li>
    //     </ul>
    //     <p>
    //       Clicking OK will:
    //       <ul>
    //         <li style="line-height: 1.5;">Look up the Shopify customer by email (or create a new customer, if it can't find that email)</li>
    //         <li style="line-height: 1.5;">Add a <b>waitlist</b> tag to that customer's profile</li>
    //         <li style="line-height: 1.5;">Give you the option to email them with an automated email (as of 7/3/25, it comes from Joe's email. Will update someday) and CCs sport leadership</li>
    //         <li style="line-height: 1.5;">Ask if you pulled multiple people off the waitlist for a single spot (if you click yes, it will add some urgency text that they should act fast)</li>
    //       </ul>
    //     </p>
    //   </div>
    // `).setWidth(500).setHeight(400);

    // SpreadsheetApp.getUi().showModelessDialog(html, 'How to Pull Someone Off the Waitlist');
  }