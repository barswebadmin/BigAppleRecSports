function pullOffWaitlist() {
  const ui = SpreadsheetApp.getUi();
  const rowNumberResponse = ui.prompt(
    'Pull Someone Off Waitlist',
    'Enter the row number to process:',
    ui.ButtonSet.OK_CANCEL
  );

  if (rowNumberResponse.getSelectedButton() !== ui.Button.OK) {
    Logger.log("User cancelled or closed prompt.");
    return;
  }

  const rowNumber = parseInt(rowNumberResponse.getResponseText().trim(), 10);
  if (!rowNumber || isNaN(rowNumber) || rowNumber < 2) {
    Logger.log("❌ Invalid row number entered.");
    return;
  }

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const sheetData = sheet.getDataRange().getValues();
  const headers = sheetData[0]; // header is first row (row 1)
  const row = sheetData[rowNumber - 1]; // subtract 1 for 0-based index

  Logger.log(`🔍 Processing row ${rowNumber}: ${JSON.stringify(row)}`);
  Logger.log(`🧠 Headers: ${JSON.stringify(headers)}`);

  // Get indexes
  const emailIndex = headers.findIndex(h => h.toLowerCase().includes("email address"));
  const firstNameIndex = headers.findIndex(h => h.toLowerCase().includes("first name"));
  const lastNameIndex = headers.findIndex(h => h.toLowerCase().includes("last name"));
  const leagueIndex = headers.findIndex(h => h.toLowerCase().includes("league you want to sign up for"));
  const phoneIndex = headers.findIndex(h => h.toLowerCase().includes("phone number"));
  const notesIndex = headers.findIndex(h => h.toLowerCase().includes("notes"));

  // Extract values
  const email = row[emailIndex]?.toString().trim().toLowerCase();
  const firstName = row[firstNameIndex]?.toString().trim();
  const lastName = row[lastNameIndex]?.toString().trim();
  const rawLeague = row[leagueIndex]?.toString().trim();
  const phone = row[phoneIndex]?.toString().trim();
  const normalizedPhoneNumber = normalizePhone(phone)

  const {season, year} = getCurrentSeasonAndYearFromSpreadsheetTitle()
  const [sport, day, rawDivision] = 
    ["Dodgeball - Tuesday Advanced - Open Division", "Dodgeball - Tuesday Social - Open Division"].includes(rawLeague)
    ?
    ["Dodgeball", "Tuesday", "Open Division"]
    :
      rawLeague === 'Pickleball - July 13th City Pickle Round Robin' ? ['Pickleball', 'Sunday', 'Round Robin'] : rawLeague.split(' - ')

  const productHandle = getProductHandleOrPromptFallback(year, season, sport, day, rawDivision)
  
  const waitlistTagToAdd = `${productHandle}-waitlist`

  if (!email) {
    Logger.log(`❌ No email found in row ${rowNumber}: ${JSON.stringify(row)}`);
    ui.alert(`❌ No email found in row ${rowNumber}: ${JSON.stringify(row)}`)
    return;
  }

  const customer = fetchShopifyCustomerByEmail(email);

  try {
    if (customer) {
      Logger.log(`✅ Customer found in Shopify: ${customer.id}`);
      const combinedTags = [...new Set([...customer.tags, waitlistTagToAdd])].join(', ');
      updateCustomer({ customerId: customer.id, tags: combinedTags, phone: normalizedPhoneNumber });
    } else {
      Logger.log(`❌ No customer found in Shopify. Creating one...`);
      const customerId = createShopifyCustomer(email, firstName, lastName);
      updateCustomer({ customerId, tags: [waitlistTagToAdd], phone: normalizedPhoneNumber})
    }

    if (notesIndex !== -1) {
      sheet.getRange(rowNumber, notesIndex + 1).setValue("Processed"); // +1 because getRange is 1-based
      Logger.log(`📝 Notes column updated to "Processed" for row ${rowNumber}`);
    } else {
      Logger.log("⚠️ Notes column not found. Skipping Notes update.");
}
  } catch(e) {
    ui.alert(e)
    return
  }

  const sendEmailResponse = ui.alert(
    'Email player with instructions',
    `Tag ${waitlistTagToAdd} added successfully to ${email}. \n 
    If you want to double check: add ${waitlistTagToAdd} to <i>your own</i> Shopify customer profile, and see if you can access that product page. \n \n
    Do you want to email the player now with instructions on how to register?`,
    ui.ButtonSet.YES_NO_CANCEL
  );

  if (sendEmailResponse !== ui.Button.YES) {
    ui.alert(`${email} was tagged with ${waitlistTagToAdd} but not emailed. Please ensure the player knows how to proceed!`)
    return;
  }

  const isMultiplePlayersAddedResponse = ui.alert(
    'Multiple players pulled off waitlist?',
    `Are you pulling multiple players off the waitlist (i.e. should the email indicate it so they know to hurry?)`,
    ui.ButtonSet.YES_NO_CANCEL
  );

  if ([ui.Button.YES, ui.Button.NO].includes(isMultiplePlayersAddedResponse)) {
    const isMultiplePlayersAdded = isMultiplePlayersAddedResponse === ui.Button.YES ? true : false
    sendEmailToPlayer(email, firstName, isMultiplePlayersAdded, rawLeague, capitalize(season), year)
  }

  
}