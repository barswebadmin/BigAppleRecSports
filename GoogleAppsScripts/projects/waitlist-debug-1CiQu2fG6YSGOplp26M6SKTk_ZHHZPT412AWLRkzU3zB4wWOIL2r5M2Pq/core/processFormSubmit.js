/**
 * Google Form Submission Trigger
 * Automatically triggered when someone submits the waitlist form
 * Validates product, calculates position, and sends confirmation email
 */

function processFormSubmit(e) {
  Logger.log("🚀 processFormSubmit called");
  Logger.log("📥 Raw event object: " + JSON.stringify(e, null, 2));
  Logger.log("📝 namedValues keys: " + JSON.stringify(Object.keys(e.namedValues || {})));

  const emailEntry = Object.entries(e.namedValues).find(([key]) =>
    key.toLowerCase().includes("email address")
  );
  const submittedEmail = emailEntry?.[1]?.[0]?.trim().toLowerCase();

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  let sheetData = sheet.getDataRange().getValues();
  const header = sheetData[0];

  Logger.log("📊 Sheet header: " + JSON.stringify(header));

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
  Logger.log("  firstNameEntry: " + JSON.stringify(firstNameEntry));
  Logger.log("  emailEntry: " + JSON.stringify(emailEntry));
  Logger.log("  leagueEntry: " + JSON.stringify(leagueEntry));
  Logger.log("  timestampEntry: " + JSON.stringify(timestampEntry));

  const submittedFirstName = firstNameEntry?.[1]?.[0]?.trim();
  const submittedLeague = leagueEntry?.[1]?.filter(val => val && val.trim()).pop()?.trim();
  const submittedTimestamp = new Date(timestampEntry?.[1]?.[0]);

  Logger.log("📋 Processed form values:");
  Logger.log("  submittedFirstName: " + submittedFirstName);
  Logger.log("  submittedEmail: " + submittedEmail);
  Logger.log("  submittedLeague: " + submittedLeague);
  Logger.log("  submittedTimestamp: " + submittedTimestamp);

  const emailValid = !!submittedEmail;
  const leagueValid = !!submittedLeague;
  const timestampValid = !!submittedTimestamp && !isNaN(submittedTimestamp.getTime());

  Logger.log("✅ Field validation results:");
  Logger.log("  emailValid: " + emailValid);
  Logger.log("  leagueValid: " + leagueValid);
  Logger.log("  timestampValid: " + timestampValid);

  if (!emailValid || !leagueValid || !timestampValid) {
    Logger.log("❌ Missing submission data - validation failed");
    Logger.log("📝 All available form field names:");
    Object.keys(e.namedValues || {}).forEach(key => {
      Logger.log(`  "${key}": ${JSON.stringify(e.namedValues[key])}`);
    });
    return;
  }

  // Validate product and inventory
  Logger.log("🔍 Validating product and inventory for league: " + submittedLeague);
  const productHandle = constructProductHandleFromLeagueAndSpreadsheet(submittedLeague, sheet.getParent().getName());
  Logger.log("🔍 Constructed product handle: " + productHandle);
  const validationResult = validateProductAndInventory(productHandle);

  if (!validationResult.isValid) {
    Logger.log("❌ === VALIDATION FAILED ===");
    Logger.log("❌ Validation failed: " + validationResult.reason);
    Logger.log("📧 SENDING EMAIL NOTIFICATION TO " + DEBUG_EMAIL);

    const emailResult = sendValidationErrorEmailToAdmin(submittedLeague, submittedEmail, validationResult.reason, productHandle);
    Logger.log(`📧 Email notification result: ${emailResult}`);

    addCanceledNoteToRow(e, submittedEmail, submittedLeague, validationResult.reason);
    Logger.log("🛑 VALIDATION FLOW COMPLETE - STOPPING PROCESSING");
    return;
  }

  Logger.log("✅ Validation passed - proceeding with waitlist processing");

  const emailCol = header.findIndex(h => h.toLowerCase().includes("email address"));
  const leagueCol = header.findIndex(h => h.toLowerCase().includes("please select the league you want to sign up for"));
  const timestampCol = 0;
  const notesCol = header.findIndex(h => h.toLowerCase().includes("notes"));

  Logger.log("📊 Column mappings:");
  Logger.log("  emailCol: " + emailCol);
  Logger.log("  leagueCol: " + leagueCol);
  Logger.log("  notesCol: " + notesCol);

  let foundRowIndex = -1;

  for (let attempts = 0; attempts < 10; attempts++) {
    Logger.log(`🔄 Row matching attempt ${attempts + 1}/10`);
    const dataRange = sheet.getDataRange();
    sheetData = dataRange.getValues();
    const backgrounds = dataRange.getBackgrounds();
    
    const filteredData = sheetData.filter((row, i) => {
      if (i === 0) return false;
      
      const notesVal = (row[notesCol] || "").toString().toLowerCase();
      if (notesVal.includes("process") || notesVal.includes("cancel") || notesVal.includes("done")) {
        return false;
      }
      
      // Skip if row has any cell with a background color (not white/default)
      const rowBackgrounds = backgrounds[i];
      const hasBackgroundColor = rowBackgrounds.some(bg => {
        const bgLower = (bg || '').toLowerCase();
        return bgLower && bgLower !== '#ffffff' && bgLower !== '#fff' && bgLower !== 'white';
      });
      
      return !hasBackgroundColor;
    });

    Logger.log(`📋 After filtering, ${filteredData.length} unprocessed rows to check`);

    for (let i = 0; i < filteredData.length; i++) {
      const row = filteredData[i];
      const rowEmail = row[emailCol]?.toString().trim().toLowerCase();
      const rowLeague = row[leagueCol]?.toString().trim();

      if (rowEmail === submittedEmail && rowLeague === submittedLeague) {
        Logger.log(`✅ Found matching row at filtered index ${i}`);
        foundRowIndex = sheetData.findIndex(r =>
          r[emailCol]?.toString().trim().toLowerCase() === submittedEmail &&
          r[leagueCol]?.toString().trim() === submittedLeague
        );
        Logger.log(`✅ Found matching row at actual sheet index ${foundRowIndex}`);
        break;
      }
    }

    if (foundRowIndex !== -1) {
      Logger.log(`✅ Match found on attempt ${attempts + 1}!`);
      break;
    }

    Utilities.sleep(1000);
  }

  if (foundRowIndex === -1) {
    Logger.log("❌ Could not find matching row after 10 attempts.");
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: "❌ Waitlist Error - Row Not Found",
      htmlBody: `
        <p>Could not find matching row after form submission.</p>
        <p><strong>Email:</strong> ${submittedEmail}</p>
        <p><strong>League:</strong> ${submittedLeague}</p>
        <p><strong>Timestamp:</strong> ${submittedTimestamp.toISOString()}</p>
      `
    });
    return;
  }

  // Calculate waitlist position
  const userTimestamp = new Date(sheetData[foundRowIndex][timestampCol]);
  Logger.log(`📊 Calculating waitlist position for user at row ${foundRowIndex}`);
  
  // Get background colors to check for highlighted/colored rows
  const backgrounds = sheet.getDataRange().getBackgrounds();
  
  let earlierCount = 0;

  for (let i = 1; i < sheetData.length; i++) {
    const notesVal = (sheetData[i][notesCol] || "").toString().toLowerCase();
    
    // Skip if notes contain process/cancel/done
    if (notesVal.includes("process") || notesVal.includes("cancel") || notesVal.includes("done")) {
      Logger.log(`⏭️ Skipping row ${i + 1} - notes contain: ${notesVal}`);
      continue;
    }
    
    // Skip if row has any cell with a background color (not white/default)
    const rowBackgrounds = backgrounds[i];
    const hasBackgroundColor = rowBackgrounds.some(bg => {
      const bgLower = (bg || '').toLowerCase();
      return bgLower && bgLower !== '#ffffff' && bgLower !== '#fff' && bgLower !== 'white';
    });
    
    if (hasBackgroundColor) {
      Logger.log(`⏭️ Skipping row ${i + 1} - has background color`);
      continue;
    }

    const league = sheetData[i][leagueCol]?.toString().trim();
    const timestamp = new Date(sheetData[i][timestampCol]);

    if (league === submittedLeague && timestamp < userTimestamp) {
      earlierCount++;
    }
  }

  const waitlistPosition = earlierCount + 1;
  Logger.log(`📊 Waitlist calculation complete: user is #${waitlistPosition}`);

  // Send confirmation email
  Logger.log("📧 === SENDING WAITLIST CONFIRMATION EMAIL ===");
  const encodedEmail = encodeURIComponent(submittedEmail);
  const encodedLeague = encodeURIComponent(submittedLeague);
  const baseUrl = WAITLIST_WEB_APP_URL;
  const spotCheckUrl = `${baseUrl}?email=${encodedEmail}&league=${encodedLeague}`;

  const barsLogoBlob = UrlFetchApp
    .fetch(BARS_LOGO_URL)
    .getBlob()
    .setName("barsLogo");

  Logger.log(`📧 About to get sport email alias for league: ${submittedLeague} (type: ${typeof submittedLeague})`);
  const sportAlias = getSportEmailAlias(submittedLeague);
  Logger.log(`📧 Got sport alias: ${sportAlias}`);
  const replyToEmail = `${sportAlias}@bigapplerecsports.com`;
  Logger.log(`📧 Reply-to email: ${replyToEmail}`);

  MailApp.sendEmail({
    to: submittedEmail,
    replyTo: replyToEmail,
    subject: `🏳️‍🌈 Your Waitlist Spot for Big Apple ${submittedLeague}`,
    htmlBody: `
      <p>Hi ${submittedFirstName},</p>
      <p>Thanks for joining the waitlist for <strong>${submittedLeague}</strong>!</p>
      <p>You are currently <strong>#${waitlistPosition}</strong> on the waitlist.</p>
      <p>We'll reach out if a spot opens up!</p>

      <div style="background-color: #e8f5e8; border: 2px solid #4CAF50; border-radius: 10px; padding: 20px; margin: 20px 0; text-align: center;">
        <h3 style="margin: 0 0 15px 0; color: #2e7d32;">🔍 Check Your Waitlist Position</h3>
        <p style="margin: 15px 0; color: #333;">View your position for <strong>${submittedLeague}</strong> and switch between all your leagues:</p>
        <a href="${spotCheckUrl}" style="display: inline-block; background: #4CAF50; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; margin: 10px 0;">Check Your Waitlist Position (#${waitlistPosition})</a>
      </div>

      <div style="background-color: #ffebee; border: 2px solid #f44336; border-radius: 8px; padding: 15px; margin: 20px 0;">
        <p style="margin: 0; color: #d32f2f; font-weight: bold;">⚠️ <strong>Important Note for Safari Users:</strong></p>
        <p style="margin: 10px 0 0 0; color: #c62828; font-size: 14px;">
          This waitlist checker does not work in Safari due to browser restrictions.
          Please use <strong>Chrome, Firefox, or Edge</strong> for the best experience.
        </p>
      </div>

      --<br>
      <p>Warmly,<br>
      <b>BARS Leadership</b></p>
      <img src="cid:barsLogo" style="width:225px; height:auto;">
    `,
    inlineImages: { barsLogo: barsLogoBlob },
  });

  Logger.log(`✅ Successfully processed form submission for ${submittedEmail}`);
  Logger.log(`📧 Emailed waitlist confirmation with spot #${waitlistPosition}`);
}

