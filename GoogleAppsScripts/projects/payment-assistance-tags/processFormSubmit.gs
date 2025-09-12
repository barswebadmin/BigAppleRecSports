function processFormSubmit(e) {

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  let data = sheet.getDataRange().getValues();
  const headers = data[0]; // Get header row

  // Find column indexes
  const timestampIndex = headers.indexOf("Timestamp");
  const rowIdIndex = headers.indexOf("Unique Row ID");
  const emailIndex = headers.indexOf("Email Address"); // Ensure this matches your actual form question

  if (timestampIndex === -1 || rowIdIndex === -1 || emailIndex === -1) {
    Logger.log("❌ Required columns not found.");
    return;
  }

  // Get the submitted email from form response
  const submittedEmail = e.namedValues["Email Address"]?.[0]?.trim().toLowerCase();
  if (!submittedEmail) {
    Logger.log("❌ No email found in form submission.");
    return;
  }

  // ✅ Wait for form submission to be fully written
  let newRowNumber = null;
  let attempts = 10; // Try for up to 10 seconds
  while (attempts > 0) {
    data = sheet.getDataRange().getValues(); // Refresh data
    for (let i = data.length - 1; i > 20; i--) { // Iterate from last row up
      const rowEmail = data[i][emailIndex]?.trim().toLowerCase();
      if (rowEmail === submittedEmail) {
        newRowNumber = i + 1; // Convert to 1-based index
        break;
      }
    }
    if (newRowNumber) break; // Stop loop once row is found
    Utilities.sleep(1000); // Wait 1 second before retrying
    attempts--;
  }

  if (!newRowNumber) {
    Logger.log("❌ Could not find the submitted row. Form may not have written yet.");
    return;
  }
  
  const existingRowIds = new Set(data.slice(1).map(row => row[rowIdIndex]).filter(id => id)); // Remove empty values

  let rowId;
  do {
    rowId = generateUid();
  } while (existingRowIds.has(rowId)); // Generate until a unique ID is found
  
  sheet.getRange(newRowNumber, rowIdIndex + 1).setValue(rowId);
  Logger.log(`✅ Row ID '${rowId}' assigned to row ${newRowNumber}`);

  // Determine request type
  const requestType = e.namedValues["Are you requesting..."]?.[0]?.trim().toLowerCase();

  if (!requestType) {
    Logger.log("❌ Request type not found.");
    return;
  }

  // const options = {
  //   method: "post",
  //   contentType: "application/json",
  //   payload: JSON.stringify(e)
  // };
  // const response = UrlFetchApp.fetch("https://xdakvg6v3jf5su2ioquv3izt2u0jcupn.lambda-url.us-east-1.on.aws/", options);

  // Logger.log(`response: ${JSON.stringify(response,null,2)}`)

  if (requestType.includes("payment plan")) {
    Logger.log(`📌 Processing Payment Plan for row ${newRowNumber}`);
    sendPaymentPlanRequest(e, rowId);
  } else if (requestType.includes("assistance")) {
    Logger.log(`📌 Processing Payment Assistance for row ${newRowNumber}`);
    sendPaymentAssistanceRequest(e, rowId);
  } else {
    Logger.log(`⚠️ Unrecognized request type: '${requestType}'. No processing triggered.`);
  }
}