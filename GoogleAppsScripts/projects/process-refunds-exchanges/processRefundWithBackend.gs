// Simplified Google Apps Script for processing refunds using the backend API
// This replaces the complex logic in the original files with API calls

const BACKEND_API_URL = 'http://127.0.0.1:8000'; // Update this to your deployed backend URL
const DEBUG_EMAIL = 'web@bigapplerecsports.com';

/**
 * Get order details from the backend API
 * @param {string} orderNumber - The order number to look up
 * @param {string} email - Optional email for fallback lookup
 * @returns {Object} Order details or error
 */
function getOrderDetails(orderNumber, email = null) {
  try {
    let url = `${BACKEND_API_URL}/orders/${encodeURIComponent(orderNumber)}`;
    if (email) {
      url += `?email=${encodeURIComponent(email)}`;
    }
    
    const response = UrlFetchApp.fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    const responseData = JSON.parse(response.getContentText());
    
    if (response.getResponseCode() === 200 && responseData.success) {
      return {
        success: true,
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
function cancelOrderWithRefund(orderNumber, refundType = 'refund', refundAmount = null, restockInventory = true, email = null) {
  try {
    let url = `${BACKEND_API_URL}/orders/${encodeURIComponent(orderNumber)}`;
    
    const params = new URLSearchParams();
    params.append('refund_type', refundType);
    params.append('restock_inventory', restockInventory.toString());
    
    if (refundAmount !== null) {
      params.append('refund_amount', refundAmount.toString());
    }
    
    if (email) {
      params.append('email', email);
    }
    
    url += `?${params.toString()}`;
    
    const response = UrlFetchApp.fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json'
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
        'Content-Type': 'application/json'
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
function restockInventory(orderNumber, variantName = null, email = null) {
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
        'Content-Type': 'application/json'
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

/**
 * Send Slack notification for refund completion
 * @param {Object} refundResult - The result from the backend API
 * @param {string} orderNumber - The order number
 * @param {string} channelId - Slack channel ID (optional)
 * @param {string} threadTs - Slack thread timestamp (optional)
 * @param {string} slackUserName - Name of the Slack user who processed it
 */
function sendSlackRefundNotification(refundResult, orderNumber, channelId = null, threadTs = null, slackUserName = 'Google Apps Script') {
  try {
    // This would typically be called by the backend API automatically
    // But you can also trigger it manually from Google Apps Script if needed
    
    Logger.log(`Slack notification would be sent for order ${orderNumber}`);
    Logger.log(`Refund result: ${JSON.stringify(refundResult, null, 2)}`);
    
    // If you want to send additional Slack messages from Google Apps Script,
    // you can use the original SlackUtils.gs functions here
    
    return { success: true, message: 'Slack notification logged' };
    
  } catch (error) {
    Logger.log(`Error with Slack notification: ${error.toString()}`);
    return { success: false, message: error.toString() };
  }
}

/**
 * Example function to process a refund request from Google Sheets
 * This would replace the complex logic in the original approveRefundRequest function
 * Now includes automatic Slack notifications via the backend API
 */
function processRefundRequest(orderNumber, email, refundType = 'refund', customRefundAmount = null) {
  try {
    // First, get order details to validate and show information
    const orderResult = getOrderDetails(orderNumber, email);
    
    if (!orderResult.success) {
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `❌ BARS Refund Request - Order Not Found`,
        htmlBody: `Order ${orderNumber} not found. Error: ${orderResult.message}`
      });
      return { success: false, message: orderResult.message };
    }
    
    const orderData = orderResult.data;
    Logger.log(`Order found: ${JSON.stringify(orderData.order, null, 2)}`);
    
    // Process the refund with cancellation
    const refundResult = cancelOrderWithRefund(
      orderNumber, 
      refundType, 
      customRefundAmount, 
      true, // restock inventory
      email
    );
    
    if (refundResult.success) {
      // Send success notification
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `✅ BARS Refund Request - Successfully Processed`,
        htmlBody: `
          <h3>Refund Request Processed Successfully</h3>
          <p><strong>Order:</strong> ${orderNumber}</p>
          <p><strong>Customer:</strong> ${orderData.order.customer.email}</p>
          <p><strong>Product:</strong> ${orderData.order.product.title}</p>
          <p><strong>Refund Type:</strong> ${refundType}</p>
          <p><strong>Refund Amount:</strong> $${refundResult.data.refund_amount}</p>
          <p><strong>Details:</strong> ${refundResult.message}</p>
          <p><strong>Note:</strong> Slack notification sent automatically by backend API</p>
        `
      });
      
      // Optional: Send additional Slack notification from Google Apps Script
      // (The backend API already sends one, but you can add custom messages here)
      try {
        sendSlackRefundNotification(refundResult, orderNumber, null, null, 'Google Apps Script User');
      } catch (slackError) {
        Logger.log(`Slack notification error: ${slackError.toString()}`);
      }
      
      return refundResult;
    } else {
      // Send error notification
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `❌ BARS Refund Request - Processing Failed`,
        htmlBody: `
          <h3>Refund Request Processing Failed</h3>
          <p><strong>Order:</strong> ${orderNumber}</p>
          <p><strong>Error:</strong> ${refundResult.message}</p>
        `
      });
      
      return refundResult;
    }
    
  } catch (error) {
    const errorMessage = `Error processing refund request: ${error.toString()}`;
    Logger.log(errorMessage);
    
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `❌ BARS Refund Request - Unexpected Error`,
      htmlBody: `
        <h3>Unexpected Error Processing Refund</h3>
        <p><strong>Order:</strong> ${orderNumber}</p>
        <p><strong>Error:</strong> ${errorMessage}</p>
        <p><strong>Stack:</strong> <pre>${error.stack || 'No stack trace available'}</pre></p>
      `
    });
    
    return { success: false, message: errorMessage };
  }
}

/**
 * Test function to verify the backend API connection
 */
function testBackendConnection() {
  try {
    // Test with a sample order number
    const testOrderNumber = '#1001'; // Replace with a real order number for testing
    const result = getOrderDetails(testOrderNumber);
    
    Logger.log(`Backend connection test result: ${JSON.stringify(result, null, 2)}`);
    
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: 'BARS Backend API Connection Test',
      htmlBody: `
        <h3>Backend API Connection Test</h3>
        <p><strong>API URL:</strong> ${BACKEND_API_URL}</p>
        <p><strong>Test Order:</strong> ${testOrderNumber}</p>
        <p><strong>Result:</strong> ${result.success ? 'SUCCESS' : 'FAILED'}</p>
        <p><strong>Details:</strong> <pre>${JSON.stringify(result, null, 2)}</pre></p>
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
      `
    });
    
    return { success: false, message: errorMessage };
  }
} 