/**
 * Price parsing functions for parse-registration-info
 * Extract numeric price values from text
 *
 * @fileoverview Price extraction and formatting
 */

/**
 * Parse price from text, removing currency symbols and formatting
 */
function parsePriceNumber_(s, unresolved) {
  if (!s || !s.trim()) return '';

  // Remove everything except numbers and decimal points
  const clean = s.replace(/[^0-9.]/g, '');
  const num = parseFloat(clean);

  if (isNaN(num)) {
    // Price not found - leave "price" in unresolved array
    return '';
  }

  // Successfully found price - remove from unresolved
  const index = unresolved.indexOf("price");
  if (index > -1) unresolved.splice(index, 1);

  return num; // number; target sheet will format to $ via its existing formatting
}
