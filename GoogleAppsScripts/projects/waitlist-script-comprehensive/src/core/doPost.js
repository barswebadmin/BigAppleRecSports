import { DEBUG_EMAIL } from '../config/constants';
import { handleCheckWaitlistPosition } from '../handlers/checkWaitlistPosition';
import { handleIncomingPostRequest } from '../helpers/handleIncomingPostRequest';

/**
 * Main POST endpoint router
 * Intelligently routes requests to appropriate handlers
 */

// biome-ignore lint/correctness/noUnusedVariables: GAS runtime trigger function
function doPost(e) {
  try {
    const body = e?.postData?.contents || '{}';
    const contentType = e?.postData?.type || 'application/json';
    
    Logger.log(`📥 Received POST request`);
    Logger.log(`Content-Type: ${contentType}`);
    Logger.log(`Body: ${body.substring(0, 200)}...`);
    
    let payload = {};
    
    try {
      if (contentType === 'application/x-www-form-urlencoded' && body.startsWith('payload=')) {
        payload = JSON.parse(decodeURIComponent(body.slice('payload='.length)));
      } else {
        payload = JSON.parse(body);
      }
    } catch (parseError) {
      Logger.log(`❌ JSON parse error: ${parseError.message}`);
      return createErrorResponse({
        status: 'error',
        message: 'Invalid JSON in request body',
        error: parseError.message
      });
    }
    
    Logger.log(`📦 Parsed payload: ${JSON.stringify(payload, null, 2)}`);
    
    const requestType = determineRequestType(e, payload);
    Logger.log(`🔍 Detected request type: ${requestType}`);
    
    switch (requestType) {
      case 'SHOPIFY_WEBHOOK':
        Logger.log(`🔀 Shopify webhooks not yet implemented in this system`);
        return createErrorResponse({
          status: 'error',
          message: 'Shopify webhooks not yet implemented',
          hint: 'This endpoint currently supports: add product requests and check waitlist requests'
        });
      
      case 'ADD_PRODUCT': {
        Logger.log(`🔀 Routing to: Add Product To Form Handler`);
        const result = handleIncomingPostRequest(payload);
        return createSuccessResponse(result);
      }
      
      case 'CHECK_WAITLIST':
        Logger.log(`🔀 Routing to: Check Waitlist Position Handler`);
        return handleCheckWaitlistPosition(payload);
      
      case 'UNKNOWN':
      default:
        Logger.log(`❌ Unrecognized request type`);
        return createErrorResponse({
          status: 'error',
          message: 'Unrecognized request type',
          hint: 'Expected: Shopify webhook, add product request, or check waitlist request',
          providedFields: Object.keys(payload),
          examples: {
            addProduct: {
              productUrl: 'https://example.com/products/handle',
              sport: 'Kickball',
              day: 'Sunday',
              division: 'Open'
            },
            checkWaitlist: {
              email: 'user@example.com',
              league: 'Kickball - Sunday - Open Division',
              productUrl: 'https://example.com/products/handle'
            }
          }
        });
    }
    
  } catch (err) {
    Logger.log(`💥 Unexpected error in doPost: ${err.message}`);
    Logger.log(`Stack: ${err.stack}`);
    
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: '🚨 Waitlist System: doPost Error',
      body: `Error: ${err.message}\n\nStack: ${err.stack}\n\nRequest: ${JSON.stringify(e, null, 2)}`
    });
    
    return createErrorResponse({
      status: 'error',
      message: 'Internal server error',
      details: String(err)
    });
  }
}

/**
 * Determine request type based on payload and headers
 * @param {Object} e - Request event object
 * @param {Object} payload - Parsed request payload
 * @returns {string} - Request type: 'SHOPIFY_WEBHOOK', 'ADD_PRODUCT', 'CHECK_WAITLIST', or 'UNKNOWN'
 */
function determineRequestType(e, payload) {
  // Check for Shopify webhook
  const headers = e?.parameter || {};
  const hasShopifyHeaders = !!(
    headers['X-Shopify-Hmac-SHA256'] ||
    headers['X-Shopify-Topic'] ||
    headers['X-Shopify-Shop-Domain']
  );
  const hasShopifyPayloadStructure = !!(
    payload.id &&
    payload.title &&
    payload.handle &&
    payload.variants
  );
  if (hasShopifyHeaders || hasShopifyPayloadStructure) {
    return 'SHOPIFY_WEBHOOK';
  }
  
  // Check for add product request
  const hasProductUrl = Object.hasOwn(payload, 'productUrl') && payload.productUrl;
  const hasAtLeastOneField = !!(
    payload.sport ||
    payload.day ||
    payload.division ||
    payload.otherIdentifier
  );
  if (hasProductUrl && hasAtLeastOneField) {
    return 'ADD_PRODUCT';
  }
  
  // Check for waitlist position check
  if (payload.email && payload.league) {
    return 'CHECK_WAITLIST';
  }
  
  return 'UNKNOWN';
}

/**
 * Create JSON error response
 */
export function createErrorResponse(errorData) {
  return ContentService
    .createTextOutput(JSON.stringify(errorData, null, 2))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Create JSON success response
 */
export function createSuccessResponse(data) {
  return ContentService
    .createTextOutput(JSON.stringify({
      status: 'ok',
      ...data
    }, null, 2))
    .setMimeType(ContentService.MimeType.JSON);
}
