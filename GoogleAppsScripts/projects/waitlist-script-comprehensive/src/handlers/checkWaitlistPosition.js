import { DEBUG_EMAIL } from '../config/constants';
import { createErrorResponse, createSuccessResponse } from '../core/doPost';
import { sendWaitlistConfirmationEmail } from '../helpers/emailHelpers';
import { extractProductHandleFromUrl, extractProductIdFromUrl } from '../helpers/productHandleHelpers';
import { calculateWaitlistPosition } from '../helpers/waitlistCalculation';
import { validateProductAndInventory, validateProductAndInventoryById } from '../shared-utilities/ShopifyUtils';

/**
 * Handle POST request to check waitlist position
 * Called by doPost router when email + league + productUrl are provided
 */

export function handleCheckWaitlistPosition(payload) {
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
      
      const waitlistResult = calculateWaitlistPosition(email, league);
      debugInfo.push(`📊 Waitlist result: ${JSON.stringify(waitlistResult)}`);
      
      if (waitlistResult.found) {
        // Send waitlist confirmation email to the user
        debugInfo.push("📧 Sending waitlist confirmation email to user...");
        const emailSent = sendWaitlistConfirmationEmail(email, league, waitlistResult.position);
        debugInfo.push(`📧 Email sent: ${emailSent}`);
        
        const response = {
          success: true,
          productSoldOut: true,
          waitlistSpot: waitlistResult.position,
          emailSent: emailSent,
          message: `You are #${waitlistResult.position} on the waitlist for ${league}. Confirmation email sent to ${email}.`
        };
        
        debugInfo.push("✅ Returning successful waitlist response");
        
        MailApp.sendEmail({
          to: DEBUG_EMAIL,
          subject: "🔍 Check Waitlist Position - Success",
          body: `${debugInfo.join('\n')}\n\nResponse: ${JSON.stringify(response, null, 2)}`
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
        body: `${debugInfo.join('\n')}\n\nResponse: ${JSON.stringify(response, null, 2)}`
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
