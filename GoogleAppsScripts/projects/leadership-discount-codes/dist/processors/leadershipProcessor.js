"use strict";
function onOpen() {
    var ui = SpreadsheetApp.getUi();
    ui.createMenu("BARS Leadership")
        .addItem("🚀 Process Leadership Discounts (Smart)", "processLeadershipDiscountsSmartCSV")
        .addItem("📊 Process with Custom Header Row", "processLeadershipDiscountsWithHeaderPrompt")
        .addSeparator()
        .addItem("🧪 Test Backend Connection", "testBackendConnection")
        .addItem("ℹ️ Show Backend Info", "showBackendInfo")
        .addSeparator()
        .addItem("📘 View Instructions", "showInstructions")
        .addToUi();
    showInstructions();
}
function processLeadershipDiscountsSmartCSV() {
    try {
        Logger.log("🚀 Starting smart CSV leadership processing...");
        var sheet = SpreadsheetApp.getActiveSheet();
        var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
        var spreadsheetTitle = spreadsheet.getName();
        Logger.log("\uD83D\uDCCA Processing spreadsheet: ".concat(spreadsheetTitle));
        var range = sheet.getDataRange();
        var csvData = range.getValues();
        Logger.log("\uD83D\uDCCB Found ".concat(csvData.length, " rows of data"));
        if (csvData.length < 2) {
            var ui_1 = SpreadsheetApp.getUi();
            ui_1.alert("❌ Error", "Spreadsheet must have at least a header row and one data row.", ui_1.ButtonSet.OK);
            return;
        }
        var ui = SpreadsheetApp.getUi();
        ui.alert("Processing", "🔄 Sending data to backend for smart processing...\n\n" +
            "The backend will:\n" +
            "• Auto-detect email columns\n" +
            "• Validate all emails\n" +
            "• Create customer segments\n" +
            "• Generate discount codes", ui.ButtonSet.OK);
        var result = sendCSVToBackend(csvData, spreadsheetTitle);
        ui.alert("BARS Leadership Processing Results", result.display_text, ui.ButtonSet.OK);
    }
    catch (error) {
        console.error("❌ Error in processLeadershipDiscountsSmartCSV:", error);
        var ui = SpreadsheetApp.getUi();
        ui.alert("❌ Error", "Failed to process leadership discounts: ".concat(error.message), ui.ButtonSet.OK);
    }
}
function processLeadershipDiscountsWithHeaderPrompt() {
    try {
        Logger.log("🚀 Starting leadership processing with header prompt...");
        var sheet = SpreadsheetApp.getActiveSheet();
        var ui = SpreadsheetApp.getUi();
        var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
        var spreadsheetTitle = spreadsheet.getName();
        var userSelection = ui.prompt("📍 Header Row Location", "Please enter the row number where the first instance of the column header \"PERSONAL EMAIL\" is located.", ui.ButtonSet.OK_CANCEL);
        if (userSelection.getSelectedButton() !== ui.Button.OK) {
            Logger.log("User cancelled header row selection");
            return;
        }
        var headerRowInput = userSelection.getResponseText().trim();
        var headerRow = parseInt(headerRowInput, 10);
        if (isNaN(headerRow) || headerRow < 1 || headerRow > sheet.getLastRow()) {
            ui.alert("❌ Invalid Input", "Please enter a valid row number between 1 and ".concat(sheet.getLastRow()), ui.ButtonSet.OK);
            return;
        }
        Logger.log("\uD83D\uDCCD Using header row: ".concat(headerRow));
        var dataRange = sheet.getRange(headerRow, 1, sheet.getLastRow() - headerRow + 1, sheet.getLastColumn());
        var csvData = dataRange.getValues();
        Logger.log("\uD83D\uDCCB Extracted ".concat(csvData.length, " rows starting from row ").concat(headerRow));
        if (csvData.length < 2) {
            ui.alert("❌ Error", "Not enough data found. Need at least a header row and one data row.", ui.ButtonSet.OK);
            return;
        }
        var previewMessage = "\uD83D\uDCCA Data Preview:\n\n" +
            "\u2022 Header row: ".concat(headerRow, "\n") +
            "\u2022 Total rows: ".concat(csvData.length, "\n") +
            "\u2022 Data rows: ".concat(csvData.length - 1, "\n") +
            "Continue processing?";
        var confirmResult = ui.alert("📋 Confirm Processing", previewMessage, ui.ButtonSet.YES_NO);
        if (confirmResult !== ui.Button.YES) {
            Logger.log("User cancelled processing confirmation");
            return;
        }
        var result = sendCSVToBackend(csvData, spreadsheetTitle, headerRow);
        ui.alert("BARS Leadership Processing Results", result.display_text, ui.ButtonSet.OK);
    }
    catch (error) {
        console.error("❌ Error in processLeadershipDiscountsWithHeaderPrompt:", error);
        var ui = SpreadsheetApp.getUi();
        ui.alert("❌ Error", "Failed to process leadership discounts: ".concat(error.message), ui.ButtonSet.OK);
    }
}
function sendCSVToBackend(csvData, spreadsheetTitle, headerRow) {
    try {
        Logger.log("📤 Sending CSV data to backend...");
        var payload = {
            csv_data: csvData,
            spreadsheet_title: spreadsheetTitle
        };
        if (headerRow !== undefined) {
            payload.header_row = headerRow;
        }
        var options = {
            method: "post",
            headers: {
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"
            },
            payload: JSON.stringify(payload)
        };
        var backendUrl = getBackendUrl();
        Logger.log("\uD83C\uDF10 Calling: ".concat(backendUrl, "/leadership/addTags"));
        var response = UrlFetchApp.fetch("".concat(backendUrl, "/leadership/addTags"), options);
        if (response.getResponseCode() !== 200) {
            throw new Error("Backend returned status ".concat(response.getResponseCode(), ": ").concat(response.getContentText()));
        }
        var result = JSON.parse(response.getContentText());
        Logger.log("✅ Backend processing completed successfully");
        return result;
    }
    catch (error) {
        console.error("❌ Error sending to backend:", error);
        throw new Error("Failed to communicate with backend: ".concat(error.message));
    }
}
function testBackendConnection(shouldShowConfirmation) {
    if (shouldShowConfirmation === void 0) { shouldShowConfirmation = true; }
    try {
        Logger.log("🧪 Testing backend connection...");
        var options = {
            method: "get",
            headers: {
                "ngrok-skip-browser-warning": "true"
            }
        };
        var backendUrl = getBackendUrl();
        var response = UrlFetchApp.fetch("".concat(backendUrl, "/leadership/health"), options);
        if (response.getResponseCode() === 200) {
            var result = JSON.parse(response.getContentText());
            Logger.log("✅ Backend connection successful:", result);
            if (shouldShowConfirmation === true) {
                var ui = SpreadsheetApp.getUi();
                ui.alert("✅ Connection Test Successful!", "Connected to backend successfully!\n\n" +
                    "\uD83C\uDF10 URL: ".concat(backendUrl, "\n") +
                    "\uD83D\uDCCA Status: ".concat(result.status, "\n") +
                    "\uD83D\uDD27 Service: ".concat(result.service, "\n\n") +
                    "\uD83C\uDFAF Ready to process leadership data!", ui.ButtonSet.OK);
            }
        }
        else {
            throw new Error("Backend returned status ".concat(response.getResponseCode()));
        }
    }
    catch (error) {
        console.error("❌ Backend connection failed:", error);
        var ui = SpreadsheetApp.getUi();
        ui.alert("❌ Connection Test Failed", "Could not connect to backend:\n\n" +
            "\u274C ".concat(error.message, "\n\n") +
            "\uD83C\uDF10 URL: ".concat(getBackendUrl(), "\n\n") +
            "\uD83D\uDD27 Troubleshooting:\n" +
            "1. Make sure your local server is running\n" +
            "2. Check that ngrok tunnel is active\n" +
            "3. Update the backend URL in secrets if needed\n" +
            "4. Verify the backend is accessible", ui.ButtonSet.OK);
    }
}
function showBackendInfo() {
    var backendUrl = getBackendUrl();
    var ui = SpreadsheetApp.getUi();
    ui.alert("🌐 Backend Information", "Current Backend URL:\n".concat(backendUrl, "\n\n") +
        "\uD83D\uDD17 Available Endpoints:\n" +
        "\u2022 Health Check: /leadership/health\n" +
        "\u2022 Add Tags (CSV Processing): /leadership/addTags\n" +
        "\u2022 Legacy Email List: /leadership/addToLeadership\n" +
        "\u2022 API Documentation: /docs\n\n" +
        "\uD83D\uDE80 This script uses the addTags endpoint with backend-generated " +
        "display text for maximum flexibility and performance.", ui.ButtonSet.OK);
}
function processLeadershipDiscounts() {
    var ui = SpreadsheetApp.getUi();
    ui.alert("🔄 Redirecting to New Method", "The legacy processing method has been upgraded!\n\n" +
        "You'll now use the new smart CSV processing which:\n" +
        "• Auto-detects email columns\n" +
        "• Handles complex spreadsheet formats\n" +
        "• Provides detailed processing reports\n" +
        "• Uses optimized backend processing\n\n" +
        "Click OK to continue with the new method.", ui.ButtonSet.OK);
    processLeadershipDiscountsSmartCSV();
}
