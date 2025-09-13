/**
 * Display instructions for the Payment Assistance & Customer Tags script
 */
function showInstructions() {
  SpreadsheetApp.getUi().alert(
    "💳 BARS Payment Assistance & Customer Tags\n\n" +
    "📋 What this script does:\n" +
    "• Processes payment assistance requests and applications\n" +
    "• Adds customer tags for scholarship recipients\n" +
    "• Manages reduced-price registration processing\n" +
    "• Tracks payment assistance usage and eligibility\n\n" +
    "🚀 How to use:\n" +
    "1. Fill out payment assistance details in the spreadsheet\n" +
    "2. Include customer email, assistance type, and amount\n" +
    "3. Click 'Process Payment Assistance' from the menu\n" +
    "4. Review and approve applications\n\n" +
    "✅ What gets processed:\n" +
    "• Customer lookup and validation in Shopify\n" +
    "• Payment assistance tags (scholarship, reduced-price, etc.)\n" +
    "• Discount code generation for approved applicants\n" +
    "• Record keeping for assistance tracking\n\n" +
    "🏷️ Tags applied:\n" +
    "• payment-assistance\n" +
    "• scholarship-recipient\n" +
    "• reduced-price-eligible\n" +
    "• financial-aid\n\n" +
    "📊 Tracking:\n" +
    "All assistance applications and approvals are logged for reporting"
  );
}
