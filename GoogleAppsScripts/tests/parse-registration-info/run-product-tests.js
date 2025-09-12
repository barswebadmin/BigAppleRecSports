/**
 * Test runner that loads actual GAS functions and runs comprehensive tests
 */

const fs = require('fs');
const path = require('path');
const { strict: assert } = require('assert');

// Mock Google Apps Script environment
global.Logger = { log: console.log };
global.SpreadsheetApp = {
  getUi: () => ({
    alert: (title, message, buttons) => ({ getSelectedButton: () => 'OK' }),
    prompt: (title, message, buttons) => ({ 
      getSelectedButton: () => 'OK',
      getResponseText: () => 'create'
    }),
    Button: { OK: 'OK', CANCEL: 'CANCEL', YES: 'YES', NO: 'NO' },
    ButtonSet: { OK: 'OK', OK_CANCEL: 'OK_CANCEL', YES_NO: 'YES_NO' }
  })
};

// Load required GAS modules by evaluating them in global scope
function loadGasFile(filePath) {
  const fullPath = path.resolve(__dirname, '../../projects/parse-registration-info', filePath);
  if (fs.existsSync(fullPath)) {
    const content = fs.readFileSync(fullPath, 'utf8');
    eval(content);
    console.log(`✅ Loaded: ${filePath}`);
  } else {
    console.log(`❌ Missing: ${filePath}`);
  }
}

console.log('🚀 Loading GAS functions...');

// Load in dependency order
loadGasFile('config/constants.gs');
loadGasFile('helpers/textUtils.gs'); 
loadGasFile('helpers/normalizers.gs');
loadGasFile('core/dateParser.gs');
loadGasFile('core/flagsParser.gs');
loadGasFile('core/notesParser.gs');
loadGasFile('core/rowParser.gs');
loadGasFile('core/portedFromProductCreateSheet/createShopifyProduct.gs');

console.log('📋 Running comprehensive product creation tests...\n');

// Test 1: Pickleball Sunday WTNB+ Social Buddy Sign-up
console.log('🧪 TEST 1: Pickleball Sunday WTNB+ Social Buddy Sign-up');
try {
  const testData = {
    A: "Pickleball",
    B: "SUNDAY\n\nWTNB+\nSocial\nBuddy-Sign Up",
    C: "Total # of Weeks: 8\nRegular Season: 7 weeks\nNewbie Night: n/a\nTournament Date: Dec 7\nClosing Party: Date TBD\n\nSkipping 11/9 and 11/30\n\n# of Teams: 9\n# of Players: 72",
    D: "October 12",
    E: "Dec 7", 
    F: "$145",
    G: "12-3PM",
    H: "John Jay College",
    I: "pickleball.wtnb@bigapplerecsports.com",
    J: "6/8 attendance from Summer 2025",
    K: "",
    L: "SAME AS SPRING/SUMMER 2025 REGISTRATION",
    M: "Sept 18th 7PM", // Early registration
    N: "Sept 17th 7PM", // Vet registration  
    O: "Sept 19th 7PM"  // Open registration
  };

  const unresolved = [];
  const parsed = parseSourceRowEnhanced_(testData, unresolved);
  const productData = convertToProductCreationFormat_(parsed, 14);
  
  console.log('📊 Parsed Data:', {
    sport: parsed.sport,
    day: parsed.day,
    division: parsed.division,
    socialOrAdvanced: parsed.socialOrAdvanced,
    types: parsed.types,
    totalInventory: parsed.totalInventory,
    price: parsed.price,
    location: parsed.location
  });
  
  console.log('📋 Product Data Sample:', {
    sport: productData.sport,
    day: productData.day, 
    division: productData.division,
    season: productData.season,
    year: productData.year,
    totalInventory: productData.totalInventory
  });
  
  // Test validation
  const validation = validateRequiredFields_(productData);
  console.log('✅ Validation:', validation);
  
  if (validation.isValid) {
    const display = buildConfirmationDisplay_(productData);
    console.log('📝 Confirmation Display (first 200 chars):', display.substring(0, 200) + '...');
  } else {
    const errorDisplay = buildErrorDisplay_(productData, validation.missingFields);
    console.log('❌ Error Display (first 200 chars):', errorDisplay.substring(0, 200) + '...');
  }
  
  console.log('✅ Pickleball test completed\n');
  
} catch (error) {
  console.log('❌ Pickleball test failed:', error.message);
  console.log('Stack:', error.stack);
}

// Test 2: Kickball Saturday Open Social Randomized  
console.log('🧪 TEST 2: Kickball Saturday Open Social Randomized');
try {
  const testData = {
    A: "Kickball",
    B: "SATURDAY\n\nOpen\nSocial\nRandomized",
    C: "Total # of Weeks: 8\nOpening Party: 9/13/25\nRegular Season: 8 weeks\nRain Date: 11/22/25\nClosing Party: 11/15/25*\n\n# of Teams: 12\n# of Players: 192 (16 players per team)\n\nGame Duration: 45 min",
    D: "9/20/2025",
    E: "11/15/2025",
    F: "$115", 
    G: "1-3pm",
    H: "Dewitt Clinton Park",
    I: "",
    J: "Saturday Open Summer 2025",
    K: "",
    L: "",
    M: "8/31/25 @ 7pm", // Early registration
    N: "8/30/25 @ 7pm", // Vet registration
    O: "9/1/25 @ 7pm"   // Open registration
  };

  const unresolved = [];
  const parsed = parseSourceRowEnhanced_(testData, unresolved);
  const productData = convertToProductCreationFormat_(parsed, 8);
  
  console.log('📊 Parsed Data:', {
    sport: parsed.sport,
    day: parsed.day,
    division: parsed.division,
    openingPartyDate: parsed.openingPartyDate,
    rainDate: parsed.rainDate,
    totalInventory: parsed.totalInventory
  });
  
  const validation = validateRequiredFields_(productData);
  console.log('✅ Validation:', validation);
  
  console.log('✅ Kickball test completed\n');
  
} catch (error) {
  console.log('❌ Kickball test failed:', error.message);
}

