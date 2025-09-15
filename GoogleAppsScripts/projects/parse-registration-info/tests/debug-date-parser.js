/**
 * Debug date parser specifically
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

// Load date parser
loadGasFile('parsers/dateParser.gs');

console.log('🧪 Testing date parsing directly...');

const testStrings = [
  "Weds, Sept. 3rd, 6pm",
  "Tues, Sept. 2nd, 7pm",
  "Thurs, Sept. 4th, 6pm",
  "Sept. 3rd, 6pm",
  "Sept 3rd, 6pm",
  "September 3rd, 6pm",
  "Sep 3 6pm"
];

testStrings.forEach(dateStr => {
  console.log(`\n📅 Testing: "${dateStr}"`);

  // Test stripWeekdays_ function
  if ('stripWeekdays_' in context) {
    const stripped = vm.runInContext('stripWeekdays_(dateStr)',
      Object.assign(context, { dateStr }));
    console.log(`   After stripWeekdays_: "${stripped}"`);

    // Manual normalization like in parseFlexible_
    let normalized = stripped
      .replace(/@|at\s+/gi, ' ')
      .replace(/\s+/g, ' ')
      .trim();
    normalized = normalized.replace(/\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\.?\s*,?\s*/gi, '$1 ');
    console.log(`   After normalization: "${normalized}"`);
  }

  // Test full parsing
  if ('parseFlexible_' in context) {
    const result = vm.runInContext('parseFlexible_(dateStr, { assumeDateTime: true })',
      Object.assign(context, { dateStr }));
    console.log(`   Parse result: ${result ? result.toString() : 'null'}`);
  }

  // Test parseDateFlexibleDateTime_
  if ('parseDateFlexibleDateTime_' in context) {
    const sportTime = new Date(2025, 8, 3, 18, 30); // Sample sport time for context
    const result = vm.runInContext('parseDateFlexibleDateTime_(dateStr, sportTime, [])',
      Object.assign(context, { dateStr, sportTime }));
    console.log(`   DateTime parse result: ${result ? result.toString() : 'null'}`);
  }
});

console.log('\n🎯 Date parsing debug completed!');
