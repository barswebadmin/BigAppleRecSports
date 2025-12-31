import { DEBUG_EMAIL } from '../config/constants';
import { sendValidationErrorEmailToAdmin, sendWaitlistConfirmationEmail } from '../helpers/emailHelpers';
import { constructProductHandle } from '../helpers/productHandleHelpers';
import { calculateWaitlistPosition } from '../helpers/waitlistCalculation';
import { validateProductAndInventory } from '../shared-utilities/ShopifyUtils';

/**
 * Google Form Submission Trigger
 * Automatically triggered when someone submits the waitlist form
 * Validates product, calculates position, and sends confirmation email
 */

export function processFormSubmit(e) {
  Logger.log("🚀 processFormSubmit called");
  Logger.log(`📥 Raw event object: ${JSON.stringify(e, null, 2)}`);
  Logger.log(`📝 namedValues keys: ${JSON.stringify(Object.keys(e.namedValues || {}))}`);

  const emailEntry = Object.entries(e.namedValues).find(([key]) =>
    key.toLowerCase().includes("email address")
  );
  const submittedEmail = emailEntry?.[1]?.[0]?.trim().toLowerCase();

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  let sheetData = sheet.getDataRange().getValues();
  const header = sheetData[0];

  Logger.log(`📊 Sheet header: ${JSON.stringify(header)}`);

  const firstNameEntry = Object.entries(e.namedValues).find(([key]) =>
    key.toLowerCase().includes("first name")
  );
  const leagueEntry = Object.entries(e.namedValues).find(([key]) =>
    key.toLowerCase().includes("please select the league you want to sign up for")
  );
  const timestampEntry = Object.entries(e.namedValues).find(([key]) =>
    key.toLowerCase().includes("timestamp")
  );

  Logger.log("🔍 Field lookup results:");
  Logger.log(`  firstNameEntry: ${JSON.stringify(firstNameEntry)}`);
  Logger.log(`  emailEntry: ${JSON.stringify(emailEntry)}`);
  Logger.log(`  leagueEntry: ${JSON.stringify(leagueEntry)}`);
  Logger.log(`  timestampEntry: ${JSON.stringify(timestampEntry)}`);

  const submittedFirstName = firstNameEntry?.[1]?.[0]?.trim();
  const submittedLeague = leagueEntry?.[1]?.filter(val => val?.trim())?.pop()?.trim();
  const submittedTimestamp = new Date(timestampEntry?.[1]?.[0]);

  Logger.log("📋 Processed form values:");
  Logger.log(`  submittedFirstName: ${submittedFirstName}`);
  Logger.log(`  submittedEmail: ${submittedEmail}`);
  Logger.log(`  submittedLeague: ${submittedLeague}`);
  Logger.log(`  submittedTimestamp: ${submittedTimestamp}`);

  const emailValid = !!submittedEmail;
  const leagueValid = !!submittedLeague;
  const timestampValid = !!submittedTimestamp && !Number.isNaN(submittedTimestamp.getTime());

  Logger.log("✅ Field validation results:");
  Logger.log(`  emailValid: ${emailValid}`);
  Logger.log(`  leagueValid: ${leagueValid}`);
  Logger.log(`  timestampValid: ${timestampValid}`);

  if (!emailValid || !leagueValid || !timestampValid) {
    Logger.log("❌ Missing submission data - validation failed");
    Logger.log("📝 All available form field names:");
    Object.keys(e.namedValues || {}).forEach(key => {
      Logger.log(`  "${key}": ${JSON.stringify(e.namedValues[key])}`);
    });
    return;
  }

  // Validate product and inventory
  Logger.log(`🔍 Validating product and inventory for league: ${submittedLeague}`);
  const productHandle = constructProductHandle(submittedLeague, sheet.getParent().getName());
  Logger.log(`🔍 Constructed product handle: ${productHandle}`);
  const validationResult = validateProductAndInventory(productHandle);

  if (!validationResult.isValid) {
    Logger.log("❌ === VALIDATION FAILED ===");
    Logger.log(`❌ Validation failed: ${validationResult.reason}`);
    Logger.log(`📧 SENDING EMAIL NOTIFICATION TO ${DEBUG_EMAIL}`);

    const emailResult = sendValidationErrorEmailToAdmin(submittedLeague, submittedEmail, validationResult.reason, productHandle);
    Logger.log(`📧 Email notification result: ${emailResult}`);

    addCanceledNoteToRow(submittedEmail, submittedLeague, validationResult.reason);
    Logger.log("🛑 VALIDATION FLOW COMPLETE - STOPPING PROCESSING");
    return;
  }

  Logger.log("✅ Validation passed - proceeding with waitlist processing");

  const emailCol = header.findIndex(h => h.toLowerCase().includes("email address"));
  const leagueCol = header.findIndex(h => h.toLowerCase().includes("please select the league you want to sign up for"));
  const notesCol = header.findIndex(h => h.toLowerCase().includes("notes"));

  Logger.log("📊 Column mappings:");
  Logger.log(`  emailCol: ${emailCol}`);
  Logger.log(`  leagueCol: ${leagueCol}`);
  Logger.log(`  notesCol: ${notesCol}`);

  // Wait for form data to appear in spreadsheet (can take a moment after submission)
  let rowFound = false;

  for (let attempts = 0; attempts < 10; attempts++) {
    Logger.log(`🔄 Checking if form data exists (attempt ${attempts + 1}/10)`);
    
    sheetData = sheet.getDataRange().getValues();
    
    // Simple check: does email+league combination exist?
    const exists = sheetData.some((row, i) => {
      if (i === 0) return false; // Skip header
      const rowEmail = (row[emailCol] || '').toString().trim().toLowerCase();
      const rowLeague = (row[leagueCol] || '').toString().trim();
      return rowEmail === submittedEmail && rowLeague === submittedLeague;
    });
    
    if (exists) {
      Logger.log(`✅ Form data found on attempt ${attempts + 1}!`);
      rowFound = true;
      break;
    }

    Logger.log(`⏳ Form data not yet in sheet, waiting...`);
    Utilities.sleep(1000);
  }

  if (!rowFound) {
    Logger.log("❌ Form data never appeared in spreadsheet after 10 attempts.");
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: "❌ Waitlist Error - Form Data Not Found",
      htmlBody: `
        <p>Form was submitted but data never appeared in spreadsheet.</p>
        <p><strong>Email:</strong> ${submittedEmail}</p>
        <p><strong>League:</strong> ${submittedLeague}</p>
        <p><strong>Timestamp:</strong> ${submittedTimestamp.toISOString()}</p>
      `
    });
    return;
  }

  // Calculate waitlist position using shared helper (it will find the row and calculate)
  Logger.log(`📊 Calculating waitlist position for ${submittedEmail} in ${submittedLeague}`);
  const positionResult = calculateWaitlistPosition(submittedEmail, submittedLeague);
  
  if (!positionResult.found) {
    Logger.log(`❌ Failed to calculate waitlist position: ${positionResult.error || 'Unknown error'}`);
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: "❌ Waitlist Error - Position Calculation Failed",
      htmlBody: `
        <p>Failed to calculate waitlist position.</p>
        <p><strong>Email:</strong> ${submittedEmail}</p>
        <p><strong>League:</strong> ${submittedLeague}</p>
        <p><strong>Error:</strong> ${positionResult.error || 'Unknown error'}</p>
      `
    });
    return;
  }
  
  const waitlistPosition = positionResult.position;
  Logger.log(`📊 Waitlist calculation complete: user is #${waitlistPosition}`);

  // Send confirmation email using helper function
  const emailSent = sendWaitlistConfirmationEmail(submittedEmail, submittedLeague, waitlistPosition, submittedFirstName);
  
  if (emailSent) {
  Logger.log(`✅ Successfully processed form submission for ${submittedEmail}`);
  Logger.log(`📧 Emailed waitlist confirmation with spot #${waitlistPosition}`);
  } else {
    Logger.log(`⚠️ Form processed but email failed for ${submittedEmail}`);
  }
}


