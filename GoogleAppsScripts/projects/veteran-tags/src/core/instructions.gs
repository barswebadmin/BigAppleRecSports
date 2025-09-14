/**
 * Display instructions for the Add Veteran Tags script
 */
function showInstructions() {
  SpreadsheetApp.getUi().alert(
    "🎖️ BARS Add Veteran Tags & Email Players\n\n" +
    "📋 What this script does:\n" +
    "• Processes veteran registration lists\n" +
    "• Adds veteran tags to customer profiles in Shopify\n" +
    "• Sends automated emails to veteran registrants\n" +
    "• Manages veteran-specific discount codes and perks\n\n" +
    "🚀 How to use:\n" +
    "1. Import veteran registration list into the spreadsheet\n" +
    "2. Ensure email column is properly formatted\n" +
    "3. Click 'Add Veteran Tags' from the menu\n" +
    "4. Select email/confirmation preferences\n\n" +
    "✅ What gets processed:\n" +
    "• Customer lookup by email address\n" +
    "• Addition of veteran-specific tags\n" +
    "• Automated welcome emails to veterans\n" +
    "• Veteran discount code generation\n\n" +
    "🏷️ Tags applied:\n" +
    "• veteran\n" +
    "• veteran-{year}\n" +
    "• military-appreciation\n" +
    "• veteran-perks-eligible\n\n" +
    "📧 Communications:\n" +
    "Veterans receive welcome emails with special perks and discount information"
  );
}
