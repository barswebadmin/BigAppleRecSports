function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu("💳 BARS Payment Assistance")
    .addItem("💰 Process Payment Assistance Request", "processPaymentAssistanceRequest")
    // .addItem("Approve Payment Plan Request and Send Code to Player", "processPaymentPlanRequest")
    // .addItem("Disable a Payment Assistance Discount Code", "disableDiscountCode")
    .addSeparator()
    .addItem("📘 View Instructions", "showInstructions")
    .addToUi();
    
  // Show instructions on first open
  showInstructions();
}

function getExecAndWebEmails() {
  const currentYear = new Date().getFullYear(); // Get current year
  const folderId = "0ADOm6pR_jNs5Uk9PVA";
  const sheetNameContains = `${currentYear} Board / Leadership Contact Sheet`;
  
  // Step 1: Find the folder
  const folder = DriveApp.getFolderById(folderId);
   if (!folder) {
    Logger.log(`❌ Folder with ID "${folderId}" not found.`);
    return [];
  }

  // Step 2: Find the sheet that matches the pattern "{currentYear} Board / Leadership Contact Sheet"
  const files = folder.getFiles();
  let file = null;
  
  while (files.hasNext()) {
    const currentFile = files.next();
    if (currentFile.getName().includes(sheetNameContains)) {
      file = currentFile;
      break;
    }
  }

  if (!file) {
    Logger.log(`❌ No file matching "${sheetNameContains}" found in "${folderName}".`);
    return [];
  }

  // Step 3: Open the found file as a Spreadsheet
  const spreadsheet = SpreadsheetApp.openById(file.getId());
  const sheet = spreadsheet.getSheets()[0];

  const headers = sheet.getRange(6, 1, 1, sheet.getLastColumn()).getValues()[0]; // Get headers from row 6
  const emailColumnIndex = headers.findIndex(header => header.toLowerCase().includes("email")) + 1; // Find index of "EMAIL" column

  if (emailColumnIndex === 0) {
    Logger.log("❌ 'EMAIL' column not found.");
    return [];
  }

  // Get email values from the identified column, starting from row 7
  const emails = [];
  const dataRange = sheet.getRange(7, emailColumnIndex, sheet.getLastRow() - 6).getValues();

  for (let i = 0; i < dataRange.length; i++) {
    const email = dataRange[i][0].trim();
    if (!email) break; // Stop at the first empty cell
    emails.push(email);
  }

  // Append fixed emails
  emails.push("web@bigapplerecsports.com", "executive-board@bigapplerecsports.com");

  Logger.log(`✅ Exec and Web Emails: ${emails.join(", ")}`);
  return emails;
}