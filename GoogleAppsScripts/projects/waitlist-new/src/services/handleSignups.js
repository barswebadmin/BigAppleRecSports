/**
 * Signup service for waitlist management
 * Handles waitlist signup operations and coordination with external systems
 */

import { SlackClient } from '../integrations/SlackClient.js';
import { sendWaitlistConfirmationEmail } from '../integrations/emailUtils.js';
import { calculateWaitlistPosition } from './calculateWaitlistPositions.js';
import { validateSignupParams } from './validateInputs.js';

/**
 * Handle complete waitlist signup process
 * @param {SheetsClient} sheetsClient - Initialized SheetsClient instance
 * @param {Object} signupData - Signup form data
 * @returns {Object} Result with success status and position
 */
export function handleWaitlistSignup(sheetsClient, signupData) {
  const slackClient = new SlackClient();
  const operationStart = Date.now();

  // Start operation logging
  slackClient.sendStepStart('Waitlist Signup Process', {
    signupData: signupData,
    timestamp: new Date().toISOString()
  });

  try {
    // Step 1: Validate signup parameters
    slackClient.sendStepStart('Input Validation', { signupData });

    const validation = validateSignupParams(signupData);

    slackClient.sendValidationResult('Signup Parameters', validation.valid, signupData,
      validation.valid ? [] : [validation.message]);

    if (!validation.valid) {
      slackClient.sendStepFailure('Input Validation', new Error(validation.message),
        { signupData, validation });
      throw new Error(validation.message);
    }

    const validatedData = validation.data;

    slackClient.sendStepSuccess('Input Validation', { validatedData },
      { originalData: signupData, validatedData });

    // Step 2: Check existing entries
    slackClient.sendStepStart('Duplicate Check', {
      productId: validatedData.productId,
      email: validatedData.email,
      customerId: validatedData.customerId
    });

    const productData = sheetsClient.getProductData(validatedData.productId);
    slackClient.sendVariableState('After getProductData', { productData: !!productData });

    const existingEntry = checkExistingEntry(productData, validatedData.email, validatedData.customerId);

    if (existingEntry) {
      slackClient.sendStepSuccess('Duplicate Check',
        { existingEntry, action: 'returning_current_position' },
        { productId: validatedData.productId, existingEntry }
      );

      // User already on waitlist - return current position
      const currentPosition = calculateWaitlistPosition(sheetsClient, validatedData.email, validatedData.productId);

      slackClient.sendStepSuccess('Position Calculation', { currentPosition },
        { email: validatedData.email, productId: validatedData.productId }
      );

      const result = {
        success: true,
        alreadyExists: true,
        position: currentPosition || 1,
        message: 'You are already on the waitlist for this product'
      };

      slackClient.sendOperationSummary('Waitlist Signup (Duplicate)', true, result, Date.now() - operationStart);
      return result;
    }

    slackClient.sendStepSuccess('Duplicate Check', { existingEntry: null, action: 'proceeding_with_signup' });

    // Step 3: Add user to waitlist
    slackClient.sendStepStart('Insert Waitlist Entry', {
      productId: validatedData.productId,
      validatedData
    });

    const insertResult = sheetsClient.insertWaitlistEntry(validatedData.productId, validatedData);
    const position = insertResult.position;

    slackClient.sendStepSuccess('Insert Waitlist Entry', { insertResult, position },
      { productId: validatedData.productId, position }
    );

    // Step 4: Send notifications asynchronously
    slackClient.sendStepStart('Send Notifications', {
      email: validatedData.email,
      firstName: validatedData.firstName,
      productName: validatedData.productName,
      position
    });

    sendNotifications(validatedData, position, slackClient);

    const result = {
      success: true,
      alreadyExists: false,
      position: position,
      message: `Successfully joined waitlist at position #${position}`
    };

    slackClient.sendOperationSummary('Waitlist Signup (New)', true, result, Date.now() - operationStart);
    return result;

  } catch (error) {
    // Log detailed error to Slack
    slackClient.sendStepFailure('Waitlist Signup Process', error,
      { signupData, timestamp: new Date().toISOString() },
      { step: 'main_process', operationDuration: Date.now() - operationStart }
    );

    slackClient.sendOperationSummary('Waitlist Signup', false,
      { error: error.message, signupData }, Date.now() - operationStart);

    throw error;
  }
}

/**
 * Check if user already exists in product data
 * @param {Object} productData - Product data from SheetsClient
 * @param {string} email - User's email
 * @param {string} customerId - User's customer ID
 * @returns {Object|null} Existing entry or null
 */
function checkExistingEntry(productData, email, customerId) {
  if (!productData || !productData.entries) return null;

  const emailLower = email?.toLowerCase()?.trim();
  const customerIdTrim = customerId?.toString()?.trim();

  // Check email lookup first
  if (emailLower && productData.byEmail?.has(emailLower)) {
    return productData.byEmail.get(emailLower);
  }

  // Check customer ID lookup
  if (customerIdTrim && productData.byCustomerId?.has(customerIdTrim)) {
    return productData.byCustomerId.get(customerIdTrim);
  }

  return null;
}

/**
 * Send confirmation notifications
 * @param {Object} entryData - Entry data
 * @param {number} position - Position on waitlist
 * @param {SlackClient} slackClient - SlackClient for logging
 */
function sendNotifications(entryData, position, slackClient) {
  try {
    slackClient.sendStepStart('Email Confirmation', {
      email: entryData.email,
      firstName: entryData.firstName,
      productName: entryData.productName,
      position
    });

    // Send email confirmation
    const emailResult = sendWaitlistConfirmationEmail(
      entryData.email,
      entryData.firstName,
      entryData.productName,
      position
    );

    if (emailResult.success) {
      slackClient.sendStepSuccess('Email Confirmation', { emailResult },
        { recipient: entryData.email, position }
      );
    } else {
      slackClient.sendStepFailure('Email Confirmation', new Error(emailResult.error || 'Email failed'),
        { recipient: entryData.email, position, emailResult }
      );
    }

  } catch (error) {
    slackClient.sendStepFailure('Send Notifications', error,
      { entryData, position },
      { step: 'email_notification' }
    );
  }
}