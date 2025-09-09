/**
 * Display instructions for the Process Refunds & Exchanges script
 */
function showInstructions() {
  SpreadsheetApp.getUi().alert(
    "💰 BARS Refunds & Exchanges Processor\n\n" +
    "📋 What this script does:\n" +
    "• Processes refund and exchange requests from spreadsheets\n" +
    "• Integrates with Shopify to handle order modifications\n" +
    "• Manages customer communications via Slack\n" +
    "• Tracks refund status and updates records\n\n" +
    "🚀 How to use:\n" +
    "1. Fill out refund/exchange request details in the spreadsheet\n" +
    "2. Mark requests as 'Ready to Process'\n" +
    "3. Click 'Process Refunds/Exchanges' from the menu\n" +
    "4. Review and confirm each transaction\n\n" +
    "✅ What gets processed:\n" +
    "• Customer order lookups and validations\n" +
    "• Refund calculations (full, partial, store credit)\n" +
    "• Exchange processing with price differences\n" +
    "• Slack notifications to relevant teams\n\n" +
    "📝 Required information:\n" +
    "Customer email, Order number, Refund amount, Reason, Processing notes\n\n" +
    "🔔 Integrations:\n" +
    "• Shopify API for order management\n" +
    "• Slack for team notifications\n" +
    "• Backend API for processing logic"
  );
}
