/**
 * Handle POST requests to check waitlist spots
 * Expected parameters: email, league, productUrl
 */
function doPost(e) {
  let debugInfo = [];

  try {
    debugInfo.push("🚀 doPost function called");
    debugInfo.push("📥 POST data received: " + JSON.stringify(e.postData));

    // Parse JSON body if it exists
    let parameters = {};

    // Debug: Log the entire e object structure
    debugInfo.push("📦 Complete e object: " + JSON.stringify({
      postData: e.postData,
      parameter: e.parameter,
      contentLength: e.contentLength,
      queryString: e.queryString
    }));

    if (e.postData && e.postData.contents) {
      debugInfo.push("📥 Raw postData.contents: " + e.postData.contents);
      debugInfo.push("📥 postData.type: " + e.postData.type);

      try {
        // Handle different content types
        let rawContent = e.postData.contents;

        // If content is URL-encoded, decode it first
        if (e.postData.type === 'application/x-www-form-urlencoded') {
          // Handle form-encoded data that might contain JSON
          if (rawContent.startsWith('payload=')) {
            rawContent = decodeURIComponent(rawContent.slice('payload='.length));
          } else {
            // Try to parse as URL-encoded parameters
            const urlParams = new URLSearchParams(rawContent);
            parameters = {};
            for (const [key, value] of urlParams) {
              parameters[key] = value;
            }
            debugInfo.push("📦 Parsed URL-encoded parameters: " + JSON.stringify(parameters));
          }
        }

        // Try to parse as JSON
        if (Object.keys(parameters).length === 0) {
          parameters = JSON.parse(rawContent);
          debugInfo.push("📦 Parsed JSON parameters: " + JSON.stringify(parameters));
        }

      } catch (error) {
        debugInfo.push("❌ Failed to parse POST data: " + error.message);
        debugInfo.push("❌ Raw content was: " + e.postData.contents);

        // Send debug email before returning error
        MailApp.sendEmail({
          to: "jdazz87@gmail.com",
          subject: "🔍 doPost Debug - JSON Parse Error",
          body: debugInfo.join('\n')
        });

        return ContentService
          .createTextOutput(JSON.stringify({
            success: false,
            error: "Invalid JSON in request body",
            debug: {
              contentType: e.postData.type,
              rawContent: e.postData.contents,
              errorMessage: error.message
            }
          }))
          .setMimeType(ContentService.MimeType.JSON);
      }
    } else {
      // Fallback to URL parameters if no JSON body
      parameters = e.parameter || {};
      debugInfo.push("📦 Using URL parameters: " + JSON.stringify(parameters));
    }

    // Extract required parameters
    const email = parameters.email;
    const league = parameters.league;
    const productUrl = parameters.productUrl;

    debugInfo.push(`📧 Email: ${email}`);
    debugInfo.push(`🏆 League: ${league}`);
    debugInfo.push(`🔗 Product URL: ${productUrl}`);

    // Validate required parameters
    if (!email || !league || !productUrl) {
      const missingParams = [];
      if (!email) missingParams.push("email");
      if (!league) missingParams.push("league");
      if (!productUrl) missingParams.push("productUrl");

      debugInfo.push(`❌ Missing required parameters: ${missingParams.join(", ")}`);

      MailApp.sendEmail({
        to: "jdazz87@gmail.com",
        subject: "🔍 doPost Debug - Missing Parameters",
        body: debugInfo.join('\n')
      });

      return ContentService
        .createTextOutput(JSON.stringify({
          success: false,
          error: `Missing required parameters: ${missingParams.join(", ")}`,
          required: ["email", "league", "productUrl"]
        }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // Extract product ID or handle from URL
    debugInfo.push("🔍 Extracting product identifier from URL...");
    const productId = extractProductIdFromUrl(productUrl);
    const productHandle = extractProductHandleFromUrl(productUrl);

    debugInfo.push(`🆔 Extracted product ID: ${productId}`);
    debugInfo.push(`🏷️ Extracted handle: ${productHandle}`);

    if (!productId && !productHandle) {
      debugInfo.push("❌ Could not extract product ID or handle from URL");

      MailApp.sendEmail({
        to: "jdazz87@gmail.com",
        subject: "🔍 doPost Debug - Invalid Product URL",
        body: debugInfo.join('\n')
      });

      return ContentService
        .createTextOutput(JSON.stringify({
          success: false,
          error: "Could not extract product ID or handle from URL",
          productUrl: productUrl
        }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // Validate product and inventory using ID or handle
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

      const waitlistResult = getWaitlistSpot(email, league, null, []);
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
          to: "jdazz87@gmail.com",
          subject: "🔍 doPost Debug - Success",
          body: debugInfo.join('\n') + '\n\nResponse: ' + JSON.stringify(response, null, 2)
        });

        return ContentService
          .createTextOutput(JSON.stringify(response))
          .setMimeType(ContentService.MimeType.JSON);

      } else {
        debugInfo.push("❌ Failed to get waitlist spot - not found in spreadsheet");

        MailApp.sendEmail({
          to: "jdazz87@gmail.com",
          subject: "🔍 doPost Debug - Waitlist Error",
          body: debugInfo.join('\n')
        });

        return ContentService
          .createTextOutput(JSON.stringify({
            success: false,
            productSoldOut: true,
            error: "Could not find waitlist position",
            details: "Email and league combination not found in waitlist spreadsheet"
          }))
          .setMimeType(ContentService.MimeType.JSON);
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
        to: "jdazz87@gmail.com",
        subject: "🔍 doPost Debug - Product Not Sold Out",
        body: debugInfo.join('\n') + '\n\nResponse: ' + JSON.stringify(response, null, 2)
      });

      return ContentService
        .createTextOutput(JSON.stringify(response))
        .setMimeType(ContentService.MimeType.JSON);
    }

  } catch (error) {
    debugInfo.push(`💥 Error in doPost: ${error.message}`);
    debugInfo.push(`Stack trace: ${error.stack}`);

    MailApp.sendEmail({
      to: "jdazz87@gmail.com",
      subject: "🔍 doPost Debug - System Error",
      body: debugInfo.join('\n')
    });

    return ContentService
      .createTextOutput(JSON.stringify({
        success: false,
        error: "Internal server error",
        details: error.message
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Extract product ID from Shopify admin or API URLs
 * Supports various Shopify URL formats with product IDs
 */
function extractProductIdFromUrl(productUrl) {
  if (!productUrl || typeof productUrl !== 'string') {
    return null;
  }

  try {
    // Remove query parameters and fragments
    const cleanUrl = productUrl.split('?')[0].split('#')[0];

    // Extract product ID from various Shopify URL patterns:
    // https://admin.shopify.com/store/store-name/products/1234567890
    // https://store-name.myshopify.com/admin/products/1234567890
    // https://shopify.com/admin/products/1234567890/variants/9876543210

    const patterns = [
      /\/products\/(\d+)(?:\/|$)/,           // /products/1234567890 or /products/1234567890/
      /\/admin\/products\/(\d+)(?:\/|$)/,    // /admin/products/1234567890
    ];

    for (const pattern of patterns) {
      const match = cleanUrl.match(pattern);
      if (match && match[1]) {
        // Return as GraphQL ID format
        return `gid://shopify/Product/${match[1]}`;
      }
    }

    return null;

  } catch (error) {
    Logger.log(`Error extracting product ID from URL: ${error.message}`);
    return null;
  }
}

/**
 * Extract product handle from Shopify product URL
 * Supports various Shopify URL formats
 */
function extractProductHandleFromUrl(productUrl) {
  if (!productUrl || typeof productUrl !== 'string') {
    return null;
  }

  try {
    // Remove query parameters and fragments
    const cleanUrl = productUrl.split('?')[0].split('#')[0];

    // Extract handle from various Shopify URL patterns:
    // https://domain.com/products/handle
    // https://domain.com/products/handle/
    // https://domain.com/collections/collection-name/products/handle

    const patterns = [
      /\/products\/([^\/]+)\/?$/,           // /products/handle or /products/handle/
      /\/products\/([^\/]+)\/$/,            // /products/handle/
      /\/collections\/[^\/]+\/products\/([^\/]+)\/?$/ // /collections/collection/products/handle
    ];

    for (const pattern of patterns) {
      const match = cleanUrl.match(pattern);
      if (match && match[1]) {
        // Make sure it's not a numeric ID (which would be caught by extractProductIdFromUrl)
        if (!/^\d+$/.test(match[1])) {
          return match[1];
        }
      }
    }

    return null;

  } catch (error) {
    Logger.log(`Error extracting product handle from URL: ${error.message}`);
    return null;
  }
}

/**
 * Send waitlist confirmation email to user (same as during form submission)
 */
function sendWaitlistConfirmationEmail(email, league, waitlistSpot) {
  try {
    Logger.log("📧 === SENDING WAITLIST CONFIRMATION EMAIL (from doPost) ===");
    Logger.log(`📧 Sending waitlist email to: ${email}`);
    Logger.log(`📧 League: ${league}`);
    Logger.log(`📧 Waitlist position: #${waitlistSpot}`);

    // Extract first name from email (fallback if we don't have it)
    const firstName = email.split('@')[0].split('.')[0];
    const capitalizedFirstName = firstName.charAt(0).toUpperCase() + firstName.slice(1);

    // Generate spot check URL using known working deployment
    const encodedEmail = encodeURIComponent(email);
    const encodedLeague = encodeURIComponent(league);
    // Use known working web app URL directly
    // ScriptApp.getService().getUrl() is unreliable and returns null even when deployment works
    const baseUrl = WAITLIST_WEB_APP_URL;
    Logger.log(`📍 Using web app URL: ${baseUrl}`);

    const spotCheckUrl = `${baseUrl}?email=${encodedEmail}&league=${encodedLeague}`;

    // Get BARS logo
    const barsLogoBlob = UrlFetchApp
                        .fetch(BARS_LOGO_URL)
                        .getBlob()
                        .setName("barsLogo");

    // Get sport email alias for reply-to
    const replyToEmail = `${getSportEmailAlias(league)}@bigapplerecsports.com`;

    const subject = `🏳️‍🌈 Your Waitlist Spot for Big Apple ${league}`;

    const htmlBody = `
      <p>Hi ${capitalizedFirstName},</p>
      <p>Thanks for joining the waitlist for <strong>${league}</strong>!</p>
      <p>You are currently <strong>#${waitlistSpot}</strong> on the waitlist.</p>
      <p>We'll reach out if a spot opens up!</p>

      <div style="background-color: #e8f5e8; border: 2px solid #4CAF50; border-radius: 10px; padding: 20px; margin: 20px 0; text-align: center;">
        <h3 style="margin: 0 0 15px 0; color: #2e7d32;">🔍 Check Your Waitlist Position</h3>
        <p style="margin: 15px 0; color: #333;">View your position for <strong>${league}</strong> and switch between all your leagues:</p>

        <a href="${spotCheckUrl}" style="display: inline-block; background: #4CAF50; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; margin: 10px 0;">Check Your Waitlist Position (#${waitlistSpot})</a>
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

      <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
        <p><strong>Big Apple Rec Sports</strong><br>
        Follow us: <a href="https://www.instagram.com/bigapplerecsports/">Instagram</a> | <a href="https://www.facebook.com/groups/bigapplerecsports">Facebook</a></p>
        <img src="cid:barsLogo" style="width:225px; height:auto; margin-top: 15px;">
      </div>
    `;

    MailApp.sendEmail({
      to: email,
      replyTo: replyToEmail,
      subject: subject,
      htmlBody: htmlBody,
      inlineImages: { barsLogo: barsLogoBlob }
    });

    Logger.log("✅ Waitlist confirmation email sent successfully");
    return true;

  } catch (error) {
    Logger.log(`💥 Error sending waitlist confirmation email: ${error.message}`);
    return false;
  }
}

/**
 * Validate product and inventory using product ID instead of handle
 */
function validateProductAndInventoryById(productId) {
  Logger.log("🚀 === STARTING PRODUCT VALIDATION BY ID ===");
  Logger.log(`🔍 Product ID to validate: "${productId}"`);

  try {
    // Get product by ID from Shopify using GraphQL
    Logger.log("📞 Calling getProductWithVariants with product ID...");
    const productWithVariants = getProductWithVariants(productId);
    Logger.log(`📦 getProductWithVariants returned: ${JSON.stringify(productWithVariants, null, 2)}`);

    if (!productWithVariants) {
      Logger.log("❌ VALIDATION RESULT: No product found");
      return {
        isValid: false,
        reason: "No product found for this product ID"
      };
    }

    Logger.log(`✅ Found product: ${productWithVariants.title} (ID: ${productWithVariants.id})`);

    if (!productWithVariants.variants || productWithVariants.variants.length === 0) {
      Logger.log("❌ VALIDATION RESULT: Product has no variants");
      return {
        isValid: false,
        reason: "Product has no variants"
      };
    }

    // Check if any non-waitlist variants have inventory available
    let hasAvailableInventory = false;
    let totalNonWaitlistInventory = 0;

    for (const variant of productWithVariants.variants) {
      const title = (variant.title || '').toLowerCase();
      const isWaitlistVariant = title.includes('waitlist');

      if (!isWaitlistVariant) {
        const inventory = variant.inventoryQuantity || 0;
        totalNonWaitlistInventory += inventory;
        if (inventory > 0) {
          hasAvailableInventory = true;
        }

        Logger.log(`📦 Variant: "${variant.title}" - Inventory: ${inventory} (Waitlist: ${isWaitlistVariant})`);
      }
    }

    Logger.log(`📊 Total non-waitlist inventory: ${totalNonWaitlistInventory}`);
    Logger.log(`💰 Has available inventory: ${hasAvailableInventory}`);

    if (hasAvailableInventory) {
      Logger.log("❌ VALIDATION RESULT: Inventory still available");
      return {
        isValid: false,
        reason: "There are still spots available for this league"
      };
    }

    Logger.log("✅ VALIDATION RESULT: Product is sold out (excluding waitlist variants)");
    return {
      isValid: true,
      reason: "Product is sold out"
    };

  } catch (error) {
    Logger.log(`💥 Error validating product by ID: ${error.message}`);
    return {
      isValid: false,
      reason: `Validation error: ${error.message}`
    };
  }
}

function doGet(e) {
  let debugInfo = [];

  try {
    debugInfo.push("🚀 doGet function called (Interactive Dropdown Version)");
    debugInfo.push("📥 Parameters received: " + JSON.stringify(e.parameter));
    debugInfo.push("📥 ALL parameters: " + JSON.stringify(e, null, 2));

    // Extract parameters
    const email = e.parameter.email;
    const selectedLeague = e.parameter.league; // This might be the initially selected league

    debugInfo.push(`📧 Email: ${email}`);
    debugInfo.push(`🏆 Initially Selected League: ${selectedLeague}`);

    // Validate email parameter
    if (!email) {
      debugInfo.push("❌ Missing email parameter");

      MailApp.sendEmail({
        to: "jdazz87@gmail.com",
        subject: "🔍 doGet Debug - Missing Email",
        body: debugInfo.join('\n')
      });

      return createErrorPage("Missing Information",
        "Email address is required to check waitlist positions.");
    }

    debugInfo.push("🔍 Calling getAllLeaguesForEmail...");

    // Get all leagues for this email
    const result = getAllLeaguesForEmail(email);
    debugInfo.push(...result.debugLog);

    if (result.error) {
      debugInfo.push(`❌ Error getting leagues: ${result.error}`);

      MailApp.sendEmail({
        to: "jdazz87@gmail.com",
        subject: "🔍 doGet Debug - Error Getting Leagues",
        body: debugInfo.join('\n')
      });

      return createErrorPage("System Error",
        `An error occurred: ${result.error}`);
    }

    if (!result.leagues || result.leagues.length === 0) {
      debugInfo.push("❌ No leagues found for this email");

      MailApp.sendEmail({
        to: "jdazz87@gmail.com",
        subject: "🔍 doGet Debug - No Leagues Found",
        body: debugInfo.join('\n')
      });

      return createErrorPage("Not Found",
        "We couldn't find any waitlist submissions for this email address.",
        [`Email: ${email}`]);
    }

    debugInfo.push(`✅ Found ${result.leagues.length} leagues for email`);
    result.leagues.forEach(league => {
      debugInfo.push(`   - ${league.league}: Position #${league.spot}`);
    });

    // Create interactive success page with dropdown
    return createInteractiveSuccessPage(result.leagues, email, selectedLeague);

  } catch (error) {
    debugInfo.push("💥 Error in doGet: " + error.message);
    debugInfo.push("📍 Error stack: " + error.stack);

    MailApp.sendEmail({
      to: "jdazz87@gmail.com",
      subject: "🔍 doGet Debug - ERROR",
      body: debugInfo.join('\n')
    });

    return createErrorPage("System Error",
      "An error occurred while checking your waitlist positions.",
      [`Error: ${error.message}`]);
  }
}



function createErrorPage(title, message, details = []) {
  const detailsHtml = details.length > 0 ?
    `<div class="details"><ul>${details.map(d => `<li>${d}</li>`).join('')}</ul></div>` : '';

  return HtmlService.createHtmlOutput(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Waitlist Check - BARS</title>
        <style>
            body {
                margin: 0;
                padding: 20px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #ff7043 0%, #ff5722 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                max-width: 600px;
                background: white;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 2.2em;
                font-weight: 600;
            }
            .content {
                padding: 30px;
                text-align: center;
            }
            .error-icon {
                font-size: 4em;
                margin-bottom: 20px;
                color: #f44336;
            }
            .message {
                font-size: 1.2em;
                color: #555;
                margin: 20px 0;
                line-height: 1.5;
            }
            .details {
                background: #f5f5f5;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: left;
            }
            .details ul {
                margin: 0;
                padding-left: 20px;
            }
            .details li {
                margin: 8px 0;
                color: #666;
            }
            .footer {
                background: #d32f2f;
                color: white;
                padding: 20px 30px;
                text-align: center;
            }
            .footer a {
                color: #ffcdd2;
                text-decoration: none;
                font-weight: 600;
                padding: 10px 20px;
                background: rgba(255,255,255,0.1);
                border-radius: 5px;
                display: inline-block;
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚠️ ${title}</h1>
            </div>
            <div class="content">
                <div class="error-icon">❌</div>
                <div class="message">${message}</div>
                ${detailsHtml}
            </div>
            <div class="footer">
                <p>Need help? Contact our support team:</p>
                <a href="mailto:info@bigapplerecsports.com">📧 Contact Support</a>
            </div>
        </div>
    </body>
    </html>
  `);
}
function createInteractiveSuccessPage(leagues, email, selectedLeague) {
  // Sort leagues alphabetically
  leagues.sort((a, b) => a.league.localeCompare(b.league));

  // Determine which league to show initially
  let initialLeague = leagues[0];
  if (selectedLeague) {
    const found = leagues.find(l => l.league.toLowerCase() === selectedLeague.toLowerCase());
    if (found) initialLeague = found;
  }

  // Generate options HTML
  const optionsHtml = leagues.map(league =>
    `<option value="${league.league}" data-spot="${league.spot}" ${league.league === initialLeague.league ? 'selected' : ''}>${league.league}</option>`
  ).join('');

  return HtmlService.createHtmlOutput(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your Waitlist Positions - BARS</title>
        <style>
            body {
                margin: 0;
                padding: 20px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                max-width: 700px;
                background: white;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 2.2em;
                font-weight: 600;
            }
            .selector-section {
                padding: 30px;
                background: #f8fffe;
                border-bottom: 1px solid #e0e0e0;
            }
            .league-selector {
                width: 100%;
                padding: 15px;
                font-size: 1.1em;
                border: 2px solid #4CAF50;
                border-radius: 10px;
                background: white;
                margin-bottom: 20px;
            }
            .league-selector:focus {
                outline: none;
                border-color: #45a049;
                box-shadow: 0 0 10px rgba(76, 175, 80, 0.3);
            }
            .position-display {
                text-align: center;
                padding: 40px 30px;
                background: #f8fffe;
            }
            .position-circle {
                width: 120px;
                height: 120px;
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 2.5em;
                font-weight: bold;
                margin: 0 auto 20px;
                box-shadow: 0 5px 15px rgba(76, 175, 80, 0.3);
                transition: all 0.3s ease;
            }
            .position-text {
                font-size: 1.4em;
                color: #2e7d32;
                margin: 20px 0;
                font-weight: 500;
            }
            .current-league {
                font-size: 1.2em;
                color: #333;
                margin: 15px 0;
                font-weight: 600;
            }
            .details {
                background: #f5f5f5;
                padding: 25px 30px;
                border-top: 1px solid #e0e0e0;
            }
            .detail-item {
                margin: 12px 0;
                color: #555;
                font-size: 1.1em;
            }
            .detail-label {
                font-weight: 600;
                color: #333;
            }
            .footer {
                background: #2e7d32;
                color: white;
                padding: 20px 30px;
                text-align: center;
                font-size: 0.95em;
            }
            .footer a {
                color: #81c784;
                text-decoration: none;
            }
            .league-count {
                background: #e8f5e8;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
                color: #2e7d32;
                font-weight: 600;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Your Waitlist Positions</h1>
            </div>

            <div class="selector-section">
                <div class="league-count">
                    📊 You're on the waitlist for ${leagues.length} league${leagues.length > 1 ? 's' : ''}
                </div>
                <label for="leagueSelector" style="font-weight: 600; color: #333; display: block; margin-bottom: 10px;">
                    🏆 Select a league to view your position:
                </label>
                <select id="leagueSelector" class="league-selector">
                    ${optionsHtml}
                </select>
            </div>

            <div class="position-display">
                <div class="position-circle" id="positionCircle">#${initialLeague.spot}</div>
                <div class="current-league" id="currentLeague">${initialLeague.league}</div>
                <div class="position-text" id="positionText">
                    You are <strong>#${initialLeague.spot}</strong> on the waitlist
                </div>
                <p style="color: #666; margin-top: 20px;">
                    📧 We'll reach out if a spot opens up!
                </p>
            </div>

            <div class="details">
                <div class="detail-item">
                    <span class="detail-label">📧 Email:</span> ${email}
                </div>
                <div class="detail-item">
                    <span class="detail-label">⏰ Checked:</span> ${new Date().toLocaleString()}
                </div>
            </div>

            <div class="footer">
                <p>
                    🍎 <strong>Big Apple Recreational Sports</strong><br>
                    Questions? Email us at <a href="mailto:info@bigapplerecsports.com">info@bigapplerecsports.com</a>
                </p>
            </div>
        </div>

        <script>
            const selector = document.getElementById('leagueSelector');
            const positionCircle = document.getElementById('positionCircle');
            const currentLeague = document.getElementById('currentLeague');
            const positionText = document.getElementById('positionText');

            selector.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                const spot = selectedOption.getAttribute('data-spot');
                const league = selectedOption.value;

                // Update display with animation
                positionCircle.style.transform = 'scale(0.8)';

                setTimeout(() => {
                    positionCircle.textContent = '#' + spot;
                    currentLeague.textContent = league;
                    positionText.innerHTML = \`You are <strong>#\${spot}</strong> on the waitlist\`;
                    positionCircle.style.transform = 'scale(1)';
                }, 150);
            });
        </script>
    </body>
    </html>
  `);
}
