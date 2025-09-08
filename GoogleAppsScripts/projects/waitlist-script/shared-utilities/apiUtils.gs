/**
 * Common API Helper Functions
 * Copy these functions into your Google Apps Script projects as needed
 */

/**
 * Make a secure API request with proper error handling
 * @param {string} url - The API endpoint URL
 * @param {Object} options - Request options (method, headers, payload, etc.)
 * @returns {Object} Parsed response or error object
 */
function makeApiRequest(url, options = {}) {
  const defaultOptions = {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    },
    muteHttpExceptions: true
  };
  
  const requestOptions = { ...defaultOptions, ...options };
  
  try {
    console.log(`Making ${requestOptions.method} request to: ${url}`);
    
    const response = UrlFetchApp.fetch(url, requestOptions);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    console.log(`Response code: ${responseCode}`);
    
    if (responseCode >= 200 && responseCode < 300) {
      try {
        return JSON.parse(responseText);
      } catch (parseError) {
        console.log('Response is not JSON, returning as text');
        return { success: true, data: responseText };
      }
    } else {
      console.error(`API request failed with code ${responseCode}: ${responseText}`);
      return { 
        success: false, 
        error: `HTTP ${responseCode}`, 
        message: responseText 
      };
    }
  } catch (error) {
    console.error('API request failed:', error);
    return { 
      success: false, 
      error: 'Request failed', 
      message: error.toString() 
    };
  }
}

/**
 * Get a secret from PropertiesService with error handling
 * @param {string} key - The secret key
 * @returns {string} The secret value
 */
function getSecret(key) {
  const value = PropertiesService.getScriptProperties().getProperty(key);
  if (!value) {
    throw new Error(`Secret '${key}' not found. Make sure it's set up in PropertiesService.`);
  }
  return value;
}

/**
 * Build Shopify GraphQL request options
 * @param {string} query - GraphQL query string
 * @param {Object} variables - GraphQL variables
 * @returns {Object} Request options for UrlFetchApp
 */
function buildShopifyGraphQLRequest(query, variables = {}) {
  const shopifyToken = getSecret('SHOPIFY_TOKEN');
  
  return {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Shopify-Access-Token': shopifyToken
    },
    payload: JSON.stringify({
      query: query,
      variables: variables
    }),
    muteHttpExceptions: true
  };
}

/**
 * Retry an API request with exponential backoff
 * @param {Function} requestFunction - Function that makes the API request
 * @param {number} maxRetries - Maximum number of retries (default: 3)
 * @param {number} baseDelay - Base delay in milliseconds (default: 1000)
 * @returns {Object} API response or final error
 */
function retryApiRequest(requestFunction, maxRetries = 3, baseDelay = 1000) {
  let lastError;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const result = requestFunction();
      
      // If successful, return immediately
      if (result && result.success !== false) {
        return result;
      }
      
      lastError = result;
    } catch (error) {
      lastError = { success: false, error: 'Request failed', message: error.toString() };
    }
    
    // If this wasn't the last attempt, wait before retrying
    if (attempt < maxRetries) {
      const delay = baseDelay * Math.pow(2, attempt); // Exponential backoff
      console.log(`Request failed, retrying in ${delay}ms... (attempt ${attempt + 1}/${maxRetries})`);
      Utilities.sleep(delay);
    }
  }
  
  console.error(`All ${maxRetries + 1} attempts failed`);
  return lastError;
}
