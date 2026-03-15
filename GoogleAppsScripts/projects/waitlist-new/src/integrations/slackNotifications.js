/**
 * Simple Slack notification function using webhook URL
 */

/**
 * Send message to Slack using webhook URL from script properties
 * Smart filtering: only send final results and failures to avoid spam
 * @param {string} message - Message to send to Slack
 * @returns {boolean} Success status
 */
export function sendToSlack(message) {
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
    const webhookUrl = PropertiesService.getScriptProperties().getProperty('SLACK_WEBHOOK_URL');

    if (!webhookUrl) {
      // Slack not configured - fail silently
      return false;
    }

    const payload = {
      text: message
    };

    const response = UrlFetchApp.fetch(webhookUrl, {
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