/**
 * Add canceled note to row when validation fails
 */
function addCanceledNoteToRow(email, league, reason) {
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    const sheetData = sheet.getDataRange().getValues();
    const header = sheetData[0];

    const emailCol = header.findIndex(h => h.toLowerCase().includes("email address"));
    const leagueCol = header.findIndex(h => h.toLowerCase().includes("please select the league you want to sign up for"));
    const notesCol = header.findIndex(h => h.toLowerCase().includes("notes"));

    if (notesCol === -1) {
      Logger.log("❌ Could not find notes column");
      return;
    }

    for (let i = 1; i < sheetData.length; i++) {
      const rowEmail = sheetData[i][emailCol]?.toString().trim().toLowerCase();
      const rowLeague = sheetData[i][leagueCol]?.toString().trim();

      if (rowEmail === email.toLowerCase() && rowLeague === league) {
        const cancelNote = `Canceled - ${reason}`;
        sheet.getRange(i + 1, notesCol + 1).setValue(cancelNote);
        Logger.log(`✅ Added cancellation note to row ${i + 1}: ${cancelNote}`);
        return;
      }
    }

    Logger.log("❌ Could not find matching row to add cancellation note");
  } catch (error) {
    Logger.log(`💥 Error adding cancellation note: ${error.message}`);
  }
}
