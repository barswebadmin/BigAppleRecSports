import { sendWaitlistProcessedEmailToPlayer } from '../helpers/emailHelpers';
import { constructProductHandle, getCurrentSeasonAndYearFromSpreadsheetTitle } from '../helpers/productHandleHelpers';
import { capitalize, normalizePhone } from '../shared-utilities/formatters';
import { createShopifyCustomer, fetchShopifyCustomerByEmail, updateCustomer } from '../shared-utilities/ShopifyUtils';

/**
 * Pull Player Off Waitlist Workflow
 * Admin workflow to tag customer in Shopify and optionally email them
 */

// biome-ignore lint/correctness/noUnusedVariables: GAS runtime menu callback
function pullOffWaitlist() {
  const ui = SpreadsheetApp.getUi();
  
  const rowNumberResponse = ui.prompt(
    'Pull Someone Off Waitlist',
    'Enter the row number to process:',
    ui.ButtonSet.OK_CANCEL
  );

  if (rowNumberResponse.getSelectedButton() !== ui.Button.OK) {
    Logger.log("User cancelled prompt");
    return;
  }

  const rowNumber = parseInt(rowNumberResponse.getResponseText().trim(), 10);
  
  if (!rowNumber || Number.isNaN(rowNumber) || rowNumber < 2) {
    ui.alert('❌ Invalid row number. Please enter a number greater than 1.');
    Logger.log("❌ Invalid row number entered");
    return;
  }

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const sheetData = sheet.getDataRange().getValues();
  const headers = sheetData[0];
  const row = sheetData[rowNumber - 1];

  Logger.log(`🔍 Processing row ${rowNumber}: ${JSON.stringify(row)}`);
  Logger.log(`🧠 Headers: ${JSON.stringify(headers)}`);

  const emailIndex = headers.findIndex(h => h.toLowerCase().includes("email address"));
  const firstNameIndex = headers.findIndex(h => h.toLowerCase().includes("first name"));
  const lastNameIndex = headers.findIndex(h => h.toLowerCase().includes("last name"));
  const leagueIndex = headers.findIndex(h => h.toLowerCase().includes("league you want to sign up for"));
  const phoneIndex = headers.findIndex(h => h.toLowerCase().includes("phone number"));
  const notesIndex = headers.findIndex(h => h.toLowerCase().includes("notes"));

  const email = row[emailIndex]?.toString().trim().toLowerCase();
  const firstName = row[firstNameIndex]?.toString().trim();
  const lastName = row[lastNameIndex]?.toString().trim();
  const rawLeague = row[leagueIndex]?.toString().trim();
  const phone = row[phoneIndex]?.toString().trim();
  const normalizedPhoneNumber = normalizePhone(phone);

  if (!email) {
    ui.alert(`❌ No email found in row ${rowNumber}`);
    Logger.log(`❌ No email found in row ${rowNumber}`);
    return;
  }

  const { season, year } = getCurrentSeasonAndYearFromSpreadsheetTitle();
  const spreadsheetName = SpreadsheetApp.getActiveSpreadsheet().getName();


  const productHandle = constructProductHandle(rawLeague, spreadsheetName);
  const waitlistTagToAdd = `${productHandle}-waitlist`;

  Logger.log(`🏷️ Waitlist tag to add: ${waitlistTagToAdd}`);

  const customer = fetchShopifyCustomerByEmail(email);

  try {
    if (customer) {
      Logger.log(`✅ Customer found in Shopify: ${customer.id}`);
      
      const existingTags = customer.tags || [];
      const combinedTags = [...new Set([...existingTags, waitlistTagToAdd])].join(', ');
      
      updateCustomer({ 
        customerId: customer.id, 
        tags: combinedTags, 
        phone: normalizedPhoneNumber 
      });
    } else {
      Logger.log(`❌ No customer found. Creating new customer...`);
      
      const customerId = createShopifyCustomer(email, firstName, lastName);
      
      updateCustomer({ 
        customerId, 
        tags: [waitlistTagToAdd], 
        phone: normalizedPhoneNumber 
      });
    }

    if (notesIndex !== -1) {
      sheet.getRange(rowNumber, notesIndex + 1).setValue("Processed");
      Logger.log(`📝 Notes column updated to "Processed" for row ${rowNumber}`);
    } else {
      Logger.log("⚠️ Notes column not found");
    }
    
  } catch (e) {
    ui.alert(`❌ Error: ${e.message}`);
    Logger.log(`❌ Error tagging customer: ${e.message}`);
    return;
  }

  const sendEmailResponse = ui.alert(
    'Email player with instructions',
    `Tag ${waitlistTagToAdd} added successfully to ${email}.\n\nIf you want to double check: add ${waitlistTagToAdd} to your own Shopify customer profile, and see if you can access that product page.\n\nDo you want to email the player now with instructions on how to register?`,
    ui.ButtonSet.YES_NO_CANCEL
  );

  if (sendEmailResponse !== ui.Button.YES) {
    ui.alert(`${email} was tagged with ${waitlistTagToAdd} but not emailed. Please ensure the player knows how to proceed!`);
    return;
  }

  const isMultiplePlayersAddedResponse = ui.alert(
    'Multiple players pulled off waitlist?',
    'Are you pulling multiple players off the waitlist (i.e. should the email indicate urgency so they know to hurry?)',
    ui.ButtonSet.YES_NO_CANCEL
  );

  if ([ui.Button.YES, ui.Button.NO].includes(isMultiplePlayersAddedResponse)) {
    const isMultiplePlayersAdded = isMultiplePlayersAddedResponse === ui.Button.YES;
    sendWaitlistProcessedEmailToPlayer(email, firstName, isMultiplePlayersAdded, rawLeague, capitalize(season), year);
    
    ui.alert('✅ Complete!', `${email} has been tagged and emailed.`, ui.ButtonSet.OK);
  } else {
    ui.alert(`${email} was tagged but not emailed.`);
  }
}

