/**
 * Product Handle Parsing and Construction
 * Bidirectional conversion between product handles and components
 */

/**
 * Parse product handle to components
 * @param {string} handle - e.g., "2025-fall-kickball-sunday-opendiv"
 * @returns {Object} - {year, season, sport, day, division}
 */
function parseProductHandle(handle) {
  try {
    const parts = handle.split('-');
    
    if (parts.length < 5) {
      throw new Error(`Invalid handle format: ${handle}`);
    }
    
    const year = parseInt(parts[0]);
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
 * Construct product handle from league name and spreadsheet
 * @param {string} year - Year (e.g., "2025")
 * @param {string} season - Season (e.g., "Fall")
 * @param {string} sport - Sport (e.g., "Kickball")
 * @param {string} day - Day (e.g., "Sunday")
 * @param {string} rawDivision - Division (e.g., "Open Division")
 * @returns {string} - e.g., "2025-fall-kickball-sunday-opendiv"
 */
function constructProductHandle(year, season, sport, day, rawDivision) {
  try {
    const divisionClean = rawDivision
      .replace(/\s+division/i, '')
      .replace(/[^a-z0-9]/gi, '')
      .toLowerCase();
    
    const divisionFormatted = divisionClean + 'div';
    
    const handle = `${year}-${season.toLowerCase()}-${sport.toLowerCase()}-${day.toLowerCase()}-${divisionFormatted}`;
    
    Logger.log(`📝 Constructed handle: ${handle}`);
    return handle;
  } catch (error) {
    Logger.log(`❌ Error constructing handle: ${error.message}`);
    throw error;
  }
}

/**
 * Get product handle with fallback to manual input
 * @param {string} year - Year
 * @param {string} season - Season
 * @param {string} sport - Sport
 * @param {string} day - Day
 * @param {string} rawDivision - Division
 * @returns {string} - Product handle
 */
function getProductHandleOrPromptFallback(year, season, sport, day, rawDivision) {
  try {
    return constructProductHandle(year, season, sport, day, rawDivision);
  } catch (error) {
    Logger.log(`⚠️ Auto-construction failed: ${error.message}`);
    
    const ui = SpreadsheetApp.getUi();
    const response = ui.prompt(
      'Manual Product Handle Entry',
      `Could not auto-construct handle.\nPlease enter the product handle manually (e.g., "2025-fall-kickball-sunday-opendiv"):`,
      ui.ButtonSet.OK_CANCEL
    );
    
    if (response.getSelectedButton() === ui.Button.OK) {
      return response.getResponseText().trim();
    } else {
      throw new Error('User cancelled handle entry');
    }
  }
}

/**
 * Get current season and year from spreadsheet title
 * @returns {Object} - {season, year}
 */
function getCurrentSeasonAndYearFromSpreadsheetTitle() {
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
function extractProductIdFromUrl(productUrl) {
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
      if (match && match[1]) {
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
function extractProductHandleFromUrl(productUrl) {
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
      if (match && match[1]) {
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
