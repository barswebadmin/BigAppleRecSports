/**
 * DoPost handler
 * Orchestrates POST requests (signup) using services
 */

import { handleWaitlistSignup } from '../services/handleSignups.js';
import { calculateWaitlistPositionsForPlayer } from '../services/calculateWaitlistPositions.js';
import { PageRender } from '../ui/renderPages.js';
import { SlackClient } from '../integrations/SlackClient.js';

/**
 * Handle doPost request for waitlist signup
 * @param {SheetsClient} sheetsClient - Initialized SheetsClient instance
 * @param {string} firstName - First name
 * @param {string} lastName - Last name
 * @param {string} email - Email address
 * @param {string} phone - Phone number
 * @param {string} customerId - Shopify customer ID
 * @param {string} productId - Product ID
 * @param {string} league - Product/league name
 * @param {string} source - Source of request
 * @returns {GoogleAppsScript.HTML.HtmlOutput} HTML response
 */
export function handleDoPost(sheetsClient, firstName, lastName, email, phone, customerId, productId, league, source) {
  const pageRender = new PageRender();
  const slackClient = new SlackClient();
  const requestStart = Date.now();

  // Start operation tracking
  slackClient.sendStepStart('DoPost Handler', {
    firstName,
    lastName,
    email: email ? '[REDACTED]' : null,
    phone: phone ? '[REDACTED]' : null,
    customerId,
    productId,
    league,
    source,
    timestamp: new Date().toISOString()
  });

  try {
    // Step 1: Handle signup through service
    slackClient.sendStepStart('Execute Signup Service', {
      productId,
      league,
      hasEmail: !!email,
      hasCustomerId: !!customerId,
      source
    });

    const signupData = {
      firstName,
      lastName,
      email,
      phone,
      customerId,
      productId,
      productName: league,
      submittedAt: new Date().toISOString(),
      source
    };

    const signupResult = handleWaitlistSignup(sheetsClient, signupData);

    slackClient.sendStepSuccess('Execute Signup Service', { signupResult }, {
      productId,
      position: signupResult?.position,
      alreadyExists: signupResult?.alreadyExists
    });

    // Step 2: Get all positions for display after signup
    slackClient.sendStepStart('Get Position Data for Display', {
      email: !!email,
      customerId: !!customerId,
      productId
    });

    const waitlistPositionsForPlayer = calculateWaitlistPositionsForPlayer(sheetsClient, email, customerId, productId);

    slackClient.sendStepSuccess('Get Position Data for Display',
      { positionsFound: waitlistPositionsForPlayer?.length || 0 },
      { productId, positions: waitlistPositionsForPlayer }
    );

    // Step 3: Render response page
    slackClient.sendStepStart('Render Success Page', {
      positionsCount: waitlistPositionsForPlayer?.length || 0,
      productId,
      source
    });

    const htmlResponse = pageRender.renderPositionsPage(waitlistPositionsForPlayer, productId, source);

    slackClient.sendStepSuccess('Render Success Page', { success: true }, {
      productId,
      source,
      responseGenerated: !!htmlResponse
    });

    // Operation summary
    slackClient.sendOperationSummary('DoPost Waitlist Signup', true, {
      productId,
      league,
      signupResult,
      positionsCount: waitlistPositionsForPlayer?.length || 0,
      source
    }, Date.now() - requestStart);

    return htmlResponse;

  } catch (error) {
    slackClient.sendStepFailure('DoPost Handler', error,
      {
        firstName,
        lastName,
        email: !!email,
        phone: !!phone,
        customerId,
        productId,
        league,
        source
      },
      {
        step: 'main_handler',
        requestDuration: Date.now() - requestStart
      }
    );

    slackClient.sendOperationSummary('DoPost Waitlist Signup', false,
      { error: error.message, productId, league, source },
      Date.now() - requestStart
    );

    slackClient.sendStepStart('Render Error Page', { errorMessage: error.message });

    const errorResponse = pageRender.renderErrorPage(`Signup failed: ${error.message}`, error);

    slackClient.sendStepSuccess('Render Error Page', { success: true }, {
      errorMessage: error.message,
      responseGenerated: !!errorResponse
    });

    return errorResponse;
  }
}