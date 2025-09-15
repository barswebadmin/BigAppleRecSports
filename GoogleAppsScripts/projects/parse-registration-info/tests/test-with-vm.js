/**
 * Test using VM to properly load GAS functions
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

console.log('🚀 Setting up VM context...');

// Create a context with all the GAS globals
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

// Load all required files
const files = [
  'config/constants.gs',
  'helpers/textUtils.gs',
  'helpers/normalizers.gs',
  'parsers/dateParser.gs',
  'parsers/timeParser.gs',
  'parsers/priceParser.gs',
  'parsers/parseColBLeagueDetails_.gs',
  'parsers/notesParser.gs',
  'parsers/_rowParser.gs',
  'core/portedFromProductCreateSheet/createShopifyProduct.gs'
];

console.log('📦 Loading GAS files...');
files.forEach(loadGasFile);

console.log('\n🧪 Testing function availability...');
console.log('parseSourceRowEnhanced_ available:', 'parseSourceRowEnhanced_' in context);
console.log('convertToProductCreationFormat_ available:', 'convertToProductCreationFormat_' in context);
console.log('validateRequiredFields_ available:', 'validateRequiredFields_' in context);

if ('parseSourceRowEnhanced_' in context) {
  console.log('\n✅ Running comprehensive tests...');

  // Test 1: Pickleball
  console.log('\n🧪 TEST 1: Pickleball Sunday WTNB+ Social Buddy Sign-up');
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
      M: "Sept 18th 7PM",
      N: "Sept 17th 7PM",
      O: "Sept 19th 7PM"
    };

    const unresolved = [];
    const parsed = vm.runInContext('parseSourceRowEnhanced_(testData, unresolved)',
      Object.assign(context, { testData, unresolved }));

    console.log('📊 Parsed result keys:', Object.keys(parsed));
    console.log('📊 Basic fields:', {
      sport: parsed.sport,
      day: parsed.day,
      division: parsed.division,
      socialOrAdvanced: parsed.socialOrAdvanced,
      types: parsed.types,
      totalInventory: parsed.totalInventory,
      price: parsed.price
    });

    if ('convertToProductCreationFormat_' in context) {
      const productData = vm.runInContext('convertToProductCreationFormat_(parsed, 14)',
        Object.assign(context, { parsed }));

      console.log('📋 Product data keys:', Object.keys(productData));
      console.log('📋 Expected vs Actual:');

      // Check key fields against user specification
      const expectedValues = {
        sport: 'Pickleball',
        day: 'Sunday',
        sportSubCategory: 'N/A',
        division: 'WTNB+',
        season: 'Fall',
        year: 2025,
        socialOrAdvanced: 'Social',
        types: 'Buddy Sign-up',
        totalInventory: 72
      };

      for (const [key, expected] of Object.entries(expectedValues)) {
        const actual = productData[key];
        const match = actual === expected;
        console.log(`  ${key}: Expected "${expected}", Got "${actual}" ${match ? '✅' : '❌'}`);
      }

      if ('validateRequiredFields_' in context) {
        const validation = vm.runInContext('validateRequiredFields_(productData)',
          Object.assign(context, { productData }));
        console.log('🔍 Validation:', validation);

        if (validation.isValid && 'buildConfirmationDisplay_' in context) {
          const display = vm.runInContext('buildConfirmationDisplay_(productData)',
            Object.assign(context, { productData }));
          console.log('📝 Display preview (first 300 chars):');
          console.log(display.substring(0, 300) + '...');

          // Check for key expected content
          console.log('📝 Display checks:');
          console.log('  Contains "Sport: Pickleball":', display.includes('Sport: Pickleball'));
          console.log('  Contains "Division: WTNB+":', display.includes('Division: WTNB+'));
          console.log('  Contains "Total Inventory: 72":', display.includes('Total Inventory: 72'));
          console.log('  Contains "Off Dates: 11/9, 11/30":', display.includes('Off Dates: 11/9, 11/30'));
        }
      }
    }

    console.log('✅ Pickleball test completed successfully');

  } catch (error) {
    console.log('❌ Pickleball test failed:', error.message);
    console.log('Stack:', error.stack);
  }

  // Test 2: Dodgeball with missing field
  console.log('\n🧪 TEST 2: Dodgeball with missing totalInventory');
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
      I: "chance.hamlin@bigapplerecsports.com",
      J: "Spring 2025 Vet Status",
      K: "",
      L: "",
      M: "Weds, Sept. 3rd, 6pm",
      N: "Tues, Sept. 2nd, 7pm",
      O: "Thurs, Sept. 4th, 6pm"
    };

    const unresolved = [];
    const parsed = vm.runInContext('parseSourceRowEnhanced_(testData, unresolved)',
      Object.assign(context, { testData, unresolved }));

    console.log('📊 Dodgeball parsed:', {
      sport: parsed.sport,
      sportSubCategory: parsed.sportSubCategory,
      socialOrAdvanced: parsed.socialOrAdvanced,
      totalInventory: parsed.totalInventory
    });

    if ('convertToProductCreationFormat_' in context) {
      const productData = vm.runInContext('convertToProductCreationFormat_(parsed, 14)',
        Object.assign(context, { parsed }));

      const validation = vm.runInContext('validateRequiredFields_(productData)',
        Object.assign(context, { productData }));

      console.log('🔍 Validation should be invalid:', validation);
      console.log('🔍 Missing fields:', validation.missingFields);

      if (!validation.isValid && 'buildErrorDisplay_' in context) {
        const errorDisplay = vm.runInContext('buildErrorDisplay_(productData, validation.missingFields)',
          Object.assign(context, { productData, validation }));

        console.log('📝 Error display checks:');
        console.log('  Starts with "Cannot":', errorDisplay.startsWith('Cannot'));
        console.log('  Shows Sport Sub-Category:', errorDisplay.includes('Sport Sub-Category: Big Ball'));
        console.log('  Shows [Not Found]:', errorDisplay.includes('[Not Found]'));
      }
    }

    console.log('✅ Dodgeball test completed successfully');

  } catch (error) {
    console.log('❌ Dodgeball test failed:', error.message);
  }

} else {
  console.log('❌ parseSourceRowEnhanced_ not available - cannot run tests');
}

console.log('\n🎯 Testing completed!');
