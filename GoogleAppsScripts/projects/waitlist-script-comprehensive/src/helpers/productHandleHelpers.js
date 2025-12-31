/**
 * Product Handle Parsing and Construction
 * Bidirectional conversion between product handles and components
 */

import { capitalize } from '../shared-utilities/formatters';

/**
 * Parse product handle to components
 * @param {string} handle - e.g., "2025-fall-kickball-sunday-opendiv"
 * @returns {Object} - {year, season, sport, day, division}
 */
export function parseProductHandle(handle) {
  try {
    const parts = handle.split('-');
    
    if (parts.length < 5) {
      throw new Error(`Invalid handle format: ${handle}`);
    }
    
    const year = parseInt(parts[0], 10);
    const season = capitalize(parts[1]);
    const sport = capitalize(parts[2]);
    const day = capitalize(parts[3]);
    const divisionRaw = parts[4];
    
    const division = divisionRaw.replace('div', '').replace(/^\w/, c => c.toUpperCase());
    
    return {
      year,
      season,
      sport,
      day,
      division
    };
  } catch (error) {
    Logger.log(`❌ Error parsing handle '${handle}': ${error.message}`);
    throw error;
  }
}

/**
 * Construct product handle from league string and spreadsheet name
 * 
 * @param {string} league - League name (e.g., "Kickball - Sunday - Open Division")
 * @param {string} spreadsheetName - Spreadsheet name (e.g., "Fall 2025 Waitlist")
 * @returns {string} - Product handle (e.g., "2025-fall-kickball-sunday-opendiv")
 */
export function constructProductHandle(league, spreadsheetName) {
  try {
    Logger.log(`📋 Parsing league: "${league}" and spreadsheet: "${spreadsheetName}"`);
    
    // Extract season and year from spreadsheet name
    const spreadsheetMatch = spreadsheetName.match(/(\w+)\s+(\d{4})/);
    if (!spreadsheetMatch) {
      throw new Error(`Could not extract season and year from: "${spreadsheetName}"`);
    }
    
    const season = spreadsheetMatch[1].toLowerCase();
    const year = spreadsheetMatch[2];
    
    // Parse league string
    const leagueParts = league.split(' - ').map(part => part.trim());
    if (leagueParts.length < 3) {
      throw new Error(`League format not recognized: "${league}". Expected format: "Sport - Day - Division"`);
    }
    
    const sport = leagueParts[0].toLowerCase();
    const day = leagueParts[1].toLowerCase();
    const rawDivision = leagueParts[2];
    
    // Clean and format division
    const divisionClean = rawDivision
      .replace(/\s+division/i, '')
      .replace(/[^a-z0-9]/gi, '')
      .toLowerCase();
    
    const divisionFormatted = `${divisionClean}div`;
    
    // Build handle
    const handle = `${year}-${season}-${sport}-${day}-${divisionFormatted}`;
    
    Logger.log(`📝 Constructed handle: ${handle}`);
    return handle;
    
  } catch (error) {
    Logger.log(`❌ Error constructing handle: ${error.message}`);
    
    // Fallback: sanitize league string
    const fallbackHandle = league.toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');
    
    Logger.log(`🔄 Using fallback handle: ${fallbackHandle}`);
    return fallbackHandle;
  }
}

/**
 * Get current season and year from spreadsheet title
 * @returns {Object} - {season, year}
 */
export function getCurrentSeasonAndYearFromSpreadsheetTitle() {
  const spreadsheetName = SpreadsheetApp.getActiveSpreadsheet().getName();
  const lower = spreadsheetName.toLowerCase();
  const seasons = ['summer', 'spring', 'fall', 'winter'];

  const cleaned = lower.replace(/waitlist/i, '').trim();
  const parts = cleaned.split(/\s+/);

  let season = null;
  let year = null;

  for (const part of parts) {
    if (seasons.includes(part)) {
      season = part;
    } else if (/^\d{4}$/.test(part)) {
      year = part;
    }
  }

  if (!season || !year) {
    Logger.log(`⚠️ Could not extract season/year from: ${spreadsheetName}`);
  }

  return { season, year };
}

/**
 * Extract product ID from Shopify admin or API URLs
 * Supports various Shopify URL formats with product IDs
 * @param {string} productUrl - Shopify product URL
 * @returns {string|null} - GraphQL ID format (gid://shopify/Product/123) or null
 */
export function extractProductIdFromUrl(productUrl) {
  if (!productUrl || typeof productUrl !== 'string') {
    return null;
  }
  
  try {
    const cleanUrl = productUrl.split('?')[0].split('#')[0];
    
    const patterns = [
      /\/products\/(\d+)(?:\/|$)/,
      /\/admin\/products\/(\d+)(?:\/|$)/,
    ];
    
    for (const pattern of patterns) {
      const match = cleanUrl.match(pattern);
      if (match?.[1]) {
        return `gid://shopify/Product/${match[1]}`;
      }
    }
    
    return null;
    
  } catch (error) {
    Logger.log(`Error extracting product ID from URL: ${error.message}`);
    return null;
  }
}

/**
 * Extract product handle from Shopify product URL
 * Supports various Shopify URL formats
 * @param {string} productUrl - Shopify product URL
 * @returns {string|null} - Product handle or null
 */
export function extractProductHandleFromUrl(productUrl) {
  if (!productUrl || typeof productUrl !== 'string') {
    return null;
  }
  
  try {
    const cleanUrl = productUrl.split('?')[0].split('#')[0];
    
    const patterns = [
      /\/products\/([a-z0-9\-]+)(?:\/|$)/i,
      /\/collections\/[^\/]+\/products\/([a-z0-9\-]+)(?:\/|$)/i,
    ];
    
    for (const pattern of patterns) {
      const match = cleanUrl.match(pattern);
      if (match?.[1]) {
        const handle = match[1];
        if (!/^\d+$/.test(handle)) {
          return handle;
        }
      }
    }
    
    return null;
    
  } catch (error) {
    Logger.log(`Error extracting product handle from URL: ${error.message}`);
    return null;
  }
}
