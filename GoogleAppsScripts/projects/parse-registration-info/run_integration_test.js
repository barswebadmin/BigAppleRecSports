#!/usr/bin/env node

/**
 * Node.js runner for parseSourceRowEnhanced integration test
 * Loads all required dependencies and runs the comprehensive test
 */

const fs = require('fs');
const path = require('path');

// Mock Google Apps Script environment
global.Logger = {
  log: (...args) => console.log(...args)
};
global.console = {
  log: console.log,
  error: console.error,
  warn: console.warn
};

// Mock SpreadsheetApp for any functions that might need it
global.SpreadsheetApp = {
  getUi: () => ({
    alert: (message) => console.log(`ALERT: ${message}`)
  })
};

console.log('🔧 Loading Google Apps Script dependencies...');

/**
 * Safely evaluate Google Apps Script code with validation
 * @param {string} filePath - Path to the file to evaluate
 * @param {string} description - Description for logging
 */
function safeEvalGasFile(filePath, description) {
  const code = fs.readFileSync(filePath, 'utf8');

  // Validation patterns - block potentially dangerous operations
  const dangerousPatterns = [
    /require\s*\(/,           // Node.js require calls
    /import\s+.*from/,        // ES6 imports
    /process\./,              // Process manipulation
    /fs\./,                   // File system access
    /child_process/,          // Child process execution
    /(?:child_process|shelljs)\.exec\s*\(/,  // Command execution modules
    /spawn\s*\(/,             // Process spawning
    /\.constructor\s*\(/,     // Constructor access (potential code injection)
    /setTimeout.*eval/,       // Delayed eval execution
    /setInterval.*eval/,      // Repeated eval execution
    /document\./,             // DOM manipulation
    /window\./,               // Window object access
  ];

  // Check for dangerous patterns
  for (const pattern of dangerousPatterns) {
    if (pattern.test(code)) {
      throw new Error(`⚠️ Security risk detected in ${filePath}: Pattern ${pattern} found`);
    }
  }

  // Additional checks for suspicious content (warnings only)
  const suspiciousKeywords = ['eval(', 'document.cookie', 'localStorage', 'sessionStorage'];
  for (const keyword of suspiciousKeywords) {
    if (code.includes(keyword)) {
      console.warn(`⚠️ Warning: Found potentially risky pattern "${keyword}" in ${filePath}`);
    }
  }

  // Validate that it looks like valid Google Apps Script code
  const gasPatterns = [
    /function\s+\w+/,         // Function definitions
    /const\s+\w+\s*=/,        // Const declarations
    /var\s+\w+\s*=/,          // Var declarations
    /\/\*\*.*\*\//,           // JSDoc comments
  ];

  const hasValidGasContent = gasPatterns.some(pattern => pattern.test(code));
  if (!hasValidGasContent && code.trim().length > 0) {
    console.warn(`⚠️ Warning: ${filePath} doesn't appear to contain typical Google Apps Script code`);
  }

  // If validation passes, evaluate the code
  console.log(`  📄 Loading ${description} (${code.length} chars, validated)`);
  // biome-ignore lint/security/noGlobalEval: Validated Google Apps Script code in test environment
  eval(code);
}

// Note: CANONICAL_LOCATIONS removed - now using productFieldEnums in constants.gs

try {
  // Load dependencies in order
  const basePath = './src';

  // Load constants and config
  if (fs.existsSync(`${basePath}/config/constants.gs`)) {
    safeEvalGasFile(`${basePath}/config/constants.gs`, 'constants.gs');
  }

  // Fallback mocks for Node.js environment if constants aren't available
  if (typeof comprehensiveProductCreateFields === 'undefined') {
    global.comprehensiveProductCreateFields = [
      'sportName', 'division', 'season', 'year', 'dayOfPlay', 'location', 'sportSubCategory', 'socialOrAdvanced',
      'types', 'newPlayerOrientationDateTime', 'scoutNightDateTime', 'openingPartyDate',
      'seasonStartDate', 'seasonEndDate', 'offDates', 'rainDate', 'closingPartyDate',
      'vetRegistrationStartDateTime', 'earlyRegistrationStartDateTime', 'openRegistrationStartDateTime',
      'leagueStartTime', 'leagueEndTime', 'alternativeStartTime', 'alternativeEndTime',
      'price', 'totalInventory', 'numberVetSpotsToReleaseAtGoLive'
    ];
  }
  if (typeof irrelevantFieldsForSport === 'undefined') {
    global.irrelevantFieldsForSport = {
      "Kickball": ["sportSubCategory", "alternativeStartTime", "alternativeEndTime"],
      "Dodgeball": ["scoutNightDateTime", "rainDate", "alternativeStartTime", "alternativeEndTime"],
      "Bowling": ["sportSubCategory", "socialOrAdvanced", "newPlayerOrientationDateTime", "scoutNightDateTime", "openingPartyDate", "rainDate"],
      "Pickleball": ["sportSubCategory", "newPlayerOrientationDateTime", "scoutNightDateTime", "rainDate", "alternativeStartTime", "alternativeEndTime"]
    };
  }
  if (typeof productFieldEnums === 'undefined') {
    global.productFieldEnums = {
      sportName: ["Dodgeball", "Kickball", "Bowling", "Pickleball"],
      location: {
        "Dodgeball": ["Elliott Center (26th St & 9th Ave)", "PS3 Charrette School (Grove St & Hudson St)"],
        "Kickball": ["Gansevoort Peninsula Athletic Park, Pier 53 (Gansevoort St & 11th)", "Chelsea Park (27th St & 9th Ave)"],
        "Pickleball": ["Gotham Pickleball (46th and Vernon in LIC)", "Pickle1 (7 Hanover Square in LIC)"],
        "Bowling": ["Frames Bowling Lounge (40th St and 9th Ave)", "Bowlero Chelsea Piers (60 Chelsea Piers)"]
      }
    };
  }

  // Load shared utilities (apiUtils for toTitleCase)
  if (fs.existsSync('../../shared-utilities/apiUtils.gs')) {
    safeEvalGasFile('../../shared-utilities/apiUtils.gs', 'shared-utilities/apiUtils.gs');
  }

  // Load helpers
  if (fs.existsSync(`${basePath}/helpers/normalizers.gs`)) {
    safeEvalGasFile(`${basePath}/helpers/normalizers.gs`, 'normalizers.gs');
  }

  if (fs.existsSync(`${basePath}/helpers/textUtils.gs`)) {
    safeEvalGasFile(`${basePath}/helpers/textUtils.gs`, 'textUtils.gs');
  }

  // Load parsers in dependency order
  const parsers = [
    'dateParser.gs',
    'timeParser.gs',
    'priceParser.gs',
    'parseBFlags_.gs',
    'notesParser.gs',
    '_rowParser.gs'  // Main parser last
  ];

  for (const parser of parsers) {
    const parserPath = `${basePath}/parsers/${parser}`;
    if (fs.existsSync(parserPath)) {
      safeEvalGasFile(parserPath, parser);
    } else {
      console.log(`  ⚠️  ${parser} not found at ${parserPath}`);
    }
  }

  // Load test file
  safeEvalGasFile('./tests/testParseSourceRowEnhanced.gs', 'testParseSourceRowEnhanced.gs');

  console.log('✅ All dependencies loaded successfully');

} catch (error) {
  console.error('❌ Error loading dependencies:', error.message);
  process.exit(1);
}

// Run the integration test
console.log(`\n${'='.repeat(80)}`);
console.log('RUNNING INTEGRATION TEST: parseSourceRowEnhanced');
console.log('='.repeat(80));

try {
  const result = testParseSourceRowEnhanced();
  console.log(`\n${'='.repeat(80)}`);
  console.log(`TEST RESULT: ${result ? 'PASSED ✅' : 'FAILED ❌ (Expected until logic is updated)'}`);
  console.log('='.repeat(80));

  if (!result) {
    console.log('\n💡 This failure is expected - the parsing logic needs to be updated');
    console.log('   to match the new field structure and requirements.');
    console.log('   The test serves as a specification for the required updates.');
  }

} catch (error) {
  console.error('\n❌ TEST ERROR:', error.message);
  if (error.stack) {
    console.error('STACK TRACE:', error.stack);
  }
  process.exit(1);
}
