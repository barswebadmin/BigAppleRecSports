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
  
  const hasBackgroundColor = rowBackgrounds.some(bg => {
    const bgLower = (bg || '').toLowerCase();
    return bgLower && bgLower !== '#ffffff' && bgLower !== '#fff' && bgLower !== 'white';
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
      
      if (!userTimestamp && rowEmail === email.toLowerCase() && rowLeague === league) {
        userTimestamp = rowTimestamp;
        Logger.log(`✅ Found user at row ${i + 1}, timestamp: ${userTimestamp}`);
      }
      
      if (shouldSkipRow(backgrounds[i], notesVal)) {
        Logger.log(`⏭️ Skipping row ${i + 1}`);
        continue;
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

