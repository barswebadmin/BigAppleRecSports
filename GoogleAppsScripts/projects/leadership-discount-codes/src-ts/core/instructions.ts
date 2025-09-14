/**
 * Display instructions for the Leadership Discount Codes script
 * TypeScript version with proper type annotations
 */

/// <reference path="../types/gas-types.ts" />
/// <reference path="../utils/backend.ts" />

/**
 * Shows detailed instructions for using the Leadership Discount Codes script
 * Displays information about functionality, usage, and troubleshooting
 */
function showInstructions(): void {
  const ui: GoogleAppsScript.Base.Ui = SpreadsheetApp.getUi();

  const instructionText: string =
    "🏅 BARS Leadership Discount Codes\n\n" +
    "📋 What this script does:\n" +
    "• Processes leadership email lists from spreadsheets\n" +
    "• Creates customer segments in Shopify for leadership members\n" +
    "• Generates seasonal discount codes (50% off, 100% off x2 per season)\n" +
    "• Uses your backend API for smart email detection and processing\n\n" +
    "🚀 How to use:\n" +
    "1. Open a spreadsheet with leadership member emails\n" +
    "2. Click 'BARS Leadership' menu → 'Process Leadership Discounts (Smart)'\n" +
    "3. The backend will auto-detect email columns and process everything\n" +
    "4. For complex spreadsheets, use 'Process with Custom Header Row'\n\n" +
    "✅ What happens automatically:\n" +
    "• Finds/validates all email addresses\n" +
    "• Creates customer segments tagged with leadership + year\n" +
    "• Generates discount codes for all 4 seasons\n" +
    "• Shows detailed results and any failed emails\n\n" +
    "🔧 Troubleshooting:\n" +
    "Use 'Test Backend Connection' to verify your API is working";

  ui.alert(instructionText);
}
