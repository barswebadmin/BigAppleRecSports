/**
 * Handle POST request to check waitlist position
 * Called by doPost router when email + league + productUrl are provided
 */

function handleCheckWaitlistPosition(payload) {
  const debugInfo = [];
  
  try {
    debugInfo.push("🚀 handleCheckWaitlistPosition called");
    debugInfo.push(`📦 Payload: ${JSON.stringify(payload)}`);
    
    const { email, league, productUrl } = payload;
    
    if (!email || !league || !productUrl) {
      const missingParams = [];
      if (!email) missingParams.push("email");
      if (!league) missingParams.push("league");
      if (!productUrl) missingParams.push("productUrl");
      
      debugInfo.push(`❌ Missing required parameters: ${missingParams.join(", ")}`);
      
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: "🔍 Check Waitlist Position - Missing Parameters",
        body: debugInfo.join('\n')
      });
      
      return createErrorResponse({
        success: false,
        error: `Missing required parameters: ${missingParams.join(", ")}`,
        required: ["email", "league", "productUrl"]
      });
    }
    
    debugInfo.push(`📧 Email: ${email}`);
    debugInfo.push(`🏆 League: ${league}`);
    debugInfo.push(`🔗 Product URL: ${productUrl}`);
    
    // Extract product ID or handle from URL
    debugInfo.push("🔍 Extracting product identifier from URL...");
    const productId = extractProductIdFromUrl(productUrl);
    const productHandle = extractProductHandleFromUrl(productUrl);
    
    debugInfo.push(`🆔 Extracted product ID: ${productId}`);
    debugInfo.push(`🏷️ Extracted handle: ${productHandle}`);
    
    if (!productId && !productHandle) {
      debugInfo.push("❌ Could not extract product ID or handle from URL");
      
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: "🔍 Check Waitlist Position - Invalid Product URL",
        body: debugInfo.join('\n')
      });
      
      return createErrorResponse({
        success: false,
        error: "Could not extract product ID or handle from URL",
        productUrl: productUrl
      });
    }
    
    // Validate product and inventory
    debugInfo.push("🔍 Validating product and inventory...");
    let validationResult;
    
    if (productId) {
      debugInfo.push("📦 Using product ID for validation...");
      validationResult = validateProductAndInventoryById(productId);
    } else {
      debugInfo.push("🏷️ Using product handle for validation...");
      validationResult = validateProductAndInventory(productHandle);
    }
    
    debugInfo.push(`✅ Validation result: ${JSON.stringify(validationResult)}`);
    
    if (validationResult.isValid) {
      // Product is sold out, check waitlist spot
      debugInfo.push("✅ Product is sold out, checking waitlist spot...");
      
      const waitlistResult = getWaitlistSpot(email, league);
      debugInfo.push(`📊 Waitlist result: ${JSON.stringify(waitlistResult)}`);
      
      if (waitlistResult.found) {
        // Send waitlist confirmation email to the user
        debugInfo.push("📧 Sending waitlist confirmation email to user...");
        const emailSent = sendWaitlistConfirmationEmail(email, league, waitlistResult.spot);
        debugInfo.push(`📧 Email sent: ${emailSent}`);
        
        const response = {
          success: true,
          productSoldOut: true,
          waitlistSpot: waitlistResult.spot,
          emailSent: emailSent,
          message: `You are #${waitlistResult.spot} on the waitlist for ${league}. Confirmation email sent to ${email}.`
        };
        
        debugInfo.push("✅ Returning successful waitlist response");
        
        MailApp.sendEmail({
          to: DEBUG_EMAIL,
          subject: "🔍 Check Waitlist Position - Success",
          body: debugInfo.join('\n') + '\n\nResponse: ' + JSON.stringify(response, null, 2)
        });
        
        return createSuccessResponse(response);
        
      } else {
        debugInfo.push("❌ Failed to get waitlist spot - not found in spreadsheet");
        
        MailApp.sendEmail({
          to: DEBUG_EMAIL,
          subject: "🔍 Check Waitlist Position - Not Found",
          body: debugInfo.join('\n')
        });
        
        return createErrorResponse({
          success: false,
          productSoldOut: true,
          error: "Could not find waitlist position",
          details: "Email and league combination not found in waitlist spreadsheet"
        });
      }
      
    } else {
      // Product has inventory available or doesn't exist
      debugInfo.push("⚠️ Product validation failed - inventory available or product not found");
      
      const response = {
        success: true,
        productSoldOut: false,
        reason: validationResult.reason,
        message: validationResult.reason.includes("No product found")
          ? "Product not found - please check the URL"
          : "This product still has available spots - no waitlist needed"
      };
      
      debugInfo.push("✅ Returning product validation response");
      
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: "🔍 Check Waitlist Position - Product Not Sold Out",
        body: debugInfo.join('\n') + '\n\nResponse: ' + JSON.stringify(response, null, 2)
      });
      
      return createSuccessResponse(response);
    }
    
  } catch (error) {
    debugInfo.push(`💥 Error in handleCheckWaitlistPosition: ${error.message}`);
    debugInfo.push(`Stack trace: ${error.stack}`);
    
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: "🔍 Check Waitlist Position - System Error",
      body: debugInfo.join('\n')
    });
    
    return createErrorResponse({
      success: false,
      error: "Internal server error",
      details: error.message
    });
  }
}

