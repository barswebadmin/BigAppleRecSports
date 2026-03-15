/**
 * Display instructions for the Parse Registration Info script
 */
export function showInstructions() {
  SpreadsheetApp.getUi().alert(
    "📊 BARS Sport Registration Parser\n\n" +
    "📋 What this script does:\n" +
    "• Parses sport registration information from BARS planning spreadsheets\n" +
    "• Creates Shopify products directly from parsed data\n" +
    "• Extracts sport details, schedules, pricing, and registration windows\n" +
    "• Automatically writes product URLs and variant IDs back to the sheet\n\n" +
    "🚀 How to use:\n" +
    "1. Fill spreadsheet with sport registration details in columns A-O\n" +
    "2. Click '🛍️ Create Shopify Product' from the menu\n" +
    "3. Select the row number you want to create a product from\n" +
    "4. Review and edit the parsed data if needed\n" +
    "5. Click 'create' to send the product to Shopify\n" +
    "6. Check the product URL in column Q for accuracy\n" +
    "7. Check the box in column P to schedule the product to go live\n\n" +
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
    "• Q: Product URL\n" +
    "• R: Veteran Variant ID\n" +
    "• S: Early Variant ID\n" +
    "• T: Open Variant ID\n" +
    "• U: Waitlist Variant ID (if applicable)\n" +
    "• P: Checkbox to schedule go-live"
  );
}
