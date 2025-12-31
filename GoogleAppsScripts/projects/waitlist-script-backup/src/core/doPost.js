/**
 * Main POST endpoint router
 * Intelligently routes requests to appropriate handlers
 */

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
    
    if (isShopifyWebhook(e, payload)) {
      Logger.log(`🔀 Routing to: Shopify Webhook Handler`);
      return handleShopifyWebhook(e, payload);
    }
    
    if (isAddProductRequest(payload)) {
      Logger.log(`🔀 Routing to: Add Product To Form Handler`);
      return handleAddProductToForm(payload);
    }
    
    if (isCheckWaitlistRequest(payload)) {
      Logger.log(`🔀 Routing to: Check Waitlist Position Handler`);
      return handleCheckWaitlistPosition(payload);
    }
    
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
 * Detect if request is from Shopify webhook
 */
function isShopifyWebhook(e, payload) {
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
  
  return hasShopifyHeaders || hasShopifyPayloadStructure;
}

/**
 * Detect if request is to add product to form
 */
function isAddProductRequest(payload) {
  const hasProductUrl = payload.hasOwnProperty('productUrl') && payload.productUrl;
  const hasAtLeastOneField = !!(
    payload.sport ||
    payload.day ||
    payload.division ||
    payload.otherIdentifier
  );
  
  return hasProductUrl && hasAtLeastOneField;
}

/**
 * Detect if request is to check waitlist position
 */
function isCheckWaitlistRequest(payload) {
  return !!(payload.email && payload.league);
}

/**
 * Create JSON error response
 */
function createErrorResponse(errorData) {
  return ContentService
    .createTextOutput(JSON.stringify(errorData, null, 2))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Create JSON success response
 */
function createSuccessResponse(data) {
  return ContentService
    .createTextOutput(JSON.stringify({
      status: 'ok',
      ...data
    }, null, 2))
    .setMimeType(ContentService.MimeType.JSON);
}
