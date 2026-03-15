/**
 * Position calculation service
 * Handles finding and calculating waitlist positions for users
 */

import { SlackClient } from '../integrations/SlackClient.js';

// Note: Column mapping moved to config.js for centralization


// =============================================================================
// INTERNAL SHARED HELPERS (not exported)
// =============================================================================

/**
 * Normalize and validate user identifiers
 * @param {string} email - User's email
 * @param {string} customerId - User's customer ID
 * @returns {Object|null} Normalized identifiers or null if both invalid
 */
function normalizeUserIdentifiers(email, customerId) {
  const emailLower = email?.toLowerCase()?.trim() || null;
  const customerIdTrim = customerId?.trim() || null;

  if (!emailLower && !customerIdTrim) {
    return null;
  }

  return { emailLower, customerIdTrim };
}

/**
 * Normalize a parsed row for consistent data types
 * @param {Object} parsedRow - Already parsed row object
 * @returns {Object} Normalized row data
 */
function normalizeSheetRow(parsedRow) {
  return {
    ...parsedRow,
    productId: parsedRow.productId ? parsedRow.productId.toString().trim() : '',
    productName: parsedRow.productName ? parsedRow.productName.toString().trim() : '',
    email: parsedRow.email ? parsedRow.email.toString().toLowerCase().trim() : '',
    customerId: parsedRow.customerId ? parsedRow.customerId.toString().trim() : '',
    submittedAt: parsedRow.submittedAt || '',
    status: parsedRow.status ? parsedRow.status.toString().trim() : '',
  };
}


/**
 * Check if entry matches user identifiers
 * @param {Object} row - Parsed row data
 * @param {string} emailLower - Normalized email
 * @param {string} customerIdTrim - Normalized customer ID
 * @returns {boolean} True if entry matches user
 */
function entryMatchesUser(row, emailLower, customerIdTrim) {
  const normalized = normalizeSheetRow(row);
  return (emailLower && normalized.email === emailLower) ||
         (customerIdTrim && normalized.customerId === customerIdTrim);
}

/**
 * Sort entries by timestamp (earliest first)
 * @param {Array} entries - Array of entry objects
 * @returns {Array} Sorted entries
 */
function sortEntriesByTimestamp(entries) {
  return entries.sort((a, b) => {
    if (!a.submittedAt || !b.submittedAt) return 0;
    return new Date(a.submittedAt) - new Date(b.submittedAt);
  });
}

/**
 * Find user's position within sorted entries
 * @param {Array} sortedEntries - Sorted entries array
 * @param {string} emailLower - Normalized email
 * @param {string} customerIdTrim - Normalized customer ID
 * @returns {number} Position (1-based) or 0 if not found
 */
function findUserPositionInEntries(sortedEntries, emailLower, customerIdTrim) {
  for (let i = 0; i < sortedEntries.length; i++) {
    const entry = sortedEntries[i];
    if (entryMatchesUser(entry, emailLower, customerIdTrim)) {
      return i + 1; // Position is 1-based
    }
  }
  return 0; // Not found
}


// =============================================================================
// PUBLIC FUNCTIONS (exported)
// =============================================================================

/**
 * Calculate waitlist positions for a player using optimized product-specific lookup
 * Returns null if no match found for the specific productId or if no email/customerId provided
 * @param {SheetsClient} sheetsClient - Initialized SheetsClient instance
 * @param {string} email - Player's email address
 * @param {string} customerId - Player's Shopify customer ID
 * @param {string} productId - Product ID to check for match
 * @returns {Array<Object>|null} Array of {productId, productName, position} objects or null if no match for productId
 */
