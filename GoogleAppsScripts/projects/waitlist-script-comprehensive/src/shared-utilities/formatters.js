/**
 * Normalize phone number to XXX-XXX-XXXX format
 * @param {string} rawPhone - Raw phone number
 * @returns {string|null} - Normalized phone or null
 */
export function normalizePhone(rawPhone) {
    if (!rawPhone) return null;
  
    const digitsOnly = rawPhone.toString().replace(/\D/g, '');
  
    const normalized = digitsOnly.length === 11 && digitsOnly.startsWith('1')
      ? digitsOnly.slice(1)
      : digitsOnly;
  
    if (normalized.length !== 10) {
      Logger.log(`⚠️ Unexpected phone format: "${rawPhone}" → "${normalized}"`);
      return null;
    }
  
    return `${normalized.slice(0, 3)}-${normalized.slice(3, 6)}-${normalized.slice(6)}`;
  }
  
  
  /**
   * Capitalize first letter of string
   * @param {string} str - String to capitalize
   * @returns {string} - Capitalized string
   */
  export function capitalize(str) {
    if (!str || typeof str !== 'string') return str;
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
  }