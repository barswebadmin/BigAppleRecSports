/**
 * DoGet handler
 * Routes based on parameters and orchestrates GET requests
 */

import { calculateWaitlistPositionsForPlayer } from '../services/calculateWaitlistPositions.js';
import { PageRender } from '../ui/renderPages.js';
import { sendToSlack } from '../integrations/slackNotifications.js';
import { getSheetsClient } from '../controllers/processRequest.js';

/**
 * Handle doGet request routing
 * @param {SheetsClient} sheetsClient - Initialized SheetsClient instance
 * @param {string} productId - Product ID
 * @param {string} email - User's email
 * @param {string} customerId - User's customer ID
 * @param {string} source - Source of request
 * @param {string} league - Product/league name
 * @returns {GoogleAppsScript.HTML.HtmlOutput} HTML response
 */
export function handleDoGet(sheetsClient, productId, email, customerId, source, league) {
  const pageRender = new PageRender();

  sendToSlack(`🔍 **HandleDoGet Started**\nProduct ID: ${productId}\nEmail: ${email ? '[REDACTED]' : 'None'}\nCustomer ID: ${customerId || 'None'}\nSource: ${source}\nLeague: ${league}`);

  try {
    // Check if this is an API request for position data
    const action = source; // For now, use source to determine if this is an API call

    if (action === 'getPositions') {
      // API endpoint: Return JSON data only
      return handleGetPositionsAPI(sheetsClient, productId, email, customerId);
    }

    // Default: Return immediate HTML with spinner, then fetch data via google.script.run
    if (productId) {
      sendToSlack(`✅ **Serving Immediate Loading Page**\nProduct ID: ${productId}`);

      const loadingPageResponse = pageRender.renderLoadingPage(productId, email, customerId, source, league);

      sendToSlack(`✅ **Loading Page Served Successfully**\nProduct ID: ${productId}\nSource: ${source}`);

      return loadingPageResponse;

    } else {
      sendToSlack(`❌ **Product ID Validation Failed**\nMissing productId\nSource: ${source}\nLeague: ${league}`);

      const errorResponse = pageRender.renderErrorPage('Missing product information. Please access this page from a product link.');

      sendToSlack(`⚠️ **Missing Product Error Page Served**\nError: missing_product_id`);

      return errorResponse;
    }

  } catch (error) {
    sendToSlack(`❌ **HandleDoGet Exception**\nError: ${error.message}\nProduct ID: ${productId}\nEmail: ${!!email}\nCustomer ID: ${customerId}\nSource: ${source}\nLeague: ${league}`);

    const errorResponse = pageRender.renderErrorPage(`Error loading page: ${error.message}`, error);

    sendToSlack(`🚨 **General Error Page Served**\nError: ${error.message}`);

    return errorResponse;
  }
}

/**
 * Handle API request for position data
 * @param {SheetsClient} sheetsClient - Initialized SheetsClient instance
 * @param {string} productId - Product ID
 * @param {string} email - User's email
 * @param {string} customerId - User's customer ID
 * @returns {GoogleAppsScript.Content.TextOutput} JSON response
 */
function handleGetPositionsAPI(sheetsClient, productId, email, customerId) {
  const pageRender = new PageRender();

  try {
    if (!productId) {
      return pageRender.renderJsonResponse({
        success: false,
        message: 'Missing product information.'
      }, 400);
    }

    // Process the actual position calculation (this takes 1-2 seconds)
    const waitlistPositionsForPlayer = calculateWaitlistPositionsForPlayer(sheetsClient, email, customerId, productId);

    if (waitlistPositionsForPlayer === null) {
      // User not found - return data for locked product page
      return pageRender.renderJsonResponse({
        success: true,
        type: 'locked',
        productId: productId
      });
    }

    // User found - return position data
    return pageRender.renderJsonResponse({
      success: true,
      type: 'positions',
      positions: waitlistPositionsForPlayer,
      currentProductId: productId
    });

  } catch (error) {
    sendToSlack(`❌ **API Position Request Failed**\nError: ${error.message}\nProduct ID: ${productId}`);

    return pageRender.renderJsonResponse({
      success: false,
      message: `Error: ${error.message}`
    }, 500);
  }
}

/**
 * Server-side function callable from HTML via google.script.run
 * @param {string} productId - Product ID
 * @param {string} email - User's email
 * @param {string} customerId - User's customer ID
 * @returns {Object} Position data object
 */
export function getPositionData(productId, email, customerId) {
  try {
    const sheetsClient = getSheetsClient();

    if (!productId) {
      return {
        success: false,
        message: 'Missing product information.'
      };
    }

    // Process the actual position calculation
    const waitlistPositionsForPlayer = calculateWaitlistPositionsForPlayer(sheetsClient, email, customerId, productId);

    if (waitlistPositionsForPlayer === null) {
      // User not found - return data for locked product page
      return {
        success: true,
        type: 'locked',
        productId: productId
      };
    }

    // User found - return position data
    return {
      success: true,
      type: 'positions',
      positions: waitlistPositionsForPlayer,
      currentProductId: productId
    };

  } catch (error) {
    sendToSlack(`❌ **getPositionData Failed**\nError: ${error.message}\nProduct ID: ${productId}`);

    return {
      success: false,
      message: `Error: ${error.message}`
    };
  }
}