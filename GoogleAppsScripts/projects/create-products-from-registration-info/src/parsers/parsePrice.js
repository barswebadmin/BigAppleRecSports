/**
 * Price parsing functions for parse-registration-info
 * Extract integer price values from text or numbers
 * Handles optional leading $ sign
 *
 * @fileoverview Price extraction and formatting
 */

/**
 * Parse price from text or number, removing currency symbols ($) and converting to integer
 * @param {string|number} priceInput - Price input (string with optional $, or number)
 * @returns {{price: number|null}} Integer price value or null
 */
export function parsePrice(priceInput) {
  // Handle null, undefined, or empty string
  if (priceInput === null || priceInput === undefined || (typeof priceInput === 'string' && !priceInput.trim())) {
    return { price: null };
  }

  // Handle number input directly
  if (typeof priceInput === 'number') {
    if (Number.isNaN(priceInput)) {
      return { price: null };
    }
    // Convert to integer
    return { price: Math.round(priceInput) };
  }

  // Handle string input
  const inputStr = priceInput.toString().trim();

  // Remove dollar signs and any whitespace
  const clean = inputStr.replace(/[$\s]/g, '');
  
  // Parse as integer
  const num = parseInt(clean, 10);

  if (Number.isNaN(num)) {
    // Could not parse as valid number - return null
    return { price: null };
  }

  return { price: num };
}
