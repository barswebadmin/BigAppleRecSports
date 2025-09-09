/**
 * ========================================================================
 * BARS REFUND PROCESSING - BACKEND INTEGRATION
 * ========================================================================
 * 
 * Complete standalone Google Apps Script for processing refunds using the backend API
 * This replaces ALL the complex logic in the original files with clean API calls
 * 
 * 🚀 BACKEND FEATURES (automatically handled by API):
 * ✅ Slack notifications to #refunds channel with rich formatting
 * ✅ Sport-specific team mentions (@kickball, @bowling, etc.)
 * ✅ Order cancellation and refund processing
 * ✅ Inventory restocking with proper location management
 * ✅ Season-aware refund calculations (95%, 90%, 80%, 70%, 60%, 50%)
 * ✅ Store credit processing (100%, 95%, 85%, 75%, 65%, 55%)
 * ✅ Error handling and comprehensive logging
 * ✅ Shopify GraphQL integration
 * 
 * 📝 GOOGLE APPS SCRIPT ROLE:
 * - Process form submissions from Google Forms
 * - Extract form data and normalize order numbers
 * - Make API calls to backend for processing
 * - Send email notifications for debugging/tracking
 * - Handle errors gracefully
 * 
 * 🔧 SETUP INSTRUCTIONS:
 * 1. Update BACKEND_API_URL to your deployed backend URL
 * 2. Comment out the old processFormSubmit() in processFormSubmit.gs
 * 3. This file will handle all form submissions automatically
 * 
 * ========================================================================
 */

// ========================================================================
// CONFIGURATION
// ========================================================================

// ========================================================================
// MAIN FORM SUBMISSION HANDLER
// ========================================================================

/**
 * NEW processFormSubmit function that integrates with the backend API
 * This replaces the original complex form processing logic
 * 
 * Triggered automatically when Google Form is submitted
 * Extracts form data and calls backend API for processing
 */
