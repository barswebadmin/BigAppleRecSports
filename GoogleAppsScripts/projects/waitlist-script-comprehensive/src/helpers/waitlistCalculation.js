import { getSheet } from '../shared-utilities/sheetUtils';

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

export function shouldSkipRow(rowBackgrounds, notes) {
  const notesLower = (notes || "").toString().toLowerCase();
  if (SKIP_KEYWORDS.some(keyword => notesLower.includes(keyword))) {
    return true;
  }
  
  // Check for background colors
  if (!rowBackgrounds || rowBackgrounds.length === 0) {
    return false;
  }
  
  const hasBackgroundColor = rowBackgrounds.some(bg => {
    if (!bg) return false;
    
    // Handle RGB object format from Google Sheets API
    // Google Sheets returns objects like {red: 1, green: 1, blue: 1} where values are 0-1
    if (typeof bg === 'object' && bg.red !== undefined) {
      // Check if it's NOT white (allowing small floating point differences)
      // White = {red: 1, green: 1, blue: 1}
      const isWhite = Math.abs((bg.red || 0) - 1.0) < 0.01 && 
                     Math.abs((bg.green || 0) - 1.0) < 0.01 && 
                     Math.abs((bg.blue || 0) - 1.0) < 0.01;
      return !isWhite;
    }
    
    // Handle string format (hex colors like '#ffffff' or 'white')
    if (typeof bg === 'string') {
      const bgLower = bg.toLowerCase();
      return bgLower && bgLower !== '#ffffff' && bgLower !== '#fff' && bgLower !== 'white' && bgLower !== '';
    }
    
    return false;
  });
  
  return hasBackgroundColor;
}

export function calculateWaitlistPosition(email, league, options = {}) {
  try {
    Logger.log(`📊 Calculating waitlist position for ${email} in ${league}`);
    
    const sheet = options.sheet || getSheet();
    const dataRange = sheet.getDataRange();
    const sheetData = options.sheetData || dataRange.getValues();
    const backgrounds = options.backgrounds || dataRange.getBackgrounds();
    
    const headers = sheetData[0];
    const emailCol = headers.findIndex(h => h.toLowerCase().includes("email address"));
    const leagueCol = headers.findIndex(h => h.toLowerCase().includes("please select the league you want to sign up for"));
    const timestampCol = 0;
    const notesCol = headers.findIndex(h => h.toLowerCase().includes("notes"));
    
    if (emailCol === -1 || leagueCol === -1) {
      Logger.log(`❌ Required columns not found. Email: ${emailCol}, League: ${leagueCol}`);
      return { found: false, error: "Required columns not found in spreadsheet" };
    }
    
    Logger.log(`📍 Column indices - Email: ${emailCol}, League: ${leagueCol}, Notes: ${notesCol}, Timestamp: ${timestampCol}`);
    
    let userTimestamp = options.userTimestamp;
    const validEntries = [];
    
    for (let i = 1; i < sheetData.length; i++) {
      const rowEmail = (sheetData[i][emailCol] || '').toString().trim().toLowerCase();
      const rowLeague = (sheetData[i][leagueCol] || '').toString().trim();
      const rowTimestamp = new Date(sheetData[i][timestampCol]);
      const notesVal = sheetData[i][notesCol] || "";
      
      // Check if row should be skipped BEFORE capturing user timestamp
      // This ensures we use the correct (non-skipped) entry for the user
      if (shouldSkipRow(backgrounds[i], notesVal)) {
        Logger.log(`⏭️ Skipping row ${i + 1}`);
        continue;
      }
      
      // Find user's entry (only from non-skipped rows)
      if (!userTimestamp && rowEmail === email.toLowerCase() && rowLeague === league) {
        userTimestamp = rowTimestamp;
        Logger.log(`✅ Found user at row ${i + 1}, timestamp: ${userTimestamp}`);
      }
      
      if (rowLeague === league) {
        validEntries.push({ rowIndex: i, timestamp: rowTimestamp });
      }
    }
    
    if (!userTimestamp) {
      Logger.log(`❌ User not found: ${email} for league ${league}`);
      return { found: false, error: "Email and league combination not found" };
    }
    
    const earlierCount = validEntries.filter(entry => entry.timestamp < userTimestamp).length;
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

