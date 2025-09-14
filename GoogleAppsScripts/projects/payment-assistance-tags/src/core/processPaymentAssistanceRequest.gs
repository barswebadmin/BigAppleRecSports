
const processPaymentAssistanceRequest = (action,rowId) => {
  const ui = SpreadsheetApp.getUi();
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const sheetHeaders = data[0];

  const fullNameIndex = sheetHeaders.indexOf("Name");
  const emailAddressIndex = sheetHeaders.indexOf("Email Address");
  const assistanceTypeIndex = sheetHeaders.indexOf("Are you requesting...");
  const seasonIndex = sheetHeaders.indexOf("What season are you requesting assistance for?");
  const isEnabledIndex = sheetHeaders.indexOf("Approved and Enabled?")
  const rowIdIndex = sheetHeaders.indexOf("Unique Row ID")

  const rowsFoundForEmail = data.slice(1).map((row, i) => ({
    rowNumber: i + 2, // Adjust for header row
    email: row[emailAddressIndex],
    fullName: row[fullNameIndex],
    assistanceRequested: row[assistanceTypeIndex]?.toLowerCase().includes("assistance"),
    seasonYear: row[seasonIndex]?.trim()
  })).filter(row => row.rowId === selectedPlayerEmail && row.assistanceRequested);

  if (rowsFoundForEmail.length === 0) {
    ui.alert(`⚠️ No rows found for '${selectedPlayerEmail}' where Payment Assistance was requested. (Do you mean to enable a Payment Plan instead?)`);
    return;
  }



  let selectedRow = data.slice(1).filter(row => row.rowId === rowId);

  const optionsText = rowsFoundForEmail.map(row => `Row ${row.rowNumber} (${row.seasonYear})`).join(", \n");
  if (rowsFoundForEmail.length === 1) {
    const userSelection = ui.alert(
      `One result found for ${rowsFoundForEmail[0].fullName} (${selectedPlayerEmail}): Row ${rowsFoundForEmail[0].rowNumber} (requesting for ${rowsFoundForEmail[0].seasonYear}). Continue?`,
      ui.ButtonSet.YES_NO
    );

    if (userSelection !== ui.Button.YES) return;
    selectedRow = rowsFoundForEmail[0];
  } else {
     const userSelection = ui.prompt(
      `Multiple rows found for ${rowsFoundForEmail[0].fullName} (${selectedPlayerEmail}). Enter the row number and click OK:\n\n${optionsText}`,
      ui.ButtonSet.OK_CANCEL
    );

    if (userSelection.getSelectedButton() !== ui.Button.OK) return;

    const selectedRowNumber = userSelection.getResponseText();
    selectedRow = rowsFoundForEmail.find(row => row.rowNumber.toString() === selectedRowNumber);
    if (!selectedRow) {
      ui.alert("⚠️ Invalid row selection.");
      return;
    }
  }

  const discountInput = ui.prompt(
    "Enter the discount percentage you want to provide, as a whole number (e.g. 25, 50, 75, 100):",
    ui.ButtonSet.OK_CANCEL
  );

  if (discountInput.getSelectedButton() !== ui.Button.OK) {
    Logger.log("⚠️ Process canceled.");
    return;
  }

  const discountPercentageAsString = discountInput.getResponseText();
  if (!/^\d+$/.test(discountPercentageAsString)) {
    ui.alert("⚠️ Invalid discount percentage. Please enter a whole number.");
    return;
  }

  const discountPercentageAsFloat = Number.parseFloat(discountPercentageAsString) / 100;
  const fullName = selectedRow.fullName
  const firstName = fullName.split(" ")[0].trim()
  const [year, season] = selectedRow.seasonYear.split("-").map(str => str.trim());
  const formattedYear = year.slice(-2);
  const tag = `fa${discountPercentageAsString}${season.toLowerCase()}${formattedYear}`;
  const discountDetails = { discountPercentage: discountPercentageAsString, season, year, tag }

  const playerDetails = {fullName, email: selectedPlayerEmail}

  try {
    const response = addTagToCustomerProfile({playerDetails, discountDetails});
    if (response.success) {
      const rowIndex = selectedRow.rowNumber;
      if (rowIndex < 2 || rowIndex > sheet.getLastRow()) {
        ui.alert(`⚠️ Invalid row index: ${rowIndex}. Check your selection.`);
        return;
      }
      const isEnabledCell = sheet.getRange(rowIndex, isEnabledIndex + 1);
      isEnabledCell.setValue(true);

      var barsLogoBlob = UrlFetchApp
                          .fetch(BARS_LOGO_URL)
                          .getBlob()
                          .setName("barsLogo.png");
      MailApp.sendEmail({
        to: playerDetails.email,
        cc: 'executive-board@bigapplerecsports.com',
        replyTo: 'executive-board@bigapplerecsports.com',
        subject: "✅ Payment Assistance Approved!",
        htmlBody: `Hi ${firstName},
        <br>
        <br>
        <p>We are very happy to inform you that have been approved for <u>Financial Assistance</u> of <b>${discountDetails.discountPercentage}% off</b> one registration this <u>${discountDetails.season}</u> season!</p>

        <p>Please use the discount code <b><u>Financial${discountDetails.discountPercentage}Assistance${discountDetails.season}${discountDetails.year.slice(-2)}</u></b> - to register for any season - it is not case-sensitive.</p>

        <p>Please also note:
        <ul><li>You will need to log in with your BARS account in order to use the code, as it's tied to the email address you provided</li>
        <li>It is only valid for this upcoming season and will expire if not used. Please let us know if your plans change, so we can offer the assisance to someone who needs it <i>now</i></li>
        </ul>
        Let us know if you have any questions.</p>
        <br>
        Warmly,<br>
        <h3>BARS Leadership</h3>
        <br>
        <img src="cid:barsLogo" style="width:225px; height:auto;"'>`,
        inlineImages: { "barsLogo": barsLogoBlob}});
      ui.alert(response.message);
    } else {
      ui.alert(`⚠️ ${response.message}`);
    }
  } catch (error) {
    ui.alert(`❌ An unexpected error occurred: ${error.message}`);
  }

}


// const disableDiscountCode = () => {
//   const ui = SpreadsheetApp.getUi();
//   const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
//   const data = sheet.getDataRange().getValues();
//   const sheetHeaders = data[0];

//   const currentUserEmail = Session.getActiveUser().getEmail();
//   const isEnabledIndex = sheetHeaders.indexOf("Enabled and Approved?")
// }
