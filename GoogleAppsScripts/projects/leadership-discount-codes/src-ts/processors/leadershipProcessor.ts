/**
 * BARS Leadership Discount Processing
 * Main script for processing leadership discount codes via backend API
 * Uses smart CSV processing with automatic email column detection
 * TypeScript version with comprehensive type safety
 */

/// <reference path="../types/gas-types.ts" />
/// <reference path="../utils/backend.ts" />

/**
 * Add custom menu to Google Sheets
 * Creates the BARS Leadership menu with all available functions
 */
function onOpen(): void {
  const ui: GoogleAppsScript.Base.Ui = SpreadsheetApp.getUi();

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
function processLeadershipDiscountsSmartCSV(): void {
  try {
    Logger.log("🚀 Starting smart CSV leadership processing...");

    const sheet: GoogleAppsScript.Spreadsheet.Sheet = SpreadsheetApp.getActiveSheet();
    const spreadsheet: GoogleAppsScript.Spreadsheet.Spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const spreadsheetTitle: string = spreadsheet.getName();

    Logger.log(`📊 Processing spreadsheet: ${spreadsheetTitle}`);

    // Get all data from the sheet (let backend handle email detection)
    const range: GoogleAppsScript.Spreadsheet.Range = sheet.getDataRange();
    const csvData: any[][] = range.getValues();

    Logger.log(`📋 Found ${csvData.length} rows of data`);

    if (csvData.length < 2) {
      const ui: GoogleAppsScript.Base.Ui = SpreadsheetApp.getUi();
      ui.alert(
        "❌ Error",
        "Spreadsheet must have at least a header row and one data row.",
        ui.ButtonSet.OK
      );
      return;
    }

    // Show loading message
    const ui: GoogleAppsScript.Base.Ui = SpreadsheetApp.getUi();
    ui.alert(
      "Processing",
      "🔄 Sending data to backend for smart processing...\n\n" +
      "The backend will:\n" +
      "• Auto-detect email columns\n" +
      "• Validate all emails\n" +
      "• Create customer segments\n" +
      "• Generate discount codes",
      ui.ButtonSet.OK
    );

    // Send to backend using new CSV endpoint
    const result: BackendResponse = sendCSVToBackend(csvData, spreadsheetTitle);

    // Display results (now handled by backend)
    ui.alert(
      "BARS Leadership Processing Results",
      result.display_text,
      ui.ButtonSet.OK
    );

  } catch (error: any) {
    console.error("❌ Error in processLeadershipDiscountsSmartCSV:", error);
    const ui: GoogleAppsScript.Base.Ui = SpreadsheetApp.getUi();
    ui.alert(
      "❌ Error",
      `Failed to process leadership discounts: ${error.message}`,
      ui.ButtonSet.OK
    );
  }
}

/**
 * ALTERNATIVE FUNCTION - With header row prompt (for complex spreadsheets)
 * Prompts user to specify which row contains headers, then processes from there
 */
function processLeadershipDiscountsWithHeaderPrompt(): void {
  try {
    Logger.log("🚀 Starting leadership processing with header prompt...");

    const sheet: GoogleAppsScript.Spreadsheet.Sheet = SpreadsheetApp.getActiveSheet();
    const ui: GoogleAppsScript.Base.Ui = SpreadsheetApp.getUi();
    const spreadsheet: GoogleAppsScript.Spreadsheet.Spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const spreadsheetTitle: string = spreadsheet.getName();

    // Prompt for header row
    const userSelection: GoogleAppsScript.Base.PromptResponse = ui.prompt(
      "📍 Header Row Location",
      "Please enter the row number where the first instance of the column header \"PERSONAL EMAIL\" is located.",
      ui.ButtonSet.OK_CANCEL
    );

    if (userSelection.getSelectedButton() !== ui.Button.OK) {
      Logger.log("User cancelled header row selection");
      return;
    }

    const headerRowInput: string = userSelection.getResponseText().trim();
    const headerRow: number = parseInt(headerRowInput, 10);

    if (isNaN(headerRow) || headerRow < 1 || headerRow > sheet.getLastRow()) {
      ui.alert(
        "❌ Invalid Input",
        `Please enter a valid row number between 1 and ${sheet.getLastRow()}`,
        ui.ButtonSet.OK
      );
      return;
    }

    Logger.log(`📍 Using header row: ${headerRow}`);

    // Get data starting from the specified header row
    const dataRange: GoogleAppsScript.Spreadsheet.Range = sheet.getRange(
      headerRow,
      1,
      sheet.getLastRow() - headerRow + 1,
      sheet.getLastColumn()
    );
    const csvData: any[][] = dataRange.getValues();

    Logger.log(`📋 Extracted ${csvData.length} rows starting from row ${headerRow}`);

    if (csvData.length < 2) {
      ui.alert(
        "❌ Error",
        "Not enough data found. Need at least a header row and one data row.",
        ui.ButtonSet.OK
      );
      return;
    }

    const previewMessage: string = `📊 Data Preview:\n\n` +
      `• Header row: ${headerRow}\n` +
      `• Total rows: ${csvData.length}\n` +
      `• Data rows: ${csvData.length - 1}\n` +
      `Continue processing?`;

    const confirmResult: GoogleAppsScript.Base.Button = ui.alert(
      "📋 Confirm Processing",
      previewMessage,
      ui.ButtonSet.YES_NO
    );

    if (confirmResult !== ui.Button.YES) {
      Logger.log("User cancelled processing confirmation");
      return;
    }

    // Send to backend
    const result: BackendResponse = sendCSVToBackend(csvData, spreadsheetTitle, headerRow);

    // Display results (now handled by backend)
    ui.alert(
      "BARS Leadership Processing Results",
      result.display_text,
      ui.ButtonSet.OK
    );

  } catch (error: any) {
    console.error("❌ Error in processLeadershipDiscountsWithHeaderPrompt:", error);
    const ui: GoogleAppsScript.Base.Ui = SpreadsheetApp.getUi();
    ui.alert(
      "❌ Error",
      `Failed to process leadership discounts: ${error.message}`,
      ui.ButtonSet.OK
    );
  }
}

/**
 * Send CSV data to backend for processing
 * @param csvData - 2D array of spreadsheet data
 * @param spreadsheetTitle - Name of the spreadsheet
 * @param headerRow - Optional header row number
 * @returns Backend response with processing results
 */
function sendCSVToBackend(
  csvData: any[][],
  spreadsheetTitle: string,
  headerRow?: number
): BackendResponse {
  try {
    Logger.log("📤 Sending CSV data to backend...");

    const payload: LeadershipPayload = {
      csv_data: csvData,
      spreadsheet_title: spreadsheetTitle
    };

    if (headerRow !== undefined) {
      payload.header_row = headerRow;
    }

    const options: GoogleAppsScript.URL_Fetch.URLFetchRequestOptions = {
      method: "post",
      headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true"
      },
      payload: JSON.stringify(payload)
    };

    const backendUrl: string = getBackendUrl();
    Logger.log(`🌐 Calling: ${backendUrl}/leadership/addTags`);

    const response: GoogleAppsScript.URL_Fetch.HTTPResponse = UrlFetchApp.fetch(
      `${backendUrl}/leadership/addTags`,
      options
    );

    if (response.getResponseCode() !== 200) {
      throw new Error(
        `Backend returned status ${response.getResponseCode()}: ${response.getContentText()}`
      );
    }

    const result: BackendResponse = JSON.parse(response.getContentText());
    Logger.log("✅ Backend processing completed successfully");

    return result;

  } catch (error: any) {
    console.error("❌ Error sending to backend:", error);
    throw new Error(`Failed to communicate with backend: ${error.message}`);
  }
}

