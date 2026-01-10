/**
 * Display instructions for the Product Variant Creation script
 */
function showInstructions() {
  SpreadsheetApp.getUi().alert(
    "🛍️ BARS Product & Variant Creation\n\n" +
    "📋 What this script does:\n" +
    "• Creates Shopify products for new sports seasons\n" +
    "• Sets up registration variants (Veteran, Early, Open, Waitlist)\n" +
    "• Configures pricing, inventory, and scheduling\n" +
    "• Handles product images and sport-specific settings\n\n" +
    "🚀 How to use:\n" +
    "1. Fill out the spreadsheet with season details (sport, dates, pricing, etc.)\n" +
    "2. Mark 'Ready to Create Product?' as TRUE for rows you want to process\n" +
    "3. Click 'Create Products' from the menu\n" +
    "4. Select specific rows or process all ready rows\n\n" +
    "✅ What gets created:\n" +
    "• Shopify product with proper title and description\n" +
    "• Multiple registration variants with different pricing\n" +
    "• Scheduled price changes and inventory moves\n" +
    "• Sport-specific images and settings\n\n" +
    "📝 Required columns:\n" +
    "Sport, Day, Division, Season, Year, Dates, Pricing, Location, Inventory\n\n" +
    "🔧 After creation:\n" +
    "Product URLs and Variant IDs will be automatically filled in"
  );
}



