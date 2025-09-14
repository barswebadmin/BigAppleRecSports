//not needed for payment plans. consider deleting after updating payment assistance requests

function updateIsEnabledColumn(email, season, year, status) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const headers = data[0];

  const emailIndex = headers.indexOf("Email Address");
  const seasonIndex = headers.indexOf("What season are you requesting assistance for?");
  const isEnabledIndex = headers.indexOf("Approved and Enabled?");

  if (emailIndex === -1 || seasonIndex === -1 || isEnabledIndex === -1) {
    Logger.log("❌ Required columns not found.");
    return;
  }

  for (let i = 1; i < data.length; i++) {
    if (data[i][emailIndex] === email && data[i][seasonIndex] === `${year} - ${season}`) {
      sheet.getRange(i + 1, isEnabledIndex + 1).setValue(status);
      Logger.log(`✅ Updated row ${i + 1} as Approved and Enabled.`);
      return;
    }
  }
  Logger.log("❌ No matching row found to update.");
}
