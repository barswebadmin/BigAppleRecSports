function processFormSubmit(e) {
  // 🔍 DEBUGGING: Log the complete event object
  Logger.log("🚀 processFormSubmit called");
  Logger.log("📥 Raw event object: " + JSON.stringify(e, null, 2));
  Logger.log("📝 namedValues keys: " + JSON.stringify(Object.keys(e.namedValues || {})));
  
  // 🚧 TESTING MODE: Only process submissions from test email
  const emailEntry = Object.entries(e.namedValues).find(([key]) =>
    key.toLowerCase().includes("email address")
  );
  const submittedEmail = emailEntry?.[1]?.[0]?.trim().toLowerCase();
  
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  let sheetData = sheet.getDataRange().getValues();
  const header = sheetData[0];
  
  // 🔍 DEBUGGING: Log header information
  Logger.log("📊 Sheet header: " + JSON.stringify(header));

  const firstNameEntry = Object.entries(e.namedValues).find(([key]) =>
    key.toLowerCase().includes("first name")
  );

  // emailEntry already found above in testing mode check
  const leagueEntry = Object.entries(e.namedValues).find(([key]) =>
    key.toLowerCase().includes("please select the league you want to sign up for")
  );
  const timestampEntry = Object.entries(e.namedValues).find(([key]) =>
    key.toLowerCase().includes("timestamp")
  );

  // 🔍 DEBUGGING: Log each field lookup result
  Logger.log("🔍 Field lookup results:");
  Logger.log("  firstNameEntry: " + JSON.stringify(firstNameEntry));
  Logger.log("  emailEntry: " + JSON.stringify(emailEntry));
  Logger.log("  leagueEntry: " + JSON.stringify(leagueEntry));
  Logger.log("  timestampEntry: " + JSON.stringify(timestampEntry));

  const submittedFirstName = firstNameEntry?.[1]?.[0]?.trim().toLowerCase();
  // submittedEmail already defined above in testing mode check
  // For league/season, get the last non-empty value from the array
  const submittedLeague = leagueEntry?.[1]?.filter(val => val && val.trim()).pop()?.trim();
  const submittedTimestamp = new Date(timestampEntry?.[1]?.[0]);

  // 🔍 DEBUGGING: Log processed values
  Logger.log("📋 Processed form values:");
  Logger.log("  submittedFirstName: " + submittedFirstName);
  Logger.log("  submittedEmail: " + submittedEmail);
  Logger.log("  submittedLeague: " + submittedLeague);
  Logger.log("  submittedTimestamp: " + submittedTimestamp);
  Logger.log("  timestampEntry raw value: " + timestampEntry?.[1]?.[0]);
  Logger.log("  timestamp isValid: " + !isNaN(submittedTimestamp.getTime()));

  // 🔍 DEBUGGING: Check each required field individually
  const emailValid = !!submittedEmail;
  const leagueValid = !!submittedLeague;
  const timestampValid = !!submittedTimestamp && !isNaN(submittedTimestamp.getTime());
  
  Logger.log("✅ Field validation results:");
  Logger.log("  emailValid: " + emailValid);
  Logger.log("  leagueValid: " + leagueValid);
  Logger.log("  timestampValid: " + timestampValid);

  if (!emailValid || !leagueValid || !timestampValid) {
    Logger.log("❌ Missing submission data - validation failed");
    Logger.log("❌ Missing fields:", {
      email: !emailValid ? "MISSING" : "OK",
      league: !leagueValid ? "MISSING" : "OK", 
      timestamp: !timestampValid ? "MISSING" : "OK"
    });
    
    // 🔍 DEBUGGING: Show all available form field names for troubleshooting
    Logger.log("📝 All available form field names:");
    Object.keys(e.namedValues || {}).forEach(key => {
      Logger.log(`  "${key}": ${JSON.stringify(e.namedValues[key])}`);
    });
    
    return;
  }

  // 🔍 VALIDATION: Check if product exists and has no available inventory
  Logger.log("🔍 Validating product and inventory for league: " + submittedLeague);
  const productHandle = constructProductHandle(submittedLeague, sheet.getParent().getName());
  Logger.log("🔍 Constructed product handle: " + productHandle);
  const validationResult = validateProductAndInventory(productHandle);
  
  if (!validationResult.isValid) {
    Logger.log("❌ === VALIDATION FAILED ===");
    Logger.log("❌ Validation failed: " + validationResult.reason);
    Logger.log("📧 SENDING EMAIL NOTIFICATION TO jdazz87@gmail.com");
    
    // Send email notification instead of Slack
    Logger.log("📞 Calling sendValidationErrorEmailToAdmin...");
    const emailResult = sendValidationErrorEmailToAdmin(submittedLeague, submittedEmail, validationResult.reason, productHandle);
    Logger.log(`📧 Email notification result: ${emailResult}`);
    
    // Add canceled note to the row (we need to find the row first)
    Logger.log("📝 Adding canceled note to row...");
    addCanceledNoteToRow(e, submittedEmail, submittedLeague, validationResult.reason);
    
    Logger.log("🛑 VALIDATION FLOW COMPLETE - STOPPING PROCESSING (NO WAITLIST EMAIL SHOULD BE SENT)");
    return;
  }
  
  Logger.log("✅ Validation passed - proceeding with waitlist processing");

  const emailCol = header.findIndex(h => h.toLowerCase().includes("email address"));
  const leagueCol = header.findIndex(h => h.toLowerCase().includes("please select the league you want to sign up for"));
  const timestampCol = 0; // Timestamp is typically the first column
  const notesCol = header.findIndex(h => h.toLowerCase().includes("notes"));

  // 🔍 DEBUGGING: Log column mappings
  Logger.log("📊 Column mappings:");
  Logger.log("  emailCol: " + emailCol);
  Logger.log("  leagueCol: " + leagueCol);
  Logger.log("  timestampCol: " + timestampCol);
  Logger.log("  notesCol: " + notesCol);
  
  // 🔍 DEBUGGING: Show all headers with their indices
  Logger.log("📋 All column headers:");
  header.forEach((h, i) => {
    Logger.log("  Column " + i + ": \"" + h + "\"");
  });

  let foundRowIndex = -1;

  // Try to find the matching row
  for (let attempts = 0; attempts < 10; attempts++) {
    Logger.log(`🔄 Row matching attempt ${attempts + 1}/10`);
    
    // Re-fetch data in each attempt
    sheetData = sheet.getDataRange().getValues();
    Logger.log(`📏 Sheet has ${sheetData.length} total rows`);

    // Filter out rows with "Processed" or "Canceled" in Notes
    const filteredData = sheetData.filter((row, i) => {
      if (i === 0) return false; // skip header
      const notesVal = (row[notesCol] || "").toString().toLowerCase();
      return !(notesVal.includes("processed") || notesVal.includes("canceled"));
    });
    
    Logger.log(`📋 After filtering, ${filteredData.length} unprocessed rows to check`);

    for (let i = 0; i < filteredData.length; i++) {
      const row = filteredData[i];
      const rowEmail = row[emailCol]?.toString().trim().toLowerCase();
      const rowLeague = row[leagueCol]?.toString().trim();
      const rowTimestamp = new Date(row[timestampCol]);

      // 🔍 DEBUGGING: Log only first 2 rows and every 20th row to avoid spam
      // if (i < 2 || (i + 1) % 20 === 0) {
      //   Logger.log(`🔍 Checking row ${i + 1}:`);
      //   Logger.log(`  rowEmail: "${rowEmail}" vs submitted: "${submittedEmail}" → ${rowEmail === submittedEmail}`);
      //   Logger.log(`  rowLeague: "${rowLeague}" vs submitted: "${submittedLeague}" → ${rowLeague === submittedLeague}`);
      // }

      if (
        rowEmail === submittedEmail &&
        rowLeague === submittedLeague
      ) {
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
    } else {
      Logger.log(`❌ Attempt ${attempts + 1}: No match found in ${filteredData.length} rows`);
    }

    Utilities.sleep(1000); // Wait and retry
  }

  if (foundRowIndex === -1) {
    Logger.log("❌ Could not find matching row after 10 attempts.");
    Logger.log("❌ Final search criteria (email + league only):");
    Logger.log(`  submittedEmail: "${submittedEmail}"`);
    Logger.log(`  submittedLeague: "${submittedLeague}"`);
    Logger.log(`  submittedTimestamp: ${submittedTimestamp} (not used for matching)`);

    Logger.log("📧 === SENDING DEBUG EMAIL (Row Not Found) ===");
    Logger.log(`📧 Sending debug email to: ${DEBUG_EMAIL}`);
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: "❌ Waitlist Error - Row Not Found",
      htmlBody: `
        <p>Could not find matching row after form submission.</p>
        <p><strong>Email:</strong> ${submittedEmail}</p>
        <p><strong>League:</strong> ${submittedLeague}</p>
        <p><strong>Timestamp:</strong> ${submittedTimestamp.toISOString()}</p>
        <p><strong>namedValues:</strong></p>
        <pre>${JSON.stringify(e.namedValues, null, 2)}</pre>
      `
    });
    Logger.log("📧 Debug email sent successfully");

    return;
  }

  // Count how many earlier filtered entries exist for the same league
  const userTimestamp = new Date(sheetData[foundRowIndex][timestampCol]);
  Logger.log(`📊 Calculating waitlist position for user at row ${foundRowIndex} with timestamp ${userTimestamp}`);
  let earlierCount = 0;

  for (let i = 1; i < sheetData.length; i++) {
    const notesVal = (sheetData[i][notesCol] || "").toString().toLowerCase();
    if (notesVal.includes("processed") || notesVal.includes("canceled")) continue;

    const league = sheetData[i][leagueCol]?.toString().trim();
    const timestamp = new Date(sheetData[i][timestampCol]);

    if (league === submittedLeague && timestamp < userTimestamp) {
      earlierCount++;
    }
  }

  Logger.log(`📊 Waitlist calculation complete: ${earlierCount} people ahead, user is #${earlierCount + 1}`);

  const encodedEmail = encodeURIComponent(submittedEmail);
  const encodedLeague = encodeURIComponent(submittedLeague);
  const encodedTimestamp = encodeURIComponent(submittedTimestamp.toISOString());
  // Web app URL format: https://script.google.com/macros/s/DEPLOYMENT_ID/exec
  // You need to create a Web App deployment in Google Apps Script to get the correct URL
  // Direct link to waitlist checker - Interactive version for all leagues
  const baseUrl = 'https://script.google.com/macros/s/AKfycbzWqY_AvxEb1Q4qjWVVBV3epjF8QGL4Rw7YzDcuPEM3DyJZrtOvACOKY5T0wbzGd3R0Yg/exec';
  const spotCheckUrl = `${baseUrl}?email=${encodedEmail}&league=${encodedLeague}`;

  const barsLogoUrl = "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/122824_BARS_Logo_Full-Black.png?v=1741951481";
  const barsLogoBlob = UrlFetchApp
                      .fetch(barsLogoUrl)
                      .getBlob()
                      .setName("barsLogo");

  Logger.log("📧 === SENDING WAITLIST CONFIRMATION EMAIL ===");
  Logger.log(`📧 Sending waitlist email to: ${submittedEmail}`);
  Logger.log(`📧 Subject: 🏳️‍🌈 Your Waitlist Spot for Big Apple ${submittedLeague}`);
  Logger.log(`📧 Waitlist position: #${earlierCount + 1}`);
  
  MailApp.sendEmail({
    to: submittedEmail,
    replyTo: `${getSportEmailAlias(submittedLeague)}@bigapplerecsports.com`,
    subject: `🏳️‍🌈 Your Waitlist Spot for Big Apple ${submittedLeague}`,
    htmlBody: `
      <p>Hi ${submittedFirstName},</p>
      <p>Thanks for joining the waitlist for <strong>${submittedLeague}</strong>!</p>
      <p>You are currently <strong>#${earlierCount + 1}</strong> on the waitlist.</p>
      <p>We'll reach out if a spot opens up!</p>
      
      <div style="background-color: #e8f5e8; border: 2px solid #4CAF50; border-radius: 10px; padding: 20px; margin: 20px 0; text-align: center;">
        <h3 style="margin: 0 0 15px 0; color: #2e7d32;">🔍 Check Your Waitlist Position</h3>
        <p style="margin: 15px 0; color: #333;">View your position for <strong>${submittedLeague}</strong> and switch between all your leagues:</p>
        
        <a href="${spotCheckUrl}" style="display: inline-block; background: #4CAF50; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; margin: 10px 0;">Check Your Waitlist Position (#${earlierCount + 1})</a>
      </div>
      
      <div style="background-color: #ffebee; border: 2px solid #f44336; border-radius: 8px; padding: 15px; margin: 20px 0;">
        <p style="margin: 0; color: #d32f2f; font-weight: bold;">
          ⚠️ <strong>Important Note for Safari Users:</strong>
        </p>
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
  Logger.log(`📧 Emailed waitlist confirmation with spot #${earlierCount + 1}`);
  Logger.log(`🎉 processFormSubmit completed successfully`);
}

function getSportEmailAlias(league) {
  const lowerLeague = league.toLowerCase();
  
  if (lowerLeague.includes('basketball')) return 'basketball';
  if (lowerLeague.includes('volleyball')) return 'volleyball';
  if (lowerLeague.includes('soccer') || lowerLeague.includes('football')) return 'soccer';
  if (lowerLeague.includes('softball')) return 'softball';
  if (lowerLeague.includes('kickball')) return 'kickball';
  if (lowerLeague.includes('dodgeball')) return 'dodgeball';
  if (lowerLeague.includes('bowling')) return 'bowling';
  if (lowerLeague.includes('tennis')) return 'tennis';
  if (lowerLeague.includes('pickleball')) return 'pickleball';
  if (lowerLeague.includes('cornhole')) return 'cornhole';
  if (lowerLeague.includes('spikeball')) return 'spikeball';
  
  return 'info'; // Default fallback
}

/**
 * Constructs a Shopify product handle from league name and spreadsheet name
 * @param {string} league - The league name (e.g., "Kickball - Sunday - Open Division")
 * @param {string} spreadsheetName - The spreadsheet name (e.g., "Fall 2025 Waitlist (Responses)")
 * @returns {string} - The constructed handle (e.g., "2025-fall-kickball-sunday-opendiv")
 */
function constructProductHandle(league, spreadsheetName) {
  try {
    // Extract year and season from spreadsheet name
    // Expected format: "Fall 2025 Waitlist (Responses)" or "Spring 2024 Waitlist"
    const spreadsheetMatch = spreadsheetName.match(/(\w+)\s+(\d{4})/);
    if (!spreadsheetMatch) {
      throw new Error(`Could not extract season and year from spreadsheet name: ${spreadsheetName}`);
    }
    
    const season = spreadsheetMatch[1].toLowerCase(); // "fall"
    const year = spreadsheetMatch[2]; // "2025"
    
    // Parse league string: "Kickball - Sunday - Open Division"
    const leagueParts = league.split(' - ').map(part => part.trim());
    if (leagueParts.length < 3) {
      throw new Error(`League format not recognized: ${league}. Expected format: "Sport - Day - Division"`);
    }
    
    const sport = leagueParts[0].toLowerCase(); // "kickball"
    const day = leagueParts[1].toLowerCase(); // "sunday"
    const rawDivision = leagueParts[2]; // "Open Division"
    
    // Convert division to handle format: "Open Division" -> "opendiv"
    const division = rawDivision.split(' ')[0].replace('+', '').toLowerCase() + 'div';
    
    // Construct handle: "2025-fall-kickball-sunday-opendiv"
    const handle = `${year}-${season}-${sport}-${day}-${division}`;
    
    Logger.log(`🔗 Constructed handle: ${handle} from league: ${league}, spreadsheet: ${spreadsheetName}`);
    return handle;
    
  } catch (error) {
    Logger.log(`💥 Error constructing handle: ${error.message}`);
    // Fallback: create a simple handle from league name
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
 * Validates that a product exists for the handle and has no available inventory
 * @param {string} handle - The product handle to validate
 * @returns {Object} - {isValid: boolean, reason: string}
 */
function validateProductAndInventory(handle) {
  Logger.log("🚀 === STARTING PRODUCT VALIDATION ===");
  Logger.log(`🔍 Handle to validate: "${handle}"`);
  
  try {
    // Get product by handle from Shopify
    Logger.log("📞 Calling getProductByHandle...");
    const product = getProductByHandle(handle);
    Logger.log(`📦 getProductByHandle returned: ${JSON.stringify(product, null, 2)}`);
    
    if (!product) {
      Logger.log("❌ VALIDATION RESULT: No product found");
      Logger.log("🔔 This should trigger Slack notification (not email)");
      return {
        isValid: false,
        reason: "No product found for this league"
      };
    }
    
    Logger.log(`✅ Found product: ${product.title} (ID: ${product.id})`);
    
    // Get detailed product info with variants and inventory
    Logger.log("📞 Calling getProductWithVariants...");
    const productWithVariants = getProductWithVariants(product.id);
    Logger.log(`📦 getProductWithVariants returned: ${JSON.stringify(productWithVariants, null, 2)}`);
    
    if (!productWithVariants || !productWithVariants.variants || productWithVariants.variants.length === 0) {
      Logger.log("❌ VALIDATION RESULT: Product has no variants");
      Logger.log("🔔 This should trigger Slack notification (not email)");
      return {
        isValid: false,
        reason: "Product has no variants"
      };
    }
    
    Logger.log(`🔍 Checking inventory for ${productWithVariants.variants.length} variants`);
    
    let nonWaitlistVariants = 0;
    let availableInventory = 0;
    
    // Check each variant for available inventory (excluding waitlist variants)
    for (const variant of productWithVariants.variants) {
      const variantTitle = (variant.title || '').toLowerCase();
      Logger.log(`🔍 Checking variant: "${variant.title}" (inventory: ${variant.inventoryQuantity})`);
      
      // Skip waitlist variants
      if (variantTitle.includes('waitlist')) {
        Logger.log(`⏭️ Skipping waitlist variant: ${variant.title}`);
        continue;
      }
      
      nonWaitlistVariants++;
      Logger.log(`✓ Non-waitlist variant found: ${variant.title}`);
      
      // Check if this variant has available inventory
      if (variant.inventoryQuantity > 0) {
        availableInventory += variant.inventoryQuantity;
        Logger.log(`❌ Found available inventory: ${variant.title} (${variant.inventoryQuantity} available)`);
        Logger.log("🔔 This should trigger Slack notification (not email)");
        return {
          isValid: false,
          reason: "There are still spots available for this league"
        };
      } else {
        Logger.log(`✓ Variant sold out: ${variant.title} (${variant.inventoryQuantity})`);
      }
    }
    
    Logger.log(`📊 Summary: ${nonWaitlistVariants} non-waitlist variants, ${availableInventory} total available inventory`);
    Logger.log("✅ All non-waitlist variants are sold out - waitlist is valid");
    Logger.log("🎉 VALIDATION RESULT: Passed - proceeding with waitlist");
    return {
      isValid: true,
      reason: "Validation passed"
    };
    
  } catch (error) {
    Logger.log("💥 ERROR during validation: " + error.message);
    Logger.log("📍 Error stack: " + error.stack);
    Logger.log("🔄 Allowing submission to proceed due to technical error");
    // If there's an error checking Shopify, allow the waitlist submission to proceed
    // This prevents the system from breaking if Shopify is temporarily unavailable
    return {
      isValid: true,
      reason: "Validation skipped due to technical error"
    };
  } finally {
    Logger.log("🏁 === PRODUCT VALIDATION COMPLETE ===");
  }
}


/**
 * Adds a canceled note to the submitted row
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
      Logger.log("❌ Could not find notes column to add cancellation note");
      return;
    }
    
    // Find the row that matches this submission
    for (let i = 1; i < sheetData.length; i++) {
      const rowEmail = sheetData[i][emailCol]?.toString().trim().toLowerCase();
      const rowLeague = sheetData[i][leagueCol]?.toString().trim();
      
      if (rowEmail === email.toLowerCase() && rowLeague === league) {
        // Add cancellation note
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
 * Sends validation error email to admin when product validation fails
 * @param {string} league - League name
 * @param {string} userEmail - User email who submitted
 * @param {string} reason - Validation failure reason
 * @param {string} productHandle - Product handle that was checked
 * @returns {boolean} - True if email sent successfully
 */
function sendValidationErrorEmailToAdmin(league, userEmail, reason, productHandle) {
  try {
    Logger.log("📧 === SENDING ADMIN VALIDATION ERROR EMAIL ===");
    Logger.log(`📧 To: jdazz87@gmail.com`);
    Logger.log(`📧 Reason: ${reason}`);
    Logger.log(`📧 Handle: ${productHandle}`);
    
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
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold; width: 30%;">Error Type:</td>
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
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><code style="background: #f8f9fa; padding: 2px 4px; border-radius: 4px;">${productHandle}</code></td>
            </tr>
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Reason:</td>
              <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">${reason}</td>
            </tr>
            <tr>
              <td style="padding: 8px; font-weight: bold;">Timestamp:</td>
              <td style="padding: 8px;">${new Date().toLocaleString()}</td>
            </tr>
          </table>
        </div>
        
        <div style="background: #e9ecef; padding: 15px; border-radius: 8px; margin-top: 20px;">
          <h4 style="margin: 0 0 10px 0; color: #495057;">Next Steps:</h4>
          <ul style="margin: 0; padding-left: 20px;">
            ${reason.includes("No product found") ? 
              `<li>Check if the product exists in Shopify with handle: <code>${productHandle}</code></li>
               <li>Verify the product is published and active</li>
               <li>Check if the handle construction logic is correct</li>` :
              `<li>Check inventory levels for the product in Shopify</li>
               <li>Verify if spots should actually be available for registration</li>
               <li>Consider if the waitlist should be paused</li>`
            }
            <li><strong>User has NOT been added to the waitlist</strong></li>
            <li>Row has been marked as "Canceled" in the spreadsheet</li>
          </ul>
        </div>
        
        <div style="margin-top: 20px; padding: 10px; background: #f8f9fa; border-radius: 4px; font-size: 12px; color: #6c757d;">
          🤖 This is an automated message from the Waitlist Script validation system.
        </div>
      </div>
    `;

    MailApp.sendEmail({
      to: "jdazz87@gmail.com",
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