export function calculateWaitlistPositionsForPlayer(sheetsClient, email, customerId, productId) {
  const slackClient = new SlackClient();

  slackClient.sendStepStart('Calculate Waitlist Positions', {
    email: email ? '[REDACTED]' : null,
    customerId,
    productId
  });

  const userIds = normalizeUserIdentifiers(email, customerId);
  if (!userIds) {
    slackClient.sendStepFailure('Calculate Waitlist Positions', new Error('No valid user identifiers'),
      { email: !!email, customerId: !!customerId });
    return null;
  }

  const { emailLower, customerIdTrim } = userIds;

  try {
    // Get optimized product-specific data
    slackClient.sendStepStart('Get Product Data', { productId });

    const productData = sheetsClient.getProductData(productId);

    slackClient.sendVariableState('Product Data Retrieved', {
      hasProductData: !!productData,
      entriesCount: productData?.entries?.length || 0
    });

    if (!productData || productData.entries.length === 0) {
      slackClient.sendStepFailure('Get Product Data', new Error('No product data found'),
        { productId, hasData: !!productData });
      return null; // No data for this product
    }

    slackClient.sendStepSuccess('Get Product Data',
      { entriesCount: productData.entries.length },
      { productId }
    );

    // Check for user match using optimized lookups
    slackClient.sendStepStart('Find User Entry', {
      hasEmail: !!emailLower,
      hasCustomerId: !!customerIdTrim,
      productId
    });

    let userEntry = null;
    if (emailLower && productData.byEmail.has(emailLower)) {
      userEntry = productData.byEmail.get(emailLower);
    } else if (customerIdTrim && productData.byCustomerId.has(customerIdTrim)) {
      userEntry = productData.byCustomerId.get(customerIdTrim);
    }

    if (!userEntry) {
      slackClient.sendStepFailure('Find User Entry', new Error('User not found in product data'),
        { productId, hasEmail: !!emailLower, hasCustomerId: !!customerIdTrim });
      return null; // No match found for this productId
    }

    slackClient.sendStepSuccess('Find User Entry', { userFound: true }, { productId });

    // Calculate position by finding user's entry in sorted list
    slackClient.sendStepStart('Calculate Position', { productId });

    const activeEntries = productData.entries.filter(entry =>
      !entry.status || entry.status === ''
    );

    slackClient.sendVariableState('Active Entries Filter', {
      totalEntries: productData.entries.length,
      activeEntries: activeEntries.length
    });

    const sortedEntries = sortEntriesByTimestamp(activeEntries);
    const position = findUserPositionInEntries(sortedEntries, emailLower, customerIdTrim);

    if (position === 0) {
      slackClient.sendStepFailure('Calculate Position', new Error('User not found in active entries'),
        { productId, activeEntries: activeEntries.length });
      return null; // User not found in active entries
    }

    slackClient.sendStepSuccess('Calculate Position', { position }, { productId });

    // Also get positions for any other products this user is on
    slackClient.sendStepStart('Get All User Products', {
      email: !!email,
      customerId: !!customerId
    });

    const allPositions = getAllProductsForPlayer(sheetsClient, email, customerId);

    slackClient.sendStepSuccess('Get All User Products',
      { productsCount: allPositions.length },
      { allPositions }
    );

    return allPositions;

  } catch (error) {
    slackClient.sendStepFailure('Calculate Waitlist Positions', error,
      { productId, email: !!email, customerId: !!customerId },
      { step: 'main_calculation' }
    );
    return null;
  }
}

/**
 * Get all products and positions for a player across all waitlists
 * @param {SheetsClient} sheetsClient - Initialized SheetsClient instance
 * @param {string} email - Player's email address
 * @param {string} customerId - Player's Shopify customer ID
 * @returns {Array<Object>} Array of {productId, productName, position} objects
 */
export function getAllProductsForPlayer(sheetsClient, email, customerId) {
  const userIds = normalizeUserIdentifiers(email, customerId);
  if (!userIds) return [];

  const { emailLower, customerIdTrim } = userIds;
  const results = [];

  try {
    // Get all product data
    const allProductsData = sheetsClient.getAllProductsData();

    for (const [productId, productData] of allProductsData) {
      if (!productData || productData.entries.length === 0) continue;

      // Check for user match
      let userEntry = null;
      if (emailLower && productData.byEmail.has(emailLower)) {
        userEntry = productData.byEmail.get(emailLower);
      } else if (customerIdTrim && productData.byCustomerId.has(customerIdTrim)) {
        userEntry = productData.byCustomerId.get(customerIdTrim);
      }

      if (!userEntry || (userEntry.status && userEntry.status !== '')) {
        continue; // No match or user is not active on this waitlist
      }

      // Calculate position
      const activeEntries = productData.entries.filter(entry =>
        !entry.status || entry.status === ''
      );

      const sortedEntries = sortEntriesByTimestamp(activeEntries);
      const position = findUserPositionInEntries(sortedEntries, emailLower, customerIdTrim);

      if (position > 0) {
        results.push({
          productId: productId,
          productName: userEntry.productName || `Product ${productId}`,
          position: position
        });
      }
    }

    return results.sort((a, b) => a.productName.localeCompare(b.productName));

  } catch (error) {
    console.error('Error getting all products for player:', error);
    return [];
  }
}

/**
 * Calculate waitlist position for a specific email and product (backward compatibility)
 * @param {SheetsClient} sheetsClient - Initialized SheetsClient instance
 * @param {string} email - The email to search for
 * @param {string} productId - The product ID to search for
 * @returns {number|null} Position (1-based) or null if not found
 */
export function calculateWaitlistPosition(sheetsClient, email, productId) {
  const allProducts = getAllProductsForPlayer(sheetsClient, email, null);
  const product = allProducts.find(p => p.productId === productId);
  return product ? product.position : null;
}

/**
 * Get summary statistics for a product's waitlist
 * @param {SheetsClient} sheetsClient - Initialized SheetsClient instance
 * @param {string} productId - Product ID to get stats for
 * @returns {Object|null} Stats object with totalEntries and activeWaitlist
 */
export function getProductWaitlistStats(sheetsClient, productId) {
  try {
    const productData = sheetsClient.getProductData(productId);
    if (!productData) return null;

    const totalCount = productData.entries.length;
    let activeCount = 0;

    for (const entry of productData.entries) {
      if (!entry.status || entry.status === '') {
        activeCount++;
      }
    }

    return {
      productId,
      totalEntries: totalCount,
      activeWaitlist: activeCount
    };

  } catch {
    return null;
  }
}

/**
 * Check if user exists in any waitlist
 * @param {SheetsClient} sheetsClient - Initialized SheetsClient instance
 * @param {string} email - User's email
 * @param {string} customerId - User's customer ID
 * @returns {boolean} True if user exists in any waitlist
 */
export function checkUserExistsInAnyWaitlist(sheetsClient, email, customerId) {
  const allProducts = getAllProductsForPlayer(sheetsClient, email, customerId);
  return allProducts.length > 0;
}