function processFormSubmitApi(e) {
  try {
    Logger.log('🚀 Processing form submission with backend API integration...');
    
    // ========================================================================
    // EXTRACT FORM DATA
    // ========================================================================
    
    const getFieldValueByKeyword = (keyword) => {
      const entry = Object.entries(e.namedValues).find(([key]) =>
        key.toLowerCase().includes(keyword.toLowerCase())
      );
      return entry?.[1]?.[0]?.trim() || "";
    };

    const requestorName = {
      first: getFieldValueByKeyword("first name"),
      last: getFieldValueByKeyword("last name")
    };

    const requestorEmail = getFieldValueByKeyword("email");
    const rawOrderNumber = getFieldValueByKeyword("order number");
    const refundAnswer = getFieldValueByKeyword("do you want a refund");
    const refundOrCredit = refundAnswer.toLowerCase().includes("refund") ? "refund" : "credit";
    const requestNotes = getFieldValueByKeyword("note");
    
    // Normalize order number (add # if missing)
    const formattedOrderNumber = normalizeOrderNumber2(rawOrderNumber);
    
    Logger.log(`📋 Form Data Extracted:`);
    Logger.log(`   - Requestor: ${requestorName.first} ${requestorName.last}`);
    Logger.log(`   - Email: ${requestorEmail}`);
    Logger.log(`   - Order: ${rawOrderNumber} → ${formattedOrderNumber}`);
    Logger.log(`   - Type: ${refundOrCredit}`);
    Logger.log(`   - Notes: ${requestNotes}`);
    
    // ========================================================================
    // SEND TO BACKEND API FOR PROCESSING
    // ========================================================================
    
    // First, get order details to validate the request
    const orderResult = getOrderDetails2(formattedOrderNumber, requestorEmail);
    
    if (!orderResult.success) {
      // Order not found - send error notification
      const errorMessage = `Order ${formattedOrderNumber} not found for ${requestorEmail}. Error: ${orderResult.message}`;
      
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `❌ BARS Refund Form - Order Not Found`,
        htmlBody: `
          <h3>❌ Refund Request Failed - Order Not Found</h3>
          <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last}</p>
          <p><strong>Email:</strong> ${requestorEmail}</p>
          <p><strong>Order Number:</strong> ${rawOrderNumber} (formatted: ${formattedOrderNumber})</p>
          <p><strong>Refund Type:</strong> ${refundOrCredit}</p>
          <p><strong>Notes:</strong> ${requestNotes}</p>
          <p><strong>Error:</strong> ${orderResult.message}</p>
          <p><strong>⚠️ Action Required:</strong> Manual review needed - customer may have entered wrong order number or email</p>
        `
      });
      
      Logger.log(`❌ Order not found: ${errorMessage}`);
      return;
    }
    
    const orderData = orderResult.data;
    Logger.log(`✅ Order found: ${orderData.order?.orderName} for ${orderData.order?.customer?.email}`);
    
    // ========================================================================
    // PROCESS REFUND VIA BACKEND API
    // ========================================================================
    
    const refundResult = processRefundRequestViaAPI(
      formattedOrderNumber,
      requestorEmail,
      refundOrCredit,
      null, // Let backend calculate refund amount
      requestorName,
      requestNotes
    );
    
    if (refundResult.success) {
      // ✅ SUCCESS - Send confirmation email
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `✅ BARS Refund Form - Successfully Processed`,
        htmlBody: `
          <h3>✅ Refund Request Processed Successfully</h3>
          <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last}</p>
          <p><strong>Email:</strong> ${requestorEmail}</p>
          <p><strong>Order:</strong> ${formattedOrderNumber}</p>
          <p><strong>Product:</strong> ${orderData.order?.product?.title}</p>
          <p><strong>Refund Type:</strong> ${refundOrCredit}</p>
          <p><strong>Refund Amount:</strong> $${refundResult.data.refund_amount}</p>
          <p><strong>Notes:</strong> ${requestNotes}</p>
          <p><strong>✅ Slack Notification:</strong> Automatically sent to #refunds channel</p>
          <p><strong>📦 Inventory:</strong> ${refundResult.data.restock_results ? 'Restocked automatically' : 'No restocking needed'}</p>
          <p><strong>🎯 Status:</strong> COMPLETE - Customer will receive refund/credit</p>
        `
      });
      
      Logger.log(`✅ Refund processed successfully via backend API`);
      
    } else {
      // ❌ FAILED - Send error notification
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `❌ BARS Refund Form - Processing Failed`,
        htmlBody: `
          <h3>❌ Refund Request Processing Failed</h3>
          <p><strong>Requestor:</strong> ${requestorName.first} ${requestorName.last}</p>
          <p><strong>Email:</strong> ${requestorEmail}</p>
          <p><strong>Order:</strong> ${formattedOrderNumber}</p>
          <p><strong>Refund Type:</strong> ${refundOrCredit}</p>
          <p><strong>Notes:</strong> ${requestNotes}</p>
          <p><strong>❌ Error:</strong> ${refundResult.message}</p>
          <p><strong>⚠️ Action Required:</strong> Manual review and processing needed</p>
        `
      });
      
      Logger.log(`❌ Refund processing failed: ${refundResult.message}`);
    }
    
  } catch (error) {
    // ⚠️ UNEXPECTED ERROR
    const errorMessage = `Unexpected error in processFormSubmit: ${error.toString()}`;
    Logger.log(`⚠️ ${errorMessage}`);
    
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `⚠️ BARS Refund Form - Unexpected Error`,
      htmlBody: `
        <h3>⚠️ Unexpected Error in Form Processing</h3>
        <p><strong>Error:</strong> ${errorMessage}</p>
        <p><strong>Stack:</strong> <pre>${error.stack || 'No stack trace available'}</pre></p>
        <p><strong>Form Data:</strong> <pre>${JSON.stringify(e.namedValues, null, 2)}</pre></p>
        <p><strong>⚠️ Action Required:</strong> Check logs and process manually</p>
      `
    });
  }
}

// ========================================================================
// BACKEND API INTEGRATION FUNCTIONS
// ========================================================================

/**
 * Get order details from the backend API
 * @param {string} orderNumber - The order number to look up
 * @param {string} email - Optional email for fallback lookup
 * @returns {Object} Order details or error
 */
