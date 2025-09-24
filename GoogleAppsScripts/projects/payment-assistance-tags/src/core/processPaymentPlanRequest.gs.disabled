const processPaymentPlanRequest = (action,rowId, requestName, requestEmail) => {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const sheetHeaders = data[0];

  const indexes = {
    rowId: sheetHeaders.indexOf("Unique Row ID"),
    fullName: sheetHeaders.indexOf("Name"),
    email: sheetHeaders.indexOf("Email Address"),
    season: sheetHeaders.indexOf("What season are you requesting assistance for?"),
    isEnabled: sheetHeaders.indexOf("Approved and Enabled?"),
    sport: sheetHeaders.indexOf("What sport do you want a payment plan for?"),
    numOfPayments: sheetHeaders.indexOf("Would you like to split your payments into 2 or 3 payments?"),
    dayOfPlay: sheetHeaders.indexOf("What day of play are you registering for? (Payment Plan)")
  };


  const findRowByRowId = (rowId) => {
    for (let i = 1; i < data.length; i++) {
      if ((data[i][indexes.rowId] || "").toString().trim() === rowId.trim()) {
        return { rowData: data[i], rowNumber: i + 1 };
      }
    }
    return { rowData: null, rowNumber: -1 };
  };

  const { rowData, rowNumber } = findRowByRowId(rowId);
  if (!rowData) {
    Logger.log(`❌ No row found for rowId: ${rowId}`);
    return { success: false, message: `⚠️ Could not find request in the spreadsheet.` };
  }

  if (action === "deny_payment_plan") {
    try {
      const fullName = rowData[indexes.fullName];
      const firstName = fullName.split(" ")[0].trim();
      const email = rowData[indexes.email];

      // Send denial email
      const emailResponse = sendDenialEmail(firstName, email);
      return { success: true, message: emailResponse.message };

    } catch (error) {
      return { success: false, message: `⚠️ Failed to send denial email to ${requestEmail}.` };
    }
  }

  try {

    const fullName = rowData[indexes.fullName];
    const firstName = fullName.split(" ")[0].trim();
    const email = rowData[indexes.email];
    const [year, season] = rowData[indexes.season].split("-").map(str => str.trim());
    const formattedYear = year.slice(-2);
    const numOfPayments = Number.parseInt(rowData[indexes.numOfPayments][0]);
    const sport = rowData[indexes.sport];
    const dayOfPlay = rowData[indexes.dayOfPlay];

    const tag = `pp-${season.toLowerCase()}-${year}-${numOfPayments}-payments`
    const code = `PPFinancialAssistance${capitalize(season)}${formattedYear}`;

    const matchingProductRow = getMatchingRow({ year, season, sport, dayOfPlay });
    if (!matchingProductRow) {
      Logger.log("❌ No matching row found in Product Sheet.");
      return { success: false, message: `⚠️ No matching product found for this request.` };
    }

    const planDetails = { year, season, sport, dayOfPlay, numOfPayments, code, tag, type: 'a Payment Plan' }
    const repaymentDetails = generateRepaymentDetails({ planDetails, matchingProductRow })

    const discountDetails = { season, year, tag, code, type: "a Payment Plan" };
    const addTagResponse = addTagToCustomerProfile({ playerDetails: { fullName, firstName, email }, discountDetails });
    const newOrReturning = addTagResponse.newOrReturning

    if (!addTagResponse.success) {
      Logger.log(`⚠️ Failed to add tag to Shopify customer: ${addTagResponse.message}`);
      return { success: false, message: `⚠️ Failed to apply discount in Shopify.` };
    }

    const sendEmailResponse = sendPaymentPlanConfirmationEmail({ playerDetails: { fullName, firstName, email, newOrReturning }, planDetails, repaymentDetails });

    if (rowNumber < 2 || rowNumber > sheet.getLastRow()) {
      Logger.log(`⚠️ Invalid row index: ${rowNumber}`);
      return { success: false, message: `⚠️ Unable to update the approval status.` };
    }
    sheet.getRange(rowNumber, indexes.isEnabled + 1).setValue("Payment Plan Approved");

    const getColumnLetter = index => {
      let column = "";
      while (index >= 0) {
        column = String.fromCharCode((index % 26) + 65) + column;
        index = Math.floor(index / 26) - 1;
      }
      return column;
    };
    const startColumn = 'A';
    const endColumn = getColumnLetter(sheet.getLastColumn() - 1); // 0-based index
    const sheetLink = `${SHEET_URL}${startColumn}${rowNumber}:${endColumn}${rowNumber}`;

    return { success: true, message: `${sendEmailResponse.message} \n\n🔗 <${sheetLink}|View Request in Google Sheets>` };

  } catch (error) {
    Logger.log(`❌ Error processing payment plan: ${error.message}`);
    MailApp.sendEmail({ to: "web@bigapplerecsports.com", subject: `Failed! ${error.message}` });
    return { success: false, message: `⚠️ An unexpected error occurred.` };
  }
}
