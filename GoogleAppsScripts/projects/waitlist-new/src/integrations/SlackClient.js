/**
 * Slack client for notifications
 * Handles all Slack API communications with comprehensive debugging
 */

import { getSlackConfig } from '../config.js';

export class SlackClient {
  constructor() {
    this.config = getSlackConfig();
  }

  /**
   * Send message using Slack webhook with smart filtering
   * @param {string} message - Message text to send
   * @returns {boolean} Success status
   */
  sendMessage(message) {
    // PERFORMANCE: Smart filtering to reduce Slack spam
    // Only send: final results, failures, and critical events
    const isImportant =
      message.includes('✅ **DoGet Request Completed Successfully**') ||
      message.includes('✅ **Signup Request Completed Successfully**') ||
      message.includes('❌') ||  // Any failure
      message.includes('🚨') ||  // Errors
      message.includes('FAILURE') ||
      message.includes('Exception') ||
      message.includes('Error:');

    if (!isImportant) {
      return true; // Skip non-critical messages
    }

    try {
      if (!this.config.enabled || !this.config.webhookUrl) {
        // Slack disabled or not configured - fail silently
        return false;
      }

      const payload = {
        text: message
      };

      const response = UrlFetchApp.fetch(this.config.webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      });

      const responseText = response.getContentText();
      return responseText === 'ok';
    } catch (error) {
      // Log error but don't break the main operation
      console.error('Slack error (non-blocking):', error.message);
      return false;
    }
  }

  /**
   * Send an error message with formatting
   * @param {string} title - Error title
   * @param {Error|string} error - Error object or message
   * @param {Object} context - Additional context data
   */
  sendError(title, error, context = null) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    const stack = error instanceof Error ? error.stack : null;

    let message = `🚨 **${title}**\n\n**Error:** ${errorMessage}`;

    if (stack) {
      message += `\n\n**Stack:** \`\`\`${stack}\`\`\``;
    }

    if (context) {
      message += `\n\n**Context:**\n\`\`\`json\n${JSON.stringify(context, null, 2)}\n\`\`\``;
    }

    return this.sendMessage(message);
  }

  /**
   * Send a debug message with formatting
   * @param {string} title - Debug title
   * @param {Object} data - Debug data
   */
  sendDebug(title, data) {
    const message = `🔍 **${title}**\n\n**Data:**\n\`\`\`json\n${JSON.stringify(data, null, 2)}\n\`\`\``;
    return this.sendMessage(message);
  }

  /**
   * Send an info message
   * @param {string} message - Info message to send
   */
  sendInfo(message) {
    return this.sendMessage(`ℹ️ ${message}`);
  }

  /**
   * Send a success message
   * @param {string} message - Success message to send
   */
  sendSuccess(message) {
    return this.sendMessage(`✅ ${message}`);
  }

  /**
   * Send a warning message
   * @param {string} message - Warning message to send
   */
  sendWarning(message) {
    return this.sendMessage(`⚠️ ${message}`);
  }

  /**
   * COMPREHENSIVE DEBUG LOGGING METHODS
   * For step-by-step operation tracking with detailed context
   */

  /**
   * Start of a processing step
   * @param {string} stepName - Name of the step starting
   * @param {Object} variables - Current variables and context
   */
  sendStepStart(stepName, variables = {}) {
    const message = `🚀 **STEP START: ${stepName}**\n\n` +
      `**Variables:**\n\`\`\`json\n${JSON.stringify(variables, null, 2)}\n\`\`\`\n\n` +
      `**Timestamp:** ${new Date().toISOString()}`;

    return this.sendMessage(message, this.debugChannel);
  }

  /**
   * Successful completion of a step
   * @param {string} stepName - Name of the completed step
   * @param {Object} result - Result data from the step
   * @param {Object} variables - Updated variables after step
   */
  sendStepSuccess(stepName, result = {}, variables = {}) {
    const message = `✅ **STEP SUCCESS: ${stepName}**\n\n` +
      `**Result:**\n\`\`\`json\n${JSON.stringify(result, null, 2)}\n\`\`\`\n\n` +
      `**Variables:**\n\`\`\`json\n${JSON.stringify(variables, null, 2)}\n\`\`\`\n\n` +
      `**Timestamp:** ${new Date().toISOString()}`;

    return this.sendMessage(message, this.debugChannel);
  }

  /**
   * Failed step with detailed error information
   * @param {string} stepName - Name of the failed step
   * @param {Error|string} error - Error that occurred
   * @param {Object} variables - Variables at time of failure
   * @param {Object} context - Additional context about the failure
   */
  sendStepFailure(stepName, error, variables = {}, context = {}) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    const stack = error instanceof Error ? error.stack : null;

    let message = `❌ **STEP FAILURE: ${stepName}**\n\n` +
      `**Error:** ${errorMessage}\n\n` +
      `**Variables:**\n\`\`\`json\n${JSON.stringify(variables, null, 2)}\n\`\`\``;

    if (Object.keys(context).length > 0) {
      message += `\n\n**Context:**\n\`\`\`json\n${JSON.stringify(context, null, 2)}\n\`\`\``;
    }

    if (stack) {
      message += `\n\n**Stack Trace:**\n\`\`\`${stack}\`\`\``;
    }

    message += `\n\n**Timestamp:** ${new Date().toISOString()}`;

    return this.sendMessage(message, this.debugChannel);
  }

  /**
   * Operation summary with full context
   * @param {string} operationName - Name of the overall operation
   * @param {boolean} success - Whether operation was successful
   * @param {Object} summary - Summary data
   * @param {number} duration - Operation duration in ms
   */
  sendOperationSummary(operationName, success, summary = {}, duration = null) {
    const emoji = success ? '✅' : '❌';
    const status = success ? 'SUCCESS' : 'FAILURE';

    let message = `${emoji} **OPERATION ${status}: ${operationName}**\n\n` +
      `**Summary:**\n\`\`\`json\n${JSON.stringify(summary, null, 2)}\n\`\`\``;

    if (duration) {
      message += `\n\n**Duration:** ${duration}ms`;
    }

    message += `\n\n**Timestamp:** ${new Date().toISOString()}`;

    return this.sendMessage(message, this.debugChannel);
  }

  /**
   * Variable tracking during processing
   * @param {string} location - Where in the code this is called from
   * @param {Object} variables - Current variable state
   */
  sendVariableState(location, variables = {}) {
    const message = `📊 **VARIABLE STATE: ${location}**\n\n` +
      `**Variables:**\n\`\`\`json\n${JSON.stringify(variables, null, 2)}\n\`\`\`\n\n` +
      `**Timestamp:** ${new Date().toISOString()}`;

    return this.sendMessage(message, this.debugChannel);
  }

  /**
   * Validation results with detailed information
   * @param {string} validationType - Type of validation performed
   * @param {boolean} isValid - Whether validation passed
   * @param {Object} input - Input that was validated
   * @param {Array|string} errors - Validation errors if any
   */
  sendValidationResult(validationType, isValid, input = {}, errors = []) {
    const emoji = isValid ? '✅' : '❌';
    const status = isValid ? 'PASSED' : 'FAILED';

    let message = `${emoji} **VALIDATION ${status}: ${validationType}**\n\n` +
      `**Input:**\n\`\`\`json\n${JSON.stringify(input, null, 2)}\n\`\`\``;

    if (!isValid && errors.length > 0) {
      const errorText = Array.isArray(errors) ? errors.join(', ') : String(errors);
      message += `\n\n**Errors:** ${errorText}`;
    }

    message += `\n\n**Timestamp:** ${new Date().toISOString()}`;

    return this.sendMessage(message, this.debugChannel);
  }
}