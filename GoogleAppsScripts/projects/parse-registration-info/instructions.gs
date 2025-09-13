/**
 * Display instructions for the Parse Registration Info script
 */
function showInstructions() {
  SpreadsheetApp.getUi().alert(
    "📊 BARS Sport Registration Parser\n\n" +
    "📋 What this script does:\n" +
    "• Parses sport registration information from BARS planning spreadsheets\n" +
    "• Converts raw sport data into structured format for Shopify product creation\n" +
    "• Extracts sport details, schedules, pricing, and registration windows\n" +
    "• Migrates parsed data to the Product and Variant Creation sheet\n\n" +
    "🚀 How to use:\n" +
    "1. Put destination season/year in cell A1 (e.g., 'Spring 2025')\n" +
    "2. Fill spreadsheet with sport registration details in columns A-O\n" +
    "3. Click 'Migrate Row to Product Creation Sheet' from menu\n" +
    "4. Select the row number you want to migrate\n\n" +
    "✅ What gets parsed:\n" +
    "• Sport name and day of week (columns A-B)\n" +
    "• Season dates and times (columns D-E, G)\n" +
    "• Pricing and location information (columns F, H)\n" +
    "• Registration windows (Veteran, Early, Open - columns M-O)\n" +
    "• League details, divisions, and special notes (column C)\n\n" +
    "📋 Required format:\n" +
    "A: Sport | B: Day/Division | C: Notes | D: Start Date | E: End Date\n" +
    "F: Price | G: Times | H: Location | M-O: Registration Windows\n\n" +
    "📈 Output:\n" +
    "Structured data ready for Shopify product creation with all variants"
  );
}
