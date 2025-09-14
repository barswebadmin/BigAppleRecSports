/**
 * BARS Leadership Discount Processing
 * Main script for processing leadership discount codes via backend API
 * Uses smart CSV processing with automatic email column detection
 */

/**
 * Add custom menu to Google Sheets
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();

  ui.createMenu("BARS Leadership")
    .addItem("🚀 Process Leadership Discounts (Smart)", "processLeadershipDiscountsSmartCSV")
    .addItem("📊 Process with Custom Header Row", "processLeadershipDiscountsWithHeaderPrompt")
    .addSeparator()
    .addItem("🧪 Test Backend Connection", "testBackendConnection")
    .addItem("ℹ️ Show Backend Info", "showBackendInfo")
    .addSeparator()
    .addItem("📘 View Instructions", "showInstructions")
    .addToUi();

  // Show instructions on first open
  showInstructions();
}

/**
 * MAIN FUNCTION - Smart CSV processing (recommended)
 * Automatically detects email columns and processes the entire sheet
 */
function processLeadershipDiscountsSmartCSV() {
  try {
    Logger.log("🚀 Starting smart CSV leadership processing...");

    const sheet = SpreadsheetApp.getActiveSheet();
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const spreadsheetTitle = spreadsheet.getName();

    Logger.log(`📊 Processing spreadsheet: ${spreadsheetTitle}`);

    // Get all data from the sheet (let backend handle email detection)
    const range = sheet.getDataRange();
    const csvData = range.getValues();

    Logger.log(`📋 Found ${csvData.length} rows of data`);

    if (csvData.length < 2) {
      SpreadsheetApp.getUi().alert("❌ Error", "Spreadsheet must have at least a header row and one data row.", SpreadsheetApp.getUi().ButtonSet.OK);
      return;
    }

    // Show loading message
    SpreadsheetApp.getUi().alert("Processing", "🔄 Sending data to backend for smart processing...\n\nThe backend will:\n• Auto-detect email columns\n• Validate all emails\n• Create customer segments\n• Generate discount codes", SpreadsheetApp.getUi().ButtonSet.OK);

    // Send to backend using new CSV endpoint
    const result = sendCSVToBackend(csvData, spreadsheetTitle);

    // Display results (now handled by backend)
    SpreadsheetApp.getUi().alert("BARS Leadership Processing Results", result.display_text, SpreadsheetApp.getUi().ButtonSet.OK);

  } catch (error) {
    console.error("❌ Error in processLeadershipDiscountsSmartCSV:", error);
    SpreadsheetApp.getUi().alert("❌ Error", `Failed to process leadership discounts: ${error.message}`, SpreadsheetApp.getUi().ButtonSet.OK);
  }
}

/**
 * ALTERNATIVE FUNCTION - With header row prompt (for complex spreadsheets)
 * Prompts user to specify which row contains headers, then processes from there
 */
function processLeadershipDiscountsWithHeaderPrompt() {
  try {
    Logger.log("🚀 Starting leadership processing with header prompt...");

    const sheet = SpreadsheetApp.getActiveSheet();
    const ui = SpreadsheetApp.getUi();
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const spreadsheetTitle = spreadsheet.getName();

    // Prompt for header row
    const userSelection = ui.prompt(
      "📍 Header Row Location",
      "Please enter the row number where the first instance of the column header \"PERSONAL EMAIL\" is located.",
      ui.ButtonSet.OK_CANCEL
    );

    if (userSelection.getSelectedButton() !== ui.Button.OK) {
      Logger.log("User cancelled header row selection");
      return;
    }

    const headerRowInput = userSelection.getResponseText().trim();
    const headerRow = parseInt(headerRowInput);

    if (isNaN(headerRow) || headerRow < 1 || headerRow > sheet.getLastRow()) {
      ui.alert("❌ Invalid Input", `Please enter a valid row number between 1 and ${sheet.getLastRow()}`, ui.ButtonSet.OK);
      return;
    }

    Logger.log(`📍 Using header row: ${headerRow}`);

    // Get data starting from the specified header row
    const dataRange = sheet.getRange(headerRow, 1, sheet.getLastRow() - headerRow + 1, sheet.getLastColumn());
    const csvData = dataRange.getValues();

    Logger.log(`📋 Extracted ${csvData.length} rows starting from row ${headerRow}`);

    if (csvData.length < 2) {
      ui.alert("❌ Error", "Not enough data found. Need at least a header row and one data row.", ui.ButtonSet.OK);
      return;
    }

    const previewMessage = `📊 Data Preview:\n\n` +
      `• Header row: ${headerRow}\n` +
      `• Total rows: ${csvData.length}\n` +
      `• Data rows: ${csvData.length - 1}\n` +
      `Continue processing?`;

    const confirmResult = ui.alert("📋 Confirm Processing", previewMessage, ui.ButtonSet.YES_NO);

    if (confirmResult !== ui.Button.YES) {
      Logger.log("User cancelled processing confirmation");
      return;
    }

    // Send to backend
    const result = sendCSVToBackend(csvData, spreadsheetTitle, headerRow);

    // Display results (now handled by backend)
    ui.alert("BARS Leadership Processing Results", result.display_text, ui.ButtonSet.OK);

  } catch (error) {
    console.error("❌ Error in processLeadershipDiscountsWithHeaderPrompt:", error);
    SpreadsheetApp.getUi().alert("❌ Error", `Failed to process leadership discounts: ${error.message}`, SpreadsheetApp.getUi().ButtonSet.OK);
  }
}

