import { DEBUG_EMAIL } from '../config/constants';
import { handleCheckWaitlistPosition } from '../handlers/checkWaitlistPosition';

/**
 * Main POST endpoint router
 * Intelligently routes requests to appropriate handlers
 */

// biome-ignore lint/correctness/noUnusedVariables: GAS runtime trigger function
function doPost(e) {
  const functionName = 'doPost';
  const startTime = new Date().getTime();
  const timestamp = new Date().toISOString();
  
  Logger.log(`🚀 [${timestamp}] === ENTERING ${functionName} ===`);
  Logger.log(`   Request received at: ${timestamp}`);
  
  let requestContext = {
    contentType: null,
    bodyLength: 0,
    payloadKeys: null,
    requestType: null,
    handlerCalled: null
  };
  
  try {
    const body = e?.postData?.contents || '{}';
    const contentType = e?.postData?.type || 'application/json';
    requestContext.contentType = contentType;
    requestContext.bodyLength = body.length;
    
    Logger.log(`📥 [${timestamp}] Received POST request`);
    Logger.log(`   Content-Type: ${contentType}`);
    Logger.log(`   Body length: ${body.length} characters`);
    Logger.log(`   Body preview: ${body.substring(0, 200)}${body.length > 200 ? '...' : ''}`);
    
    let payload = {};
    
    try {
      Logger.log(`🔍 [${timestamp}] Parsing request body...`);
      if (contentType === 'application/x-www-form-urlencoded' && body.startsWith('payload=')) {
        Logger.log(`   Detected form-encoded payload, decoding...`);
        payload = JSON.parse(decodeURIComponent(body.slice('payload='.length)));
      } else {
        Logger.log(`   Parsing as JSON...`);
        payload = JSON.parse(body);
      }
      requestContext.payloadKeys = Object.keys(payload);
      Logger.log(`✅ [${timestamp}] Successfully parsed payload with ${requestContext.payloadKeys.length} keys: ${requestContext.payloadKeys.join(', ')}`);
    } catch (parseError) {
      const errorContext = {
        function: functionName,
        operation: 'parse_request_body',
        contentType: contentType,
        bodyLength: body.length,
        bodyPreview: body.substring(0, 500),
        error: parseError.message,
        errorName: parseError.name,
        stack: parseError.stack
      };
      
      Logger.log(`❌ [${timestamp}] === JSON PARSE ERROR in ${functionName} ===`);
      Logger.log(`   Operation: Parsing request body`);
      Logger.log(`   Content-Type: ${contentType}`);
      Logger.log(`   Body length: ${body.length} characters`);
      Logger.log(`   Error: ${parseError.message}`);
      Logger.log(`   Error type: ${parseError.name}`);
      Logger.log(`   Stack trace: ${parseError.stack || 'No stack trace available'}`);
      Logger.log(`   Body preview: ${body.substring(0, 500)}`);
      
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `🚨 ${functionName}: JSON Parse Error`,
        htmlBody: `
          <h2>🚨 JSON Parse Error in ${functionName}</h2>
          <p><strong>Timestamp:</strong> ${timestamp}</p>
          <p><strong>Operation:</strong> Parsing request body</p>
          <p><strong>Content-Type:</strong> ${contentType}</p>
          <p><strong>Body Length:</strong> ${body.length} characters</p>
          <p><strong>Error:</strong> ${parseError.message}</p>
          <p><strong>Error Type:</strong> ${parseError.name}</p>
          <h3>Stack Trace:</h3>
          <pre>${parseError.stack || 'No stack trace available'}</pre>
          <h3>Body Preview:</h3>
          <pre>${body.substring(0, 1000)}</pre>
        `
      });
      
      return createErrorResponse({
        status: 'error',
        message: 'Invalid JSON in request body',
        error: parseError.message,
        context: errorContext
      });
    }
    
    Logger.log(`📦 [${timestamp}] Parsed payload: ${JSON.stringify(payload, null, 2)}`);
    
    try {
      Logger.log(`🔍 [${timestamp}] Determining request type...`);
      const requestType = determineRequestType(payload);
      requestContext.requestType = requestType;
      Logger.log(`✅ [${timestamp}] Detected request type: ${requestType}`);
    } catch (typeError) {
      const errorContext = {
        function: functionName,
        operation: 'determine_request_type',
        payloadKeys: Object.keys(payload),
        error: typeError.message,
        errorName: typeError.name,
        stack: typeError.stack
      };
      
      Logger.log(`❌ [${timestamp}] === ERROR determining request type in ${functionName} ===`);
      Logger.log(`   Operation: Determining request type`);
      Logger.log(`   Payload keys: ${Object.keys(payload).join(', ')}`);
      Logger.log(`   Error: ${typeError.message}`);
      Logger.log(`   Stack: ${typeError.stack || 'No stack trace'}`);
      
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `🚨 ${functionName}: Request Type Detection Error`,
        htmlBody: `
          <h2>🚨 Error Determining Request Type in ${functionName}</h2>
          <p><strong>Timestamp:</strong> ${timestamp}</p>
          <p><strong>Operation:</strong> Determining request type</p>
          <p><strong>Payload Keys:</strong> ${Object.keys(payload).join(', ')}</p>
          <p><strong>Error:</strong> ${typeError.message}</p>
          <h3>Stack Trace:</h3>
          <pre>${typeError.stack || 'No stack trace'}</pre>
        `
      });
      
      return createErrorResponse({
        status: 'error',
        message: 'Failed to determine request type',
        error: typeError.message,
        context: errorContext
      });
    }
    
    let result;
    try {
      switch (requestContext.requestType) {
        case 'CHECK_WAITLIST':
          Logger.log(`🔀 [${timestamp}] Routing to: Check Waitlist Position Handler`);
          requestContext.handlerCalled = 'handleCheckWaitlistPosition';
          Logger.log(`   Calling handler with email: ${payload.email}, league: ${payload.league}`);
          result = handleCheckWaitlistPosition(payload);
          Logger.log(`✅ [${timestamp}] Handler completed successfully`);
          return result;
        
        case 'UNKNOWN':
        default:
          Logger.log(`❌ [${timestamp}] Unrecognized request type`);
          return createErrorResponse({
            status: 'error',
            message: 'Unrecognized request type',
            hint: 'Expected: check waitlist request with email and league fields',
            providedFields: Object.keys(payload),
            example: {
              email: 'user@example.com',
              league: 'Kickball - Sunday - Open Division',
              productUrl: 'https://example.com/products/handle'
            }
          });
      }
    } catch (handlerError) {
      const errorContext = {
        function: functionName,
        operation: `calling_handler_${requestContext.handlerCalled || 'unknown'}`,
        requestType: requestContext.requestType,
        handlerCalled: requestContext.handlerCalled,
        payloadKeys: Object.keys(payload),
        error: handlerError.message,
        errorName: handlerError.name,
        stack: handlerError.stack
      };
      
      Logger.log(`❌ [${timestamp}] === HANDLER ERROR in ${functionName} ===`);
      Logger.log(`   Operation: Calling handler '${requestContext.handlerCalled}'`);
      Logger.log(`   Request Type: ${requestContext.requestType}`);
      Logger.log(`   Payload keys: ${Object.keys(payload).join(', ')}`);
      Logger.log(`   Error: ${handlerError.message}`);
      Logger.log(`   Error type: ${handlerError.name}`);
      Logger.log(`   Stack trace: ${handlerError.stack || 'No stack trace available'}`);
      
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: `🚨 ${functionName}: Handler Error - ${requestContext.handlerCalled}`,
        htmlBody: `
          <h2>🚨 Handler Error in ${functionName}</h2>
          <p><strong>Timestamp:</strong> ${timestamp}</p>
          <p><strong>Operation:</strong> Calling handler '${requestContext.handlerCalled}'</p>
          <p><strong>Request Type:</strong> ${requestContext.requestType}</p>
          <p><strong>Payload Keys:</strong> ${Object.keys(payload).join(', ')}</p>
          <p><strong>Error:</strong> ${handlerError.message}</p>
          <p><strong>Error Type:</strong> ${handlerError.name}</p>
          <h3>Stack Trace:</h3>
          <pre>${handlerError.stack || 'No stack trace available'}</pre>
          <h3>Full Payload:</h3>
          <pre>${JSON.stringify(payload, null, 2)}</pre>
        `
      });
      
      return createErrorResponse({
        status: 'error',
        message: `Handler error: ${handlerError.message}`,
        handler: requestContext.handlerCalled,
        error: handlerError.message,
        context: errorContext
      });
    }
    
  } catch (err) {
    const duration = new Date().getTime() - startTime;
    const errorContext = {
      function: functionName,
      operation: 'unexpected_error',
      durationMs: duration,
      requestContext: requestContext,
      error: err.message,
      errorName: err.name,
      stack: err.stack
    };
    
    Logger.log(`💥 [${timestamp}] === UNEXPECTED ERROR in ${functionName} ===`);
    Logger.log(`   Duration: ${duration}ms`);
    Logger.log(`   Error: ${err.message}`);
    Logger.log(`   Error type: ${err.name}`);
    Logger.log(`   Stack trace: ${err.stack || 'No stack trace available'}`);
    Logger.log(`   Request context: ${JSON.stringify(requestContext, null, 2)}`);
    
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `🚨 ${functionName}: Unexpected Error`,
      htmlBody: `
        <h2>🚨 Unexpected Error in ${functionName}</h2>
        <p><strong>Timestamp:</strong> ${timestamp}</p>
        <p><strong>Duration:</strong> ${duration}ms</p>
        <p><strong>Error:</strong> ${err.message}</p>
        <p><strong>Error Type:</strong> ${err.name}</p>
        <h3>Stack Trace:</h3>
        <pre>${err.stack || 'No stack trace available'}</pre>
        <h3>Request Context:</h3>
        <pre>${JSON.stringify(requestContext, null, 2)}</pre>
        <h3>Full Request:</h3>
        <pre>${JSON.stringify(e, null, 2)}</pre>
      `
    });
    
    return createErrorResponse({
      status: 'error',
      message: 'Internal server error',
      details: String(err),
      context: errorContext
    });
  } finally {
    const duration = new Date().getTime() - startTime;
    const endTimestamp = new Date().toISOString();
    Logger.log(`🏁 [${endTimestamp}] === EXITING ${functionName} ===`);
    Logger.log(`   Duration: ${duration}ms`);
  }
}

/**
 * Determine request type based on payload
 * @param {Object} payload - Parsed request payload
 * @returns {string} - Request type: 'CHECK_WAITLIST' or 'UNKNOWN'
 */
function determineRequestType(e, payload) {
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
