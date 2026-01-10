/**
 * Simple test to verify parsing functions work
 */

const fs = require('fs');
const path = require('path');

// Mock Google Apps Script environment
global.Logger = { log: console.log };

function loadGasFile(filePath) {
  const fullPath = path.resolve(__dirname, '../../projects/parse-registration-info', filePath);
  console.log(`Loading: ${fullPath}`);
  if (fs.existsSync(fullPath)) {
    const content = fs.readFileSync(fullPath, 'utf8');
    console.log(`File size: ${content.length} chars`);
    console.log(`First 100 chars: ${content.substring(0, 100)}`);
    try {
      eval(content);
      console.log(`✅ Successfully loaded: ${filePath}`);
    } catch (error) {
      console.log(`❌ Error loading ${filePath}:`, error.message);
    }
  } else {
    console.log(`❌ File not found: ${filePath}`);
  }
}

console.log('🚀 Testing file loading...');

// Load dependencies in order
loadGasFile('config/constants.js');
loadGasFile('helpers/textUtils.js');
loadGasFile('helpers/normalizers.js');
loadGasFile('parsers/dateParser.js');
loadGasFile('parsers/parseColBLeagueDetails_.js');
loadGasFile('parsers/notesParser.js');
loadGasFile('parsers/_rowParser.js');

console.log('\n🧪 Testing function availability...');
console.log('parseSourceRowEnhanced_ defined?', typeof parseSourceRowEnhanced_ !== 'undefined');
console.log('normalizeSport_ defined?', typeof normalizeSport_ !== 'undefined');
console.log('parseTimeRangeBothSessions_ defined?', typeof parseTimeRangeBothSessions_ !== 'undefined');

if (typeof parseSourceRowEnhanced_ !== 'undefined') {
  console.log('\n✅ Basic function test...');
  try {
    const testData = {
      A: "Pickleball",
      B: "SUNDAY\n\nWTNB+\nSocial\nBuddy-Sign Up",
      C: "# of Players: 72",
      D: "October 12",
      E: "Dec 7",
      F: "$145",
      G: "12-3PM",
      H: "John Jay College",
      M: "Sept 18th 7PM",
      N: "Sept 17th 7PM",
      O: "Sept 19th 7PM"
    };

    const unresolved = [];
    const result = parseSourceRowEnhanced_(testData, unresolved);
    console.log('✅ Parse result:', {
      sportName: result.sportName,
      dayOfPlay: result.dayOfPlay,
      division: result.division,
      totalInventory: result.totalInventory
    });
  } catch (error) {
    console.log('❌ Parse test failed:', error.message);
  }
}