/**
 * Send CSV data to backend for processing
 */
function sendCSVToBackend(csvData, spreadsheetTitle, headerRow = null) {
  try {
    Logger.log("📤 Sending CSV data to backend...");

    const payload = {
      csv_data: csvData,
      spreadsheet_title: spreadsheetTitle
    };

    if (headerRow) {
      payload.header_row = headerRow;
    }

    const options = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true"
      },
      payload: JSON.stringify(payload)
    };

    const backendUrl = getBackendUrl();
    Logger.log(`🌐 Calling: ${backendUrl}/leadership/addTags`);
    const response = UrlFetchApp.fetch(`${backendUrl}/leadership/addTags`, options);

    if (response.getResponseCode() !== 200) {
      throw new Error(`Backend returned status ${response.getResponseCode()}: ${response.getContentText()}`);
    }

    const result = JSON.parse(response.getContentText());
    Logger.log("✅ Backend processing completed successfully");

    return result;

  } catch (error) {
    console.error("❌ Error sending to backend:", error);
    throw new Error(`Failed to communicate with backend: ${error.message}`);
  }
}

/**
 * Test backend connection
 */
function testBackendConnection(shouldShowConfirmation=true) {
  try {
    Logger.log("🧪 Testing backend connection...");

    const options = {
      method: "GET",
      headers: {
        "ngrok-skip-browser-warning": "true"
      }
    };

    const backendUrl = getBackendUrl();
    const response = UrlFetchApp.fetch(`${backendUrl}/leadership/health`, options);

    if (response.getResponseCode() === 200) {
      const result = JSON.parse(response.getContentText());
      Logger.log("✅ Backend connection successful:", result);

      if (shouldShowConfirmation === true) {
        SpreadsheetApp.getUi().alert(
          "✅ Connection Test Successful!",
          `Connected to backend successfully!\n\n🌐 URL: ${backendUrl}\n📊 Status: ${result.status}\n🔧 Service: ${result.service}\n\n🎯 Ready to process leadership data!`,
          SpreadsheetApp.getUi().ButtonSet.OK
        );
      }
    } else {
      throw new Error(`Backend returned status ${response.getResponseCode()}`);
    }

  } catch (error) {
    console.error("❌ Backend connection failed:", error);

    SpreadsheetApp.getUi().alert(
      "❌ Connection Test Failed",
      `Could not connect to backend:\n\n❌ ${error.message}\n\n🌐 URL: ${getBackendUrl()}\n\n🔧 Troubleshooting:\n1. Make sure your local server is running\n2. Check that ngrok tunnel is active\n3. Update the backend URL in secrets if needed\n4. Verify the backend is accessible`,
      SpreadsheetApp.getUi().ButtonSet.OK
    );
  }
}

/**
 * Show backend information
 */
function showBackendInfo() {
  const backendUrl = getBackendUrl();

  SpreadsheetApp.getUi().alert(
    "🌐 Backend Information",
    `Current Backend URL:\n${backendUrl}\n\n🔗 Available Endpoints:\n• Health Check: /leadership/health\n• Add Tags (CSV Processing): /leadership/addTags\n• Legacy Email List: /leadership/addToLeadership\n• API Documentation: /docs\n\n🚀 This script uses the addTags endpoint with backend-generated display text for maximum flexibility and performance.`,
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

/**
 * Legacy function for backward compatibility
 * (Redirects to smart CSV processing)
 */
function processLeadershipDiscounts() {
  SpreadsheetApp.getUi().alert(
    "🔄 Redirecting to New Method",
    "The legacy processing method has been upgraded!\n\nYou'll now use the new smart CSV processing which:\n• Auto-detects email columns\n• Handles complex spreadsheet formats\n• Provides detailed processing reports\n• Uses optimized backend processing\n\nClick OK to continue with the new method.",
    SpreadsheetApp.getUi().ButtonSet.OK
  );

  processLeadershipDiscountsSmartCSV();
}