/**
 * Get waitlist spot for email + league combination
 * Searches the active spreadsheet for the matching row
 */
function getWaitlistSpot(email, league) {
  try {
    Logger.log(`🔍 Getting waitlist spot for email: ${email}, league: ${league}`);
    
    const sheet = getSheet();
    const dataRange = sheet.getDataRange();
    const values = dataRange.getValues();
    const backgrounds = dataRange.getBackgrounds();
    const headers = values[0];
    const dataRows = values.slice(1);
    const backgroundRows = backgrounds.slice(1);
    
    Logger.log(`📊 Found ${dataRows.length} total rows`);
    
    // Find column indices
    const emailCol = headers.findIndex(h => h.toLowerCase().includes("email address"));
    const leagueCol = headers.findIndex(h => h.toLowerCase().includes("please select the league you want to sign up for"));
    const notesCol = headers.findIndex(h => h.toLowerCase().includes("notes"));
    
    if (emailCol === -1 || leagueCol === -1) {
      Logger.log(`❌ Required columns not found. Email col: ${emailCol}, League col: ${leagueCol}`);
      return { found: false };
    }
    
    Logger.log(`📍 Column indices - Email: ${emailCol}, League: ${leagueCol}, Notes: ${notesCol}`);
    
    // Find matching email + league
    let position = 0;
    let foundRow = null;
    
    for (let i = 0; i < dataRows.length; i++) {
      const row = dataRows[i];
      const rowEmail = (row[emailCol] || '').toString().trim().toLowerCase();
      const rowLeague = (row[leagueCol] || '').toString().trim();
      const rowNotes = notesCol !== -1 ? (row[notesCol] || '').toString().trim().toLowerCase() : '';
      const rowBackgrounds = backgroundRows[i];
      
      // Skip if row has any cell with a background color (not white/default)
      const hasBackgroundColor = rowBackgrounds.some(bg => {
        const bgLower = (bg || '').toLowerCase();
        return bgLower && bgLower !== '#ffffff' && bgLower !== '#fff' && bgLower !== 'white';
      });
      
      if (hasBackgroundColor) {
        Logger.log(`⏭️ Skipping row ${i + 2} - has background color`);
        continue;
      }
      
      // Skip if row is marked as "Processed", "Canceled", or "Done"
      if (rowNotes.includes('process') || rowNotes.includes('cancel') || rowNotes.includes('done')) {
        Logger.log(`⏭️ Skipping row ${i + 2} - notes contain: ${rowNotes}`);
        continue;
      }
      
      // If league matches, increment position
      if (rowLeague === league) {
        position++;
        
        // Check if this is our email
        if (rowEmail === email.toLowerCase()) {
          foundRow = { row: i + 2, position }; // +2 for 1-indexed and header row
          break;
        }
      }
    }
    
    if (foundRow) {
      Logger.log(`✅ Found waitlist spot: #${foundRow.position} (row ${foundRow.row})`);
      return { found: true, spot: foundRow.position };
    } else {
      Logger.log(`❌ Email not found on waitlist for league: ${league}`);
      return { found: false };
    }
    
  } catch (error) {
    Logger.log(`💥 Error in getWaitlistSpot: ${error.message}`);
    return { found: false, error: error.message };
  }
}

