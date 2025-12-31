import { getSheet } from '../shared-utilities/sheetUtils';

/**
 * Shared Waitlist Position Calculation Logic
 * Single source of truth for calculating waitlist positions
 */

export const SKIP_KEYWORDS = [
  'process',
  'cancel',
  'done',
  'sent',
  'sign',
  'already',
  'not found',
  'no product',
  'not sold'
];

/**
 * Calculate waitlist position for a given email and league
 * @param {string} email - Player email
 * @param {string} league - League name
 * @param {Object} options - Optional parameters
 * @param {Object} options.sheet - Pre-fetched sheet (optional, will fetch if not provided)
 * @param {Array} options.sheetData - Pre-fetched sheet data (optional)
 * @param {Array} options.backgrounds - Pre-fetched backgrounds (optional)
 * @param {Date} options.userTimestamp - User's timestamp for timestamp-based calculation
 * @returns {Object} { found: boolean, position: number, error?: string }
 */
export function calculateWaitlistPosition(email, league, options = {}) {
  try {
    Logger.log(`📊 Calculating waitlist position for ${email} in ${league}`);
    
    // Get sheet data
    const sheet = options.sheet || getSheet();
    const dataRange = sheet.getDataRange();
    const sheetData = options.sheetData || dataRange.getValues();
    const backgrounds = options.backgrounds || dataRange.getBackgrounds();
    
    const headers = sheetData[0];
    
    // Find column indices
    const emailCol = headers.findIndex(h => h.toLowerCase().includes("email address"));
    const leagueCol = headers.findIndex(h => h.toLowerCase().includes("please select the league you want to sign up for"));
    const timestampCol = 0; // Timestamp is always first column
    const notesCol = headers.findIndex(h => h.toLowerCase().includes("notes"));
    
    if (emailCol === -1 || leagueCol === -1) {
      Logger.log(`❌ Required columns not found. Email: ${emailCol}, League: ${leagueCol}`);
      return { found: false, error: "Required columns not found in spreadsheet" };
    }
    
    Logger.log(`📍 Column indices - Email: ${emailCol}, League: ${leagueCol}, Notes: ${notesCol}, Timestamp: ${timestampCol}`);
    
    // Find the user's row and timestamp
    let userRowIndex = -1;
    let userTimestamp = options.userTimestamp;
    
    if (!userTimestamp) {
      // Find user's row to get their timestamp
      for (let i = 1; i < sheetData.length; i++) {
        const rowEmail = (sheetData[i][emailCol] || '').toString().trim().toLowerCase();
        const rowLeague = (sheetData[i][leagueCol] || '').toString().trim();
        
        if (rowEmail === email.toLowerCase() && rowLeague === league) {
          userRowIndex = i;
          userTimestamp = new Date(sheetData[i][timestampCol]);
          Logger.log(`✅ Found user at row ${i + 1}, timestamp: ${userTimestamp}`);
          break;
        }
      }
      
      if (userRowIndex === -1) {
        Logger.log(`❌ User not found: ${email} for league ${league}`);
        return { found: false, error: "Email and league combination not found" };
      }
    }
    
    // Calculate position by counting earlier non-skipped entries
    let earlierCount = 0;
    
    for (let i = 1; i < sheetData.length; i++) {
      const rowLeague = (sheetData[i][leagueCol] || '').toString().trim();
      const rowTimestamp = new Date(sheetData[i][timestampCol]);
      const notesVal = (sheetData[i][notesCol] || "").toString().toLowerCase();
      
      if (SKIP_KEYWORDS.some(keyword => notesVal.includes(keyword))) {
        Logger.log(`⏭️ Skipping row ${i + 1} - notes: "${notesVal}"`);
        continue;
      }
      
      // Skip if row has any cell with a background color (not white/default)
      const rowBackgrounds = backgrounds[i];
      const hasBackgroundColor = rowBackgrounds.some(bg => {
        const bgLower = (bg || '').toLowerCase();
        return bgLower && bgLower !== '#ffffff' && bgLower !== '#fff' && bgLower !== 'white';
      });
      
      if (hasBackgroundColor) {
        Logger.log(`⏭️ Skipping row ${i + 1} - has background color`);
        continue;
      }
      
      // Count if same league and earlier timestamp
      if (rowLeague === league && rowTimestamp < userTimestamp) {
        earlierCount++;
      }
    }
    
    const position = earlierCount + 1;
    Logger.log(`📊 Waitlist position calculated: #${position}`);
    
    return {
      found: true,
      position: position
    };
    
  } catch (error) {
    Logger.log(`💥 Error calculating waitlist position: ${error.message}`);
    Logger.log(`Stack trace: ${error.stack}`);
    return {
      found: false,
      error: error.message
    };
  }
}

/**
 * Check if a row should be skipped in waitlist calculations
 * @param {Array} rowBackgrounds - Background colors for the row
 * @param {string} notes - Notes field value
 * @returns {boolean} - True if row should be skipped
 */
export function shouldSkipRow(rowBackgrounds, notes) {
  // Skip if notes contain any skip keywords
  const notesLower = (notes || "").toString().toLowerCase();
  if (SKIP_KEYWORDS.some(keyword => notesLower.includes(keyword))) {
    return true;
  }
  
  // Skip if row has any cell with a background color (not white/default)
  const hasBackgroundColor = rowBackgrounds.some(bg => {
    const bgLower = (bg || '').toLowerCase();
    return bgLower && bgLower !== '#ffffff' && bgLower !== '#fff' && bgLower !== 'white';
  });
  
  return hasBackgroundColor;
}

