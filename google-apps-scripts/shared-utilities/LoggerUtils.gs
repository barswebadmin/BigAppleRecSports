/**
 * Robust Logging Utility for Google Apps Script
 * Provides structured logging with timestamps, error tracking, and email notifications
 * 
 * Usage:
 *   import { logInfo, logError, logWarning, logSuccess, logFunctionEntry, logFunctionExit } from './shared-utilities/LoggerUtils';
 * 
 *   logFunctionEntry('myFunction', { param1: 'value' });
 *   logInfo('Processing data...');
 *   logError('Failed to process', error);
 *   logFunctionExit('myFunction', { result: 'success' });
 */

/**
 * Log levels
 */
const LOG_LEVELS = {
  DEBUG: 'DEBUG',
  INFO: 'INFO',
  WARNING: 'WARNING',
  ERROR: 'ERROR',
  SUCCESS: 'SUCCESS'
};

/**
 * Get formatted timestamp
 */
function getTimestamp() {
  const now = new Date();
  return Utilities.formatDate(now, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss.SSS');
}

/**
 * Format log message with timestamp and level
 */
function formatLogMessage(level, message, context = {}) {
  const timestamp = getTimestamp();
  const contextStr = Object.keys(context).length > 0 
    ? ` | Context: ${JSON.stringify(context)}` 
    : '';
  return `[${timestamp}] [${level}] ${message}${contextStr}`;
}

/**
 * Log info message
 */
function logInfo(message, context = {}) {
  const formatted = formatLogMessage(LOG_LEVELS.INFO, message, context);
  Logger.log(formatted);
  console.log(formatted);
}

/**
 * Log success message
 */
function logSuccess(message, context = {}) {
  const formatted = formatLogMessage(LOG_LEVELS.SUCCESS, `✅ ${message}`, context);
  Logger.log(formatted);
  console.log(formatted);
}

/**
 * Log warning message
 */
function logWarning(message, context = {}) {
  const formatted = formatLogMessage(LOG_LEVELS.WARNING, `⚠️ ${message}`, context);
  Logger.log(formatted);
  console.warn(formatted);
}

/**
 * Log error message with stack trace
 */
function logError(message, error = null, context = {}) {
  const errorContext = { ...context };
  
  if (error) {
    errorContext.errorMessage = error.message || String(error);
    errorContext.errorStack = error.stack || 'No stack trace available';
    if (error.name) {
      errorContext.errorName = error.name;
    }
  }
  
  const formatted = formatLogMessage(LOG_LEVELS.ERROR, `❌ ${message}`, errorContext);
  Logger.log(formatted);
  console.error(formatted);
  
  // Log full error details
  if (error) {
    Logger.log(`   Error Details: ${JSON.stringify(errorContext, null, 2)}`);
  }
}

/**
 * Log function entry with parameters
 */
function logFunctionEntry(functionName, params = {}) {
  const context = {
    function: functionName,
    params: params
  };
  const formatted = formatLogMessage(LOG_LEVELS.DEBUG, `🚀 Entering: ${functionName}`, context);
  Logger.log(formatted);
  console.log(formatted);
}

/**
 * Log function exit with result
 */
function logFunctionExit(functionName, result = null, duration = null) {
  const context = {
    function: functionName,
    result: result
  };
  if (duration !== null) {
    context.durationMs = duration;
  }
  const formatted = formatLogMessage(LOG_LEVELS.DEBUG, `🏁 Exiting: ${functionName}`, context);
  Logger.log(formatted);
  console.log(formatted);
}

/**
 * Log API request
 */
function logApiRequest(method, url, headers = {}, body = null) {
  const context = {
    method: method,
    url: url,
    headers: headers,
    bodyLength: body ? (typeof body === 'string' ? body.length : JSON.stringify(body).length) : 0
  };
  const formatted = formatLogMessage(LOG_LEVELS.INFO, `📤 API Request: ${method} ${url}`, context);
  Logger.log(formatted);
  console.log(formatted);
}

/**
 * Log API response
 */
function logApiResponse(statusCode, headers = {}, body = null, duration = null) {
  const context = {
    statusCode: statusCode,
    headers: headers,
    bodyLength: body ? (typeof body === 'string' ? body.length : JSON.stringify(body).length) : 0
  };
  if (duration !== null) {
    context.durationMs = duration;
  }
  const statusEmoji = statusCode >= 200 && statusCode < 300 ? '✅' : '❌';
  const formatted = formatLogMessage(LOG_LEVELS.INFO, `${statusEmoji} API Response: ${statusCode}`, context);
  Logger.log(formatted);
  console.log(formatted);
}

/**
 * Log critical error and send email notification
 */
function logCriticalError(message, error = null, context = {}, emailRecipient = null) {
  logError(message, error, context);
  
  // Try to get debug email from properties if not provided
  if (!emailRecipient) {
    try {
      emailRecipient = PropertiesService.getScriptProperties().getProperty('DEBUG_EMAIL');
    } catch (e) {
      Logger.log('⚠️ Could not get DEBUG_EMAIL from properties');
    }
  }
  
  if (emailRecipient) {
    try {
      const errorDetails = {
        message: message,
        timestamp: getTimestamp(),
        context: context
      };
      
      if (error) {
        errorDetails.error = {
          message: error.message || String(error),
          stack: error.stack || 'No stack trace',
          name: error.name || 'UnknownError'
        };
      }
      
      MailApp.sendEmail({
        to: emailRecipient,
        subject: `🚨 CRITICAL ERROR: ${message}`,
        htmlBody: `
          <h2>🚨 Critical Error Detected</h2>
          <p><strong>Message:</strong> ${message}</p>
          <p><strong>Timestamp:</strong> ${errorDetails.timestamp}</p>
          <h3>Context:</h3>
          <pre>${JSON.stringify(errorDetails.context, null, 2)}</pre>
          ${error ? `
          <h3>Error Details:</h3>
          <pre>${JSON.stringify(errorDetails.error, null, 2)}</pre>
          ` : ''}
        `
      });
      
      Logger.log(`📧 Critical error email sent to ${emailRecipient}`);
    } catch (emailError) {
      Logger.log(`❌ Failed to send critical error email: ${emailError.message}`);
    }
  }
}

/**
 * Wrap function with automatic logging
 */
function withLogging(functionName, fn) {
  return function(...args) {
    const startTime = new Date().getTime();
    logFunctionEntry(functionName, { args: args });
    
    try {
      const result = fn.apply(this, args);
      const duration = new Date().getTime() - startTime;
      logFunctionExit(functionName, { success: true }, duration);
      return result;
    } catch (error) {
      const duration = new Date().getTime() - startTime;
      logError(`Error in ${functionName}`, error, { durationMs: duration });
      logFunctionExit(functionName, { success: false, error: error.message }, duration);
      throw error;
    }
  };
}
