/**
 * Debug dodgeball registration parsing
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

console.log('🚀 Setting up VM context...');

const context = {
  console: console,
  Logger: { log: console.log },
};

vm.createContext(context);

function loadGasFile(filePath) {
  const fullPath = path.resolve(__dirname, '../../projects/parse-registration-info', filePath);
  if (fs.existsSync(fullPath)) {
    const content = fs.readFileSync(fullPath, 'utf8');
    try {
      vm.runInContext(content, context);
      return true;
    } catch (error) {
      console.log(`❌ Error loading ${filePath}:`, error.message);
      return false;
    }
  }
  return false;
}

// Load all required files
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
];

files.forEach(loadGasFile);

console.log('🧪 Testing dodgeball registration parsing...');

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
};

console.log('📋 Test data registration fields:');
console.log('  M (Early):', testData.M);
console.log('  N (Vet):', testData.N);
console.log('  O (Open):', testData.O);

const unresolved = [];
const parsed = vm.runInContext('parseSourceRowEnhanced_(testData, unresolved)',
  Object.assign(context, { testData, unresolved }));

console.log('\n📊 Parsed registration fields:');
console.log('  vetRegistrationStartDateTime:', parsed.vetRegistrationStartDateTime);
console.log('  earlyRegistrationStartDateTime:', parsed.earlyRegistrationStartDateTime);
console.log('  openRegistrationStartDateTime:', parsed.openRegistrationStartDateTime);

console.log('\n🔍 Unresolved issues:');
unresolved.forEach(issue => console.log('  -', issue));

console.log('\n🎯 Debug completed!');
