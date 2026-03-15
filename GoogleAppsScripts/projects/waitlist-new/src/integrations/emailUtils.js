/**
 * Email utilities for Google Apps Script
 * Simple functions for sending emails via GmailApp
 */

/**
 * Send waitlist confirmation email
 */
export function sendWaitlistConfirmationEmail(email, firstName, productName, position) {
  const subject = `You're on the waitlist for ${productName}!`;
  const body = `Hi ${firstName},

You've successfully joined the waitlist for ${productName}.

Your position: #${position}

We'll notify you when a spot becomes available!

Best regards,
Big Apple Rec Sports`;

  try {
    GmailApp.sendEmail(email, subject, body);
    return { success: true };
  } catch (error) {
    console.error('Failed to send confirmation email:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Send position update email
 */
export function sendPositionUpdateEmail(email, firstName, productName, newPosition) {
  const subject = `Your waitlist position has been updated - ${productName}`;
  const body = `Hi ${firstName},

Your position on the waitlist for ${productName} has been updated.

New position: #${newPosition}

Best regards,
Big Apple Rec Sports`;

  try {
    GmailApp.sendEmail(email, subject, body);
    return { success: true };
  } catch (error) {
    console.error('Failed to send position update email:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Send spot available email
 */
export function sendSpotAvailableEmail(email, firstName, productName) {
  const subject = `A spot is now available - ${productName}!`;
  const body = `Hi ${firstName},

Great news! A spot has become available for ${productName}.

Please register soon as spots are first-come, first-served.

Best regards,
Big Apple Rec Sports`;

  try {
    GmailApp.sendEmail(email, subject, body);
    return { success: true };
  } catch (error) {
    console.error('Failed to send spot available email:', error);
    return { success: false, error: error.message };
  }
}