/**
 * Display instructions for the Process Refunds & Exchanges script
 */
function showInstructions() {
  console.warn("⚠️ PLACEHOLDER INSTRUCTIONS: This project needs proper instructions implementation");

  SpreadsheetApp.getUi().alert(
    "💰 BARS Process Refunds & Exchanges\n\n" +
    "📋 What this script does:\n" +
    "• Processes refund requests from customer forms\n" +
    "• Handles product exchanges and cancellations\n" +
    "• Manages refund calculations and processing\n" +
    "• Integrates with Shopify for order management\n\n" +
    "🚀 How to use:\n" +
    "1. Refund requests are automatically received from web forms\n" +
    "2. Review refund details and customer information\n" +
    "3. Process approved refunds through the system\n" +
    "4. Handle exchanges and partial refunds as needed\n\n" +
    "✅ What gets processed:\n" +
    "• Customer order lookup and validation\n" +
    "• Refund amount calculations based on timing\n" +
    "• Automated refund processing to original payment method\n" +
    "• Inventory restocking for cancelled items\n\n" +
    "💳 Refund Types:\n" +
    "• Full refunds for early cancellations\n" +
    "• Partial refunds with processing fees\n" +
    "• Product exchanges with price adjustments\n" +
    "• Store credit for late requests\n\n" +
    "📊 Tracking:\n" +
    "All refunds and exchanges are logged for financial reporting"
  );
}
