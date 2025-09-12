/**
 * Final comprehensive test with fresh VM context
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { strict: assert } = require('assert');

console.log('🚀 Setting up fresh VM context...');

const context = {
  console: console,
  Logger: { log: console.log },
  SpreadsheetApp: {
    getUi: () => ({
      alert: (title, message, buttons) => ({ getSelectedButton: () => 'OK' }),
      prompt: (title, message, buttons) => ({ 
        getSelectedButton: () => 'OK',
        getResponseText: () => 'create'
      }),
      Button: { OK: 'OK', CANCEL: 'CANCEL', YES: 'YES', NO: 'NO' },
      ButtonSet: { OK: 'OK', OK_CANCEL: 'OK_CANCEL', YES_NO: 'YES_NO' }
    })
  }
};

vm.createContext(context);

function loadGasFile(filePath) {
  const fullPath = path.resolve(__dirname, '../../projects/parse-registration-info', filePath);
  if (fs.existsSync(fullPath)) {
    const content = fs.readFileSync(fullPath, 'utf8');
    try {
      vm.runInContext(content, context);
      console.log(`✅ Loaded: ${filePath}`);
      return true;
    } catch (error) {
      console.log(`❌ Error loading ${filePath}:`, error.message);
      return false;
    }
  } else {
    console.log(`❌ File not found: ${filePath}`);
    return false;
  }
}

// Load all required files in dependency order
const files = [
  'config/constants.gs',
  'helpers/textUtils.gs',
  'helpers/normalizers.gs',
  'core/dateParser.gs',
  'core/timeParser.gs',
  'core/priceParser.gs',
  'core/flagsParser.gs',
  'core/notesParser.gs',
  'core/rowParser.gs',
  'core/portedFromProductCreateSheet/createShopifyProduct.gs'
];

console.log('📦 Loading GAS files...');
files.forEach(loadGasFile);

console.log('\n🧪 Running final comprehensive tests...\n');

// ===== TEST 1: PICKLEBALL =====
console.log('🏓 TEST 1: Pickleball Sunday WTNB+ Social Buddy Sign-up');
try {
  const pickleballData = {
    A: "Pickleball",
    B: "SUNDAY\n\nWTNB+\nSocial\nBuddy-Sign Up",
    C: "Total # of Weeks: 8\nRegular Season: 7 weeks\nNewbie Night: n/a\nTournament Date: Dec 7\nOpening Party: TBD\nClosing Party: Date TBD\n\nSkipping 11/9 and 11/30\n\n# of Teams: 9\n# of Players: 72",
    D: "October 12",
    E: "Dec 7", 
    F: "$145",
    G: "12-3PM",
    H: "John Jay College",
    I: "pickleball.wtnb@bigapplerecsports.com",
    J: "6/8 attendance from Summer 2025",
    K: "",
    L: "SAME AS SPRING/SUMMER 2025 REGISTRATION",
    M: "Sept 18th 7PM",
    N: "Sept 17th 7PM",
    O: "Sept 19th 7PM"
  };

  const unresolved = [];
  const parsed = vm.runInContext('parseSourceRowEnhanced_(testData, unresolved)', 
    Object.assign(context, { testData: pickleballData, unresolved }));

  const productData = vm.runInContext('convertToProductCreationFormat_(parsed, 14)', 
    Object.assign(context, { parsed }));

  // Check critical field mappings
  const checks = {
    'sport': { expected: 'Pickleball', actual: productData.sport },
    'day': { expected: 'Sunday', actual: productData.day },
    'sportSubCategory': { expected: 'N/A', actual: productData.sportSubCategory },
    'division': { expected: 'WTNB+', actual: productData.division },
    'season': { expected: 'Fall', actual: productData.season },
    'year': { expected: 2025, actual: productData.year },
    'socialOrAdvanced': { expected: 'Social', actual: productData.socialOrAdvanced },
    'types': { expected: 'Buddy Sign-up', actual: productData.types },
    'totalInventory': { expected: 72, actual: productData.totalInventory },
    'openingPartyDate': { expected: 'TBD', actual: productData.openingPartyDate },
    'closingPartyDate': { expected: 'TBD', actual: productData.closingPartyDate }
  };

  let allPassed = true;
  for (const [field, check] of Object.entries(checks)) {
    const passed = check.actual === check.expected;
    console.log(`  ${field}: Expected "${check.expected}", Got "${check.actual}" ${passed ? '✅' : '❌'}`);
    if (!passed) allPassed = false;
  }

  // Check validation
  const validation = vm.runInContext('validateRequiredFields_(productData)', 
    Object.assign(context, { productData }));
  console.log(`  Validation valid: ${validation.isValid} ${validation.isValid ? '✅' : '❌'}`);

  // Check off dates parsing
  console.log(`  Off dates: "${productData.offDatesCommaSeparated}" ${productData.offDatesCommaSeparated.includes('11/9') ? '✅' : '❌'}`);

  // Check TBD display in confirmation if validation is valid
  let tbdDisplayCorrect = true;
  if (validation.isValid && 'buildConfirmationDisplay_' in context) {
    const display = vm.runInContext('buildConfirmationDisplay_(productData)', 
      Object.assign(context, { productData }));
    
    const hasTBDOpening = display.includes('Opening Party Date: TBD');
    const hasTBDClosing = display.includes('Closing Party Date: TBD');
    console.log(`  Display shows 'Opening Party Date: TBD': ${hasTBDOpening ? '✅' : '❌'}`);
    console.log(`  Display shows 'Closing Party Date: TBD': ${hasTBDClosing ? '✅' : '❌'}`);
    
    if (!hasTBDOpening || !hasTBDClosing) {
      console.log(`  💡 Display preview (special events section): ${display.substring(display.indexOf('=== SPECIAL EVENTS ==='), display.indexOf('=== LOCATION & PRICING ==='))}`);
      tbdDisplayCorrect = false;
    }
  }

  console.log(`  🏓 Pickleball test: ${allPassed && validation.isValid && tbdDisplayCorrect ? 'PASSED ✅' : 'FAILED ❌'}`);

} catch (error) {
  console.log(`  ❌ Pickleball test failed: ${error.message}`);
}

// ===== TEST 2: DODGEBALL =====
console.log('\n🥎 TEST 2: Dodgeball Monday Big Ball - Missing Required Field');
try {
  const dodgeballData = {
    A: "Dodgeball",
    B: "MONDAY\n\nOpen\nSocial Big Ball\nRandomized - Buddy Sign Ups",
    C: "Newbie Night/Open Play - 10/6/25\n\nNo games on Indigineous Peoples Day 10/13",
    D: "10-20-2025",
    E: "12/8/2025",
    F: "$120",
    G: "6:30-10",
    H: "Hartley House\n413 W 46th Street",
    I: "chance.hamlin@bigapplerecsports.com",
    J: "Spring 2025 Vet Status",
    K: "",
    L: "",
    M: "Wed, Sept 3, 6pm",  // Simplified format
    N: "Tue, Sept 2, 7pm",  // Simplified format
    O: "Thu, Sept 4, 6pm"   // Simplified format
  };

  const unresolved = [];
  const parsed = vm.runInContext('parseSourceRowEnhanced_(testData, unresolved)', 
    Object.assign(context, { testData: dodgeballData, unresolved }));

  console.log(`  Registration parsing results:`);
  console.log(`    Vet reg: "${parsed.vetRegistrationStartDateTime}"`);
  console.log(`    Early reg: "${parsed.earlyRegistrationStartDateTime}"`);
  console.log(`    Open reg: "${parsed.openRegistrationStartDateTime}"`);

  const productData = vm.runInContext('convertToProductCreationFormat_(parsed, 14)', 
    Object.assign(context, { parsed }));

  // Key checks for dodgeball
  const checks = {
    'sport': { expected: 'Dodgeball', actual: productData.sport },
    'sportSubCategory': { expected: 'Big Ball', actual: productData.sportSubCategory },
    'socialOrAdvanced': { expected: 'Social', actual: productData.socialOrAdvanced },
    'totalInventory': { expected: '', actual: productData.totalInventory } // Should be empty (missing)
  };

  let allPassed = true;
  for (const [field, check] of Object.entries(checks)) {
    const passed = check.actual === check.expected;
    console.log(`  ${field}: Expected "${check.expected}", Got "${check.actual}" ${passed ? '✅' : '❌'}`);
    if (!passed) allPassed = false;
  }

  // Validation should fail due to missing total inventory
  const validation = vm.runInContext('validateRequiredFields_(productData)', 
    Object.assign(context, { productData }));
  const shouldFail = !validation.isValid && validation.missingFields.includes('Total Inventory');
  console.log(`  Should fail validation: ${shouldFail} ${shouldFail ? '✅' : '❌'}`);

  // Should show off dates from "No games on..."
  const hasOffDates = productData.offDatesCommaSeparated.includes('10/13');
  console.log(`  Off dates (10/13): "${productData.offDatesCommaSeparated}" ${hasOffDates ? '✅' : '❌'}`);

  console.log(`  🥎 Dodgeball test: ${allPassed && shouldFail && hasOffDates ? 'PASSED ✅' : 'FAILED ❌'}`);

} catch (error) {
  console.log(`  ❌ Dodgeball test failed: ${error.message}`);
}

// ===== TEST 3: BOWLING =====
console.log('\n🎳 TEST 3: Bowling Sunday Open Multiple Types');
try {
  const bowlingData = {
    A: "Bowling",
    B: "SUNDAY\n\nOpen\n\nBuddy-Sign Up\nRandomized",
    C: "2 sessions; 350-364 players, 50-52 teams, 7 players max\nTeams are randomly assigned\nPlayers are able to sign-up with one buddy\nTimes: 12:45-2:45PM & 3:00-5:00PM\n\nNOTE: SKIPPING 11/9 to accommodate for all sports charity awards event.",
    D: "9/21/25",
    E: "11/16/25",
    F: "$145",
    G: "Times: 12:45-2:45PM & 3:00-5:00PM",
    H: "Frames Bowling Lounge",
    I: "sunday-bowling@bigapplerecsports.com",
    J: "Spring 2025",
    K: "9/21, 9/28, 10/5, 10/12, 10/19, 10/26, 11/2, 11/9, 11/16",
    L: "SAME AS SPRING/SUMMER 2025 REGISTRATION",
    M: "Wed, Sept 3, 6pm",
    N: "Tue, Sept 2, 6pm",
    O: "Thu, Sept 4, 6pm"
  };

  const unresolved = [];
  const parsed = vm.runInContext('parseSourceRowEnhanced_(testData, unresolved)', 
    Object.assign(context, { testData: bowlingData, unresolved }));

  const productData = vm.runInContext('convertToProductCreationFormat_(parsed, 5)', 
    Object.assign(context, { parsed }));

  // Check key bowling fields
  const checks = {
    'sport': { expected: 'Bowling', actual: productData.sport },
    'types': { expected: 'Randomized Teams, Buddy Sign-up', actual: productData.types },
    'totalInventory': { expected: 364, actual: productData.totalInventory }, // Should take max from range
    'alternativeStartTime': { expected: null, actual: productData.alternativeStartTime },
    'alternativeEndTime': { expected: null, actual: productData.alternativeEndTime }
  };

  let allPassed = true;
  for (const [field, check] of Object.entries(checks)) {
    const passed = (check.actual === check.expected) || 
                  (field.includes('alternative') && check.actual); // Alternative times should exist
    console.log(`  ${field}: Expected "${check.expected}", Got "${check.actual}" ${passed ? '✅' : '❌'}`);
    if (!passed && !field.includes('alternative')) allPassed = false;
  }

  // Check that bowling doesn't show social/advanced in confirmation
  const display = vm.runInContext('buildConfirmationDisplay_(productData)', 
    Object.assign(context, { productData }));
  const hiddenFields = !display.includes('Social or Advanced:') && !display.includes('New Player Orientation:');
  console.log(`  Hides Social/Advanced and Orientation for bowling: ${hiddenFields ? '✅' : '❌'}`);

  const showsAlternative = display.includes('Alternative Start Time:') && display.includes('Alternative End Time:');
  console.log(`  Shows alternative times: ${showsAlternative ? '✅' : '❌'}`);

  console.log(`  🎳 Bowling test: ${allPassed && hiddenFields && showsAlternative ? 'PASSED ✅' : 'FAILED ❌'}`);

} catch (error) {
  console.log(`  ❌ Bowling test failed: ${error.message}`);
}

console.log('\n🎯 All comprehensive tests completed!');