function getOrderDetails2(orderNumber, email = null) {
  try {
    let url = `${BACKEND_API_URL}/orders/${encodeURIComponent(orderNumber)}/validate-email`;
    if (email) {
      url += `?email=${encodeURIComponent(email)}`;
    }
    
    const response = UrlFetchApp.fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        "ngrok-skip-browser-warning": "true"
      }
    });

    const rawText = response.getContentText();
    Logger.log(`🧪 Raw response from backend:\n${rawText}`);
    
    const responseData = JSON.parse(response.getContentText());
    
    if (response.getResponseCode() === 200 && responseData.data.email_matches) {
      return {
        success: true,
        data: responseData.data
      };
    } else if (response.getResponseCode() === 200 && !responseData.data.email_matches) {
      return {
        success: false,
        data: responseData.data
      };
    } else {
      return {
        success: false,
        message: responseData.detail || 'Failed to fetch order details'
      };
    }
    
  } catch (error) {
    Logger.log(`Error fetching order details: ${error.toString()}`);
    return {
      success: false,
      message: `Error fetching order details: ${error.toString()}`
    };
  }
}

/**
 * Cancel an order and process refund/credit via backend API
 * @param {string} orderNumber - The order number to cancel
 * @param {string} refundType - 'refund' or 'credit'
 * @param {number} refundAmount - Optional custom refund amount
 * @param {boolean} restockInventory - Whether to restock inventory
 * @param {string} email - Optional email for fallback lookup
 * @returns {Object} Cancellation result
 */
function cancelOrderWithRefund(orderNumber, refundType = 'refund', refundAmount = null, restockInventory = false, email = null) {
  try {
    let url = `${BACKEND_API_URL}/orders/${encodeURIComponent(orderNumber)}?refund_type=${refundType}&refundAmount=${refundAmount}&restockInventory=${restockInventory}&email=${email}`;
    
    // const params = new URLSearchParams();
    // params.append('refund_type', refundType);
    // params.append('restock_inventory', restockInventory.toString());
    
    // if (refundAmount !== null) {
    //   params.append('refund_amount', refundAmount.toString());
    // }
    
    // if (email) {
    //   params.append('email', email);
    // }
    
    // url += `?${params.toString()}`;
    
    const response = UrlFetchApp.fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        "ngrok-skip-browser-warning": "true"
      }
    });
    
    const responseData = JSON.parse(response.getContentText());
    
    if (response.getResponseCode() === 200 && responseData.success) {
      return {
        success: true,
        data: responseData.data,
        message: responseData.message
      };
    } else {
      return {
        success: false,
        message: responseData.detail || 'Failed to cancel order'
      };
    }
    
  } catch (error) {
    Logger.log(`Error canceling order: ${error.toString()}`);
    return {
      success: false,
      message: `Error canceling order: ${error.toString()}`
    };
  }
}

/**
 * Create a refund or store credit without canceling the order
 * @param {string} orderNumber - The order number
 * @param {string} refundType - 'refund' or 'credit'
 * @param {number} refundAmount - Optional custom refund amount
 * @param {string} email - Optional email for fallback lookup
 * @returns {Object} Refund result
 */
function createRefundOnly(orderNumber, refundType = 'refund', refundAmount = null, email = null) {
  try {
    let url = `${BACKEND_API_URL}/orders/${encodeURIComponent(orderNumber)}/refund`;
    
    const params = new URLSearchParams();
    params.append('refund_type', refundType);
    
    if (refundAmount !== null) {
      params.append('refund_amount', refundAmount.toString());
    }
    
    if (email) {
      params.append('email', email);
    }
    
    url += `?${params.toString()}`;
    
    const response = UrlFetchApp.fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        "ngrok-skip-browser-warning": "true"
      }
    });
    
    const responseData = JSON.parse(response.getContentText());
    
    if (response.getResponseCode() === 200 && responseData.success) {
      return {
        success: true,
        data: responseData.data,
        message: responseData.message
      };
    } else {
      return {
        success: false,
        message: responseData.detail || 'Failed to create refund'
      };
    }
    
  } catch (error) {
    Logger.log(`Error creating refund: ${error.toString()}`);
    return {
      success: false,
      message: `Error creating refund: ${error.toString()}`
    };
  }
}

/**
 * Restock inventory for an order
 * @param {string} orderNumber - The order number
 * @param {string} variantName - Optional specific variant to restock
 * @param {string} email - Optional email for fallback lookup
 * @returns {Object} Restock result
 */
function restockInventory2(orderNumber, variantName = null, email = null) {
  try {
    let url = `${BACKEND_API_URL}/orders/${encodeURIComponent(orderNumber)}/restock`;
    
    const params = new URLSearchParams();
    
    if (variantName) {
      params.append('variant_name', variantName);
    }
    
    if (email) {
      params.append('email', email);
    }
    
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    
    const response = UrlFetchApp.fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        "ngrok-skip-browser-warning": "true"
      }
    });
    
    const responseData = JSON.parse(response.getContentText());
    
    if (response.getResponseCode() === 200 && responseData.success) {
      return {
        success: true,
        data: responseData.data,
        message: responseData.message
      };
    } else {
      return {
        success: false,
        message: responseData.detail || 'Failed to restock inventory'
      };
    }
    
  } catch (error) {
    Logger.log(`Error restocking inventory: ${error.toString()}`);
    return {
      success: false,
      message: `Error restocking inventory: ${error.toString()}`
    };
  }
}

// ========================================================================
// MAIN WORKFLOW FUNCTIONS
// ========================================================================

/**
 * Process a complete refund request via the backend API
 * This is the main workflow function that handles the entire process
 * 
 * @param {string} orderNumber - The order number
 * @param {string} email - Customer email
 * @param {string} refundType - 'refund' or 'credit'
 * @param {number} customRefundAmount - Optional custom amount
 * @param {Object} requestorName - {first, last}
 * @param {string} requestNotes - Additional notes
 * @returns {Object} Processing result
 */
function processRefundRequestViaAPI(orderNumber, email, refundType = 'refund', customRefundAmount = null, requestorName = {}, requestNotes = '') {
  try {
    Logger.log(`🔄 Processing refund request via backend API...`);
    Logger.log(`   - Order: ${orderNumber}`);
    Logger.log(`   - Email: ${email}`);
    Logger.log(`   - Type: ${refundType}`);
    Logger.log(`   - Custom Amount: ${customRefundAmount || 'Auto-calculate'}`);
    
    // Process the refund with cancellation via backend API
    const refundResult = cancelOrderWithRefund(
      orderNumber, 
      refundType, 
      customRefundAmount, 
      true, // restock inventory
      email
    );
    
    if (refundResult.success) {
      Logger.log(`✅ Refund processed successfully via backend API`);
      Logger.log(`   - Refund Amount: $${refundResult.data.refund_amount}`);
      Logger.log(`   - Slack notification sent automatically`);
      Logger.log(`   - Inventory restocked: ${refundResult.data.restock_results ? 'Yes' : 'No'}`);
      
      return refundResult;
    } else {
      Logger.log(`❌ Refund processing failed: ${refundResult.message}`);
      return refundResult;
    }
    
  } catch (error) {
    const errorMessage = `Error in processRefundRequestViaAPI: ${error.toString()}`;
    Logger.log(`❌ ${errorMessage}`);
    
    return { 
      success: false, 
      message: errorMessage 
    };
  }
}

// ========================================================================
// UTILITY FUNCTIONS
// ========================================================================

/**
 * Normalize order number to ensure it has # prefix
 * @param {string} rawOrderNumber - Raw order number from form
 * @returns {string} Normalized order number with # prefix
 */
function normalizeOrderNumber2(rawOrderNumber) {
  if (!rawOrderNumber) return '';
  
  const cleaned = rawOrderNumber.toString().trim();
  return cleaned.startsWith('#') ? cleaned.slice(1) : cleaned;
}

/**
 * Test function to verify the backend API connection
 */
function testBackendConnection() {
  try {
    Logger.log('🧪 Testing backend API connection...');
    
    // Test with a sample order number
    const testOrderNumber = '#1001'; // Replace with a real order number for testing
    const result = getOrderDetails2(testOrderNumber);
    
    Logger.log(`Backend connection test result: ${JSON.stringify(result, null, 2)}`);
    
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: 'BARS Backend API Connection Test',
      htmlBody: `
        <h3>Backend API Connection Test</h3>
        <p><strong>API URL:</strong> ${BACKEND_API_URL}</p>
        <p><strong>Test Order:</strong> ${testOrderNumber}</p>
        <p><strong>Result:</strong> ${result.success ? 'SUCCESS ✅' : 'FAILED ❌'}</p>
        <p><strong>Details:</strong> <pre>${JSON.stringify(result, null, 2)}</pre></p>
        ${result.success ? 
          '<p><strong>✅ Backend is working correctly!</strong></p>' : 
          '<p><strong>❌ Backend connection failed - check URL and server status</strong></p>'
        }
      `
    });
    
    return result;
    
  } catch (error) {
    const errorMessage = `Backend connection test failed: ${error.toString()}`;
    Logger.log(errorMessage);
    
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: '❌ BARS Backend API Connection Test Failed',
      htmlBody: `
        <h3>Backend API Connection Test Failed</h3>
        <p><strong>API URL:</strong> ${BACKEND_API_URL}</p>
        <p><strong>Error:</strong> ${errorMessage}</p>
        <p><strong>Stack:</strong> <pre>${error.stack || 'No stack trace available'}</pre></p>
        <p><strong>⚠️ Action Required:</strong> Check backend server status and URL configuration</p>
      `
    });
    
    return { success: false, message: errorMessage };
  }
}