/**
 * Test backend connection
 * @param shouldShowConfirmation - Whether to show success dialog (default: true)
 */
function testBackendConnection(shouldShowConfirmation: boolean = true): void {
  try {
    Logger.log("🧪 Testing backend connection...");

    const options: GoogleAppsScript.URL_Fetch.URLFetchRequestOptions = {
      method: "get",
      headers: {
        "ngrok-skip-browser-warning": "true"
      }
    };

    const backendUrl: string = getBackendUrl();
    const response: GoogleAppsScript.URL_Fetch.HTTPResponse = UrlFetchApp.fetch(
      `${backendUrl}/leadership/health`,
      options
    );

    if (response.getResponseCode() === 200) {
      const result: HealthCheckResponse = JSON.parse(response.getContentText());
      Logger.log("✅ Backend connection successful:", result);

      if (shouldShowConfirmation === true) {
        const ui: GoogleAppsScript.Base.Ui = SpreadsheetApp.getUi();
        ui.alert(
          "✅ Connection Test Successful!",
          `Connected to backend successfully!\n\n` +
          `🌐 URL: ${backendUrl}\n` +
          `📊 Status: ${result.status}\n` +
          `🔧 Service: ${result.service}\n\n` +
          `🎯 Ready to process leadership data!`,
          ui.ButtonSet.OK
        );
      }
    } else {
      throw new Error(`Backend returned status ${response.getResponseCode()}`);
    }

  } catch (error: any) {
    console.error("❌ Backend connection failed:", error);

    const ui: GoogleAppsScript.Base.Ui = SpreadsheetApp.getUi();
    ui.alert(
      "❌ Connection Test Failed",
      `Could not connect to backend:\n\n` +
      `❌ ${error.message}\n\n` +
      `🌐 URL: ${getBackendUrl()}\n\n` +
      `🔧 Troubleshooting:\n` +
      `1. Make sure your local server is running\n` +
      `2. Check that ngrok tunnel is active\n` +
      `3. Update the backend URL in secrets if needed\n` +
      `4. Verify the backend is accessible`,
      ui.ButtonSet.OK
    );
  }
}

/**
 * Show backend information
 * Displays current backend URL and available endpoints
 */
function showBackendInfo(): void {
  const backendUrl: string = getBackendUrl();
  const ui: GoogleAppsScript.Base.Ui = SpreadsheetApp.getUi();

  ui.alert(
    "🌐 Backend Information",
    `Current Backend URL:\n${backendUrl}\n\n` +
    `🔗 Available Endpoints:\n` +
    `• Health Check: /leadership/health\n` +
    `• Add Tags (CSV Processing): /leadership/addTags\n` +
    `• Legacy Email List: /leadership/addToLeadership\n` +
    `• API Documentation: /docs\n\n` +
    `🚀 This script uses the addTags endpoint with backend-generated ` +
    `display text for maximum flexibility and performance.`,
    ui.ButtonSet.OK
  );
}

/**
 * Legacy function for backward compatibility
 * Redirects to smart CSV processing with explanation
 */
function processLeadershipDiscounts(): void {
  const ui: GoogleAppsScript.Base.Ui = SpreadsheetApp.getUi();

  ui.alert(
    "🔄 Redirecting to New Method",
    "The legacy processing method has been upgraded!\n\n" +
    "You'll now use the new smart CSV processing which:\n" +
    "• Auto-detects email columns\n" +
    "• Handles complex spreadsheet formats\n" +
    "• Provides detailed processing reports\n" +
    "• Uses optimized backend processing\n\n" +
    "Click OK to continue with the new method.",
    ui.ButtonSet.OK
  );

  processLeadershipDiscountsSmartCSV();
}
