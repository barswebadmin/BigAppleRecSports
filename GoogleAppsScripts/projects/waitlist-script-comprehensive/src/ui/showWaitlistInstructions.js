export function showWaitlistInstructions() {
    SpreadsheetApp.getUi().alert(
      "To use this workflow:\n\n" +
      "1. Click 'BARS Workflows' in the menu at the top of the page\n" +
      "2. Click 'Pull Someone Off Waitlist'\n" +
      "3. Enter the NUMBER of the row (before column A) and click OK\n\n" +
      "This will:\n" +
      "- Find (or create) the customer by email in Shopify\n" +
      "- Tag them with the product-specific waitlist tag\n" +
      "- Update their phone number\n" +
      "- Give you the option to email them with registration instructions\n\n" +
      "If you decide to email them, it will ask if you pulled multiple people off for one spot. If so, the email will include urgency language."
    );
  }