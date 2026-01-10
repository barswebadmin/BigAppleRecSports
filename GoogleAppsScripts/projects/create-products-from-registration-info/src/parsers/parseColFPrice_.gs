/**
 * Price parsing functions for parse-registration-info
 * Extract numeric price values from text
 *
 * @fileoverview Price extraction and formatting
 */

/**
 * Parse price from text, removing currency symbols ($) and using parseFloat
 * @param {string|number} s - Price input (string or number)
 * @returns {{price: number|null}} Price value or null
 */
function parseColFPrice_(s) {
  // Price parsing: handles $ symbols and uses parseFloat for conversion

  // Handle null, undefined, or empty string
  if (s === null || s === undefined || (typeof s === 'string' && !s.trim())) {
    return { price: null };
  }

  // Handle number input directly
  if (typeof s === 'number') {
    if (Number.isNaN(s)) {
      return { price: null };
    }
    // Successfully parsed number
    return { price: s };
  }

  // Handle string input
  const inputStr = s.toString().trim();

  // Check if input contains only digits and dollar signs
  const validCharsRegex = /^[\d$\.]+$/;
  if (!validCharsRegex.test(inputStr)) {
    // Contains invalid characters - return null
    return { price: null };
  }

  // Remove dollar signs and parse as number
  const clean = inputStr.replace(/\$/g, '');
  const num = parseFloat(clean);

  if (Number.isNaN(num)) {
    // Could not parse as valid number - return null
    return { price: null };
  }


  return { price: num };
}
