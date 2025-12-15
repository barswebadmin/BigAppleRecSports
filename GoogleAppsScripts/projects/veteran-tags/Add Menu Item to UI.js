const ui = SpreadsheetApp.getUi();

function onOpen() {
  ui.createMenu("🎖️ BARS Veteran Tags")
    .addItem("➕ Add Veteran Tags to Customers", "addVeteranTagToCustomerEmails")
    .addItem("➖ Remove Veteran Tags from Customers", "removeVeteranTagFromCustomerEmails")
    .addSeparator()
    .addItem("📧 Send Veteran Eligibility Email", "sendVeteranEmailFromMenu")
    .addSeparator()
    .addItem("📘 View Instructions", "showInstructions")
    .addToUi();
    
  // Show instructions on first open
  showInstructions();
}

function sendVeteranEmailFromMenu() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

  const fieldsToProcess = {
    sport: getFieldValue(sheet, "Sport"),
    season: getFieldValue(sheet, "Season"),
    year: getFieldValue(sheet, "Year"),
    day: getFieldValue(sheet, "Day"),
    division: getFieldValue(sheet, "Division"),
    veteranTag: getFieldValue(sheet, "Vet code to be added"),
    leadershipEmailAddress: getFieldValue(sheet, "BARS team email alias")
  };

  // ✅ Check for missing fields
  for (const [key, value] of Object.entries(fieldsToProcess)) {
    if (!value) return;
  }

  const emailColIndex = getEmailColumnIndex(sheet);
  const emailRange = getEmails(sheet, emailColIndex);

  if (emailRange.length === 0) {
    ui.alert("⚠️ No emails found in the 'Vet Emails' column.");
    return;
  }

  const { sport, season, year, day, division, veteranTag, leadershipEmailAddress } = fieldsToProcess;

  // // Only include players who have the tag
  // const veteransList = emailRange.filter(email => {
  //   const [_, tags] = getCustomerDetails(email);
  //   return Array.isArray(tags) && tags.includes(veteranTag);
  // });

  // if (veteransList.length === 0) {
  //   ui.alert("⚠️ No players with the veteran tag found.");
  //   return;
  // }

  const confirmSend = ui.alert(
    `Send email to ${emailRange.length} player(s)?`,
    ui.ButtonSet.OK_CANCEL
  );

  if (confirmSend === ui.Button.CANCEL || confirmSend === ui.Button.CLOSE) return;

  sendVeteranEmail(emailRange, sport, day, division, season, year, leadershipEmailAddress);
  ui.alert(`✅ Emails sent to ${emailRange.length} veteran(s)!`);
}