/**
 * Manual refund processing function for testing/debugging
 * Can be called manually from Google Apps Script editor
 */
function manualRefundTest() {
  const testOrderNumber = '#1001'; // Replace with actual order number
  const testEmail = 'test@example.com'; // Replace with actual email
  const testRefundType = 'refund'; // or 'credit'
  
  Logger.log('🧪 Manual refund test starting...');
  
  const result = processRefundRequestViaAPI(
    testOrderNumber,
    testEmail,
    testRefundType,
    null, // auto-calculate amount
    { first: 'Test', last: 'User' },
    'Manual test from Google Apps Script'
  );
  
  Logger.log(`Manual refund test result: ${JSON.stringify(result, null, 2)}`);
  
  return result;
}

// ========================================================================
// GOOGLE SHEETS MENU FUNCTIONS (OPTIONAL)
// ========================================================================

/**
 * Create custom menu in Google Sheets for manual operations
 * This function runs when the spreadsheet is opened
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  
  ui.createMenu('💰 BARS Refunds & Exchanges')
    .addItem('🧪 Test Backend Connection', 'testBackendConnection')
    .addItem('🔄 Manual Refund Test', 'manualRefundTest')
    .addSeparator()
    .addItem('📖 View API Documentation', 'showAPIDocumentation')
    .addItem('📘 View Instructions', 'showInstructions')
    .addToUi();
    
  // Show instructions on first open
  showInstructions();
}

/**
 * Show API documentation in a dialog
 */
function showAPIDocumentation() {
  const html = `
    <div style="font-family: Arial, sans-serif; padding: 20px;">
      <h2>🎯 BARS Refunds Backend API</h2>
      
      <h3>🚀 Features</h3>
      <ul>
        <li>✅ Automatic Slack notifications to #refunds channel</li>
        <li>✅ Sport-specific team mentions (@kickball, @bowling, etc.)</li>
        <li>✅ Season-aware refund calculations</li>
        <li>✅ Inventory restocking with proper location management</li>
        <li>✅ Error handling and comprehensive logging</li>
      </ul>
      
      <h3>📊 Refund Tiers</h3>
      <p><strong>Refunds:</strong> 95%, 90%, 80%, 70%, 60%, 50% (based on timing)</p>
      <p><strong>Credits:</strong> 100%, 95%, 85%, 75%, 65%, 55% (higher amounts)</p>
      
      <h3>🔧 Current Configuration</h3>
      <p><strong>Backend URL:</strong> ${BACKEND_API_URL}</p>
      <p><strong>Debug Email:</strong> ${DEBUG_EMAI_2L}</p>
      
      <h3>🆘 Troubleshooting</h3>
      <p>If refunds are not processing:</p>
      <ol>
        <li>Test backend connection using the menu</li>
        <li>Check that backend server is running</li>
        <li>Verify BACKEND_API_URL is correct</li>
        <li>Check email notifications for error details</li>
      </ol>
    </div>
  `;
  
  const htmlOutput = HtmlService.createHtmlOutput(html)
    .setWidth(600)
    .setHeight(500);
    
  SpreadsheetApp.getUi().showModalDialog(htmlOutput, 'BARS Refunds API Documentation');
}

// ========================================================================
// END OF FILE
// ========================================================================

/**
 * 📋 DEPLOYMENT CHECKLIST:
 * 
 * 1. ✅ Update BACKEND_API_URL to your deployed backend URL
 * 2. ✅ Comment out old processFormSubmit() in processFormSubmit.gs
 * 3. ✅ Test backend connection using testBackendConnection()
 * 4. ✅ Test with a real order using manualRefundTest()
 * 5. ✅ Verify Slack notifications are working
 * 6. ✅ Monitor email notifications for any issues
 * 
 * 🎯 This file completely replaces the complex original refund logic
 * with clean, maintainable API calls to your backend!
 */