/**
 * Construct product handle from league name and spreadsheet name
 * @param {string} league - League name (e.g., "Kickball - Sunday - Open Division")
 * @param {string} spreadsheetName - Spreadsheet name (e.g., "Fall 2025 Waitlist")
 * @returns {string} - Product handle
 */
function constructProductHandleFromLeagueAndSpreadsheet(league, spreadsheetName) {
  try {
    const spreadsheetMatch = spreadsheetName.match(/(\w+)\s+(\d{4})/);
    if (!spreadsheetMatch) {
      throw new Error(`Could not extract season and year from: ${spreadsheetName}`);
    }

    const season = spreadsheetMatch[1].toLowerCase();
    const year = spreadsheetMatch[2];

    const leagueParts = league.split(' - ').map(part => part.trim());
    if (leagueParts.length < 3) {
      throw new Error(`League format not recognized: ${league}`);
    }

    const sport = leagueParts[0].toLowerCase();
    const day = leagueParts[1].toLowerCase();
    const rawDivision = leagueParts[2];
    const division = rawDivision.split(' ')[0].replace('+', '').toLowerCase() + 'div';

    const handle = `${year}-${season}-${sport}-${day}-${division}`;
    Logger.log(`🔗 Constructed handle: ${handle}`);
    return handle;

  } catch (error) {
    Logger.log(`💥 Error constructing handle: ${error.message}`);
    const fallbackHandle = league.toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');
    Logger.log(`🔄 Using fallback handle: ${fallbackHandle}`);
    return fallbackHandle;
  }
}

/**
 * Add canceled note to row when validation fails
 */
function addCanceledNoteToRow(e, email, league, reason) {
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
    Logger.log("💥 Error adding cancellation note: " + error.message);
  }
}

/**
 * Send validation error email to admin
 */
function sendValidationErrorEmailToAdmin(league, userEmail, reason, productHandle) {
  try {
    Logger.log("📧 === SENDING ADMIN VALIDATION ERROR EMAIL ===");
    
    const errorIcon = reason.includes("No product found") ? "🚫" : "📦";
    const title = reason.includes("No product found") ? "Product Not Found" : "Inventory Available";
    const subject = `${errorIcon} Waitlist Validation Error: ${title}`;

    const htmlBody = `
      <div style="font-family: Arial, sans-serif; max-width: 600px;">
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
          <h2 style="color: #dc3545; margin: 0;">${errorIcon} Waitlist Validation Error</h2>
        </div>

        <div style="background: white; padding: 20px; border: 1px solid #dee2e6; border-radius: 8px;">
          <h3 style="color: #495057; margin-top: 0;">Error Details</h3>
          <table style="width: 100%; border-collapse: collapse;">
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Error Type:</td>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">${title}</td>
            </tr>
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">League:</td>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">${league}</td>
            </tr>
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">User Email:</td>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">${userEmail}</td>
            </tr>
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Product Handle:</td>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><code>${productHandle}</code></td>
            </tr>
            <tr>
              <td style="padding: 8px; font-weight: bold;">Timestamp:</td>
              <td style="padding: 8px;">${new Date().toLocaleString()}</td>
            </tr>
          </table>
        </div>

        <div style="background: #e9ecef; padding: 15px; border-radius: 8px; margin-top: 20px;">
          <h4 style="margin: 0 0 10px 0;">Next Steps:</h4>
          <ul style="margin: 0; padding-left: 20px;">
            <li>User has NOT been added to the waitlist</li>
            <li>Row has been marked as "Canceled" in the spreadsheet</li>
          </ul>
        </div>
      </div>
    `;

    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: subject,
      htmlBody: htmlBody
    });

    Logger.log("✅ Admin validation error email sent successfully");
    return true;
  } catch (error) {
    Logger.log(`💥 Error sending admin validation email: ${error.message}`);
    return false;
  }
}