// Test 3: Bowling Sunday Open Multiple Types
console.log('🧪 TEST 3: Bowling Sunday Open Multiple Types');
try {
  const testData = {
    A: "Bowling",
    B: "SUNDAY\n\nOpen\n\nBuddy-Sign Up\nRandomized",
    C: "2 sessions; 350-364 players, 50-52 teams, 7 players max\nTeams are randomly assigned\nPlayers are able to sign-up with one buddy\nTimes: 12:45-2:45PM & 3:00-5:00PM\n\nNOTE: SKIPPING 11/9 to accommodate for all sports charity awards event.",
    D: "9/21/25",
    E: "11/16/25",
    F: "$145",
    G: "Times: 12:45-2:45PM & 3:00-5:00PM",
    H: "Frames Bowling Lounge",
    I: "sunday-bowling@bigapplerecsports.com",
    J: "Spring 2025 – qualify if players attendnace is max 2 missed sessions",
    K: "9/21, 9/28, 10/5, 10/12, 10/19, 10/26, 11/2, 11/9, 11/16",
    L: "SAME AS SPRING/SUMMER 2025 REGISTRATION",
    M: "Weds, Sept. 3rd, 6pm", // Early registration  
    N: "Tues, Sept. 2nd, 6pm", // Vet registration
    O: "Thurs, Sept. 4th, 6pm" // Open registration
  };

  const unresolved = [];
  const parsed = parseSourceRowEnhanced_(testData, unresolved);
  const productData = convertToProductCreationFormat_(parsed, 5);
  
  console.log('📊 Parsed Data:', {
    sport: parsed.sport,
    day: parsed.day,
    types: parsed.types,
    alternativeStartTime: parsed.alternativeStartTime,
    alternativeEndTime: parsed.alternativeEndTime,
    totalInventory: parsed.totalInventory
  });
  
  const validation = validateRequiredFields_(productData);
  console.log('✅ Validation:', validation);
  
  const display = buildConfirmationDisplay_(productData);
  console.log('📝 Should NOT show Social/Advanced for bowling:', !display.includes('Social or Advanced:'));
  console.log('📝 Should show alternative times:', display.includes('Alternative Start Time:'));
  
  console.log('✅ Bowling test completed\n');
  
} catch (error) {
  console.log('❌ Bowling test failed:', error.message);
}

// Test 4: Dodgeball Monday Big Ball - Missing Required Field
console.log('🧪 TEST 4: Dodgeball Monday Big Ball - Missing Required Field');
try {
  const testData = {
    A: "Dodgeball",
    B: "MONDAY\n\nOpen\nSocial Big Ball\nRandomized - Buddy Sign Ups",
    C: "Newbie Night/Open Play - 10/6/25\n\nNo games on Indigineous Peoples Day 10/13",
    D: "10-20-2025",
    E: "12/8/2025",
    F: "$120",
    G: "6:30-10",
    H: "Hartley House\n413 W 46th Street",
    I: "chance.hamlin@bigapplerecsports.com\ntenni.tenerelli@bigapplerecsports.com",
    J: "Spring 2025 Vet Status",
    K: "",
    L: "",
    M: "Weds, Sept. 3rd, 6pm", // Early registration
    N: "Tues, Sept. 2nd, 7pm", // Vet registration
    O: "Thurs, Sept. 4th, 6pm" // Open registration
    // NOTE: Missing total inventory in the data!
  };

  const unresolved = [];
  const parsed = parseSourceRowEnhanced_(testData, unresolved);
  const productData = convertToProductCreationFormat_(parsed, 14);
  
  console.log('📊 Parsed Data:', {
    sport: parsed.sport,
    sportSubCategory: parsed.sportSubCategory,
    day: parsed.day,
    newPlayerOrientationDateTime: parsed.newPlayerOrientationDateTime,
    offDatesFromNotes: parsed.offDatesFromNotes,
    totalInventory: parsed.totalInventory
  });
  
  const validation = validateRequiredFields_(productData);
  console.log('✅ Validation:', validation);
  
  if (!validation.isValid) {
    const errorDisplay = buildErrorDisplay_(productData, validation.missingFields);
    console.log('📝 Should show Sport Sub-Category for dodgeball:', errorDisplay.includes('Sport Sub-Category:'));
    console.log('📝 Should show [Not Found] for missing inventory:', errorDisplay.includes('Total Inventory: [Not Found]'));
    console.log('📝 Error starts with "Cannot":', errorDisplay.startsWith('Cannot'));
  }
  
  console.log('✅ Dodgeball test completed\n');
  
} catch (error) {
  console.log('❌ Dodgeball test failed:', error.message);
}

console.log('🎯 All tests completed!');
