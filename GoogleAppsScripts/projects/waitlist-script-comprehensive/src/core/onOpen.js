/**
 * Spreadsheet Menu and Triggers
 * Creates custom menu when spreadsheet opens
 */

import { showWaitlistInstructions } from '../ui/showWaitlistInstructions';

// biome-ignore lint/correctness/noUnusedVariables: GAS runtime trigger function
function onOpen() {
  const ui = SpreadsheetApp.getUi();

  ui.createMenu("🏳️‍🌈 BARS Workflows")
    .addItem("✅ Pull Someone Off Waitlist", "pullOffWaitlist")
    .addItem("📘 View Instructions", "showWaitlistInstructions")
    .addToUi();

  showWaitlistInstructions();
}


