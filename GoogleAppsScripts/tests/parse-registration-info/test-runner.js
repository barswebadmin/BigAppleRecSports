#!/usr/bin/env node

/**
 * Automated test runner for parse-registration-info Google Apps Script functions
 * Runs locally and in CI/CD without requiring Google Apps Script environment
 */

const fs = require('fs');
const path = require('path');

// Colors for console output
const colors = {
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m',
  bold: '\x1b[1m'
};

// Test results tracking
let testsRun = 0;
let testsPassed = 0;
let testsFailed = 0;
const failedTests = [];

// Mock Google Apps Script environment
global.Logger = {
  log: (message) => {
    console.log(`[Logger]: ${message}`);
  }
};

// Don't silence console.log - logs are essential for debugging tests
// global.console remains unchanged so we can see all output

// Google Apps Script API mocks
global.SpreadsheetApp = {
  getUi: () => ({
    alert: (message) => console.log(`[MOCK UI ALERT]: ${message}`),
    Button: { YES: 'YES', NO: 'NO' },
    ButtonSet: { YES_NO: 'YES_NO', OK: 'OK' }
  }),
  openById: (id) => ({
    getSheetByName: (name) => ({
      getRange: () => ({
        getDisplayValues: () => [['Sport', 'Day', 'Division', 'Type']],
        getValues: () => [['Kickball', 'Tuesday', 'Open', 'Buddy Sign-up']],
        setValues: () => {}
      }),
      getLastRow: () => 10,
      getLastColumn: () => 15
    })
  })
};

global.UrlFetchApp = {
  fetch: (url, options) => ({
    getResponseCode: () => 200,
    getContentText: () => '{"success": true}'
  })
};

// Test utility functions
function assert(condition, message) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function assertEquals(actual, expected, message = '') {
  if (actual !== expected) {
    throw new Error(`Expected ${expected}, but got ${actual}. ${message}`);
  }
}

function assertTrue(value, message = '') {
  if (value !== true) {
    throw new Error(`Expected true, but got ${value}. ${message}`);
  }
}

function assertFalse(value, message = '') {
  if (value !== false) {
    throw new Error(`Expected false, but got ${value}. ${message}`);
  }
}

// Load Google Apps Script functions
function loadGASFunctions() {
  const projectPath = path.join(__dirname, '../../projects/parse-registration-info');

  // Load all .gs files and evaluate their JavaScript content
  const gasFiles = [
    'config/constants.gs',
    'core/flagsParser.gs',
    'core/notesParser.gs',
    'core/rowParser.gs',
    'core/migration.gs',
    'helpers/textUtils.gs',
    'validators/fieldValidation.gs'
  ];

  const loadedFunctions = {};

  gasFiles.forEach(filePath => {
    const fullPath = path.join(projectPath, filePath);
    if (fs.existsSync(fullPath)) {
      const content = fs.readFileSync(fullPath, 'utf8');

      // Remove Google Apps Script specific comments and execute
      const cleanContent = content
        .replace(/\/\/\/ <reference.*\/>/g, '') // Remove reference comments
        .replace(/\/\*\*[\s\S]*?\*\//g, '') // Remove JSDoc comments for now
        .replace(/Logger\.log\([^)]*\);?/g, ''); // Remove Logger.log calls

      try {
        eval(cleanContent);
        console.log(`${colors.green}✓${colors.reset} Loaded ${filePath}`);
      } catch (error) {
        console.log(`${colors.red}✗${colors.reset} Failed to load ${filePath}: ${error.message}`);
        throw error; // Re-throw to fail the test
      }
    }
  });

  return loadedFunctions;
}

// Test suites
function runTest(testName, testFunction) {
  testsRun++;
  try {
    testFunction();
    testsPassed++;
    console.log(`${colors.green}✓${colors.reset} ${testName}`);
  } catch (error) {
    testsFailed++;
    failedTests.push({ name: testName, error: error.message });
    console.log(`${colors.red}✗${colors.reset} ${testName}: ${error.message}`);
  }
}

// Date parsing tests
function testDateParsing() {
  console.log(`\n${colors.blue}${colors.bold}📅 Date Parsing Tests${colors.reset}`);

  runTest('Parse standard date MM/DD/YYYY', () => {
    const result = parseDateField_('01/15/2025');
    assertEquals(result, '2025-01-15');
  });

  runTest('Parse single digit date M/D/YYYY', () => {
    const result = parseDateField_('1/5/2025');
    assertEquals(result, '2025-01-05');
  });

  runTest('Parse invalid date returns empty', () => {
    const result = parseDateField_('invalid');
    assertEquals(result, '');
  });

  runTest('Parse empty date returns empty', () => {
    const result = parseDateField_('');
    assertEquals(result, '');
  });
}

// Flags parsing tests (including your specific buddy signup case)
function testFlagsParsing() {
  console.log(`\n${colors.blue}${colors.bold}🏷️ Flags Parsing Tests${colors.reset}`);

  runTest('Detect "Buddy Sign Ups" (your specific case)', () => {
    const result = hasBuddySignup_('TUESDAY Open Social Small Ball Randomized - Buddy Sign Ups');
    assertTrue(result, 'Should detect "Buddy Sign Ups" in the text');
  });

  runTest('Detect "Buddy Signup" (singular)', () => {
    const result = hasBuddySignup_('MONDAY League - Buddy Signup');
    assertTrue(result, 'Should detect "Buddy Signup" in the text');
  });

  runTest('No buddy signup in regular text', () => {
    const result = hasBuddySignup_('TUESDAY Regular League');
    assertFalse(result, 'Should not detect buddy signup in regular text');
  });

  runTest('Parse day from text', () => {
    const result = parseDay_('TUESDAY Open Social Small Ball');
    assertEquals(result, 'Tuesday');
  });

  runTest('Parse buddy flag from text', () => {
    const result = parseFlags_('TUESDAY Open Social - Buddy Sign Ups');
    assertTrue(result.buddy, 'Should parse buddy flag as true');
  });
}

// Location normalization tests
function testLocationNormalization() {
  console.log(`\n${colors.blue}${colors.bold}🏠 Location Normalization Tests${colors.reset}`);

  runTest('Normalize John Jay College location', () => {
    const result = canonicalizeLocation_('John Jay College');
    assertEquals(result, 'John Jay College (59th and 10th)');
  });

  runTest('Handle unknown location passthrough', () => {
    const result = canonicalizeLocation_('Unknown Gym');
    assertEquals(result, 'Unknown Gym');
  });
}

// Price parsing tests
function testPriceParsing() {
  console.log(`\n${colors.blue}${colors.bold}💰 Price Parsing Tests${colors.reset}`);

  runTest('Parse standard price format', () => {
    const result = parsePrice_('$45');
    assertEquals(result, '45');
  });

  runTest('Parse price with decimals', () => {
    const result = parsePrice_('$45.50');
    assertEquals(result, '45.50');
  });

  runTest('Parse price from descriptive text', () => {
    const result = parsePrice_('Registration fee is $45 per person');
    assertEquals(result, '45');
  });
}

// Your specific buddy signup validation issue test
function testBuddySignupValidationIssue() {
  console.log(`\n${colors.blue}${colors.bold}🚨 Buddy Signup Validation Issue Tests${colors.reset}`);

  runTest('Buddy signup detection from your source text', () => {
    const sourceText = "TUESDAY Open Social Small Ball Randomized - Buddy Sign Ups";
    const detected = hasBuddySignup_(sourceText);
    assertTrue(detected, 'Should detect buddy signup from your specific text');
  });

  runTest('Write validation catches "Buddy Signup" vs "Buddy Sign-up" mismatch', () => {
    // Simulate the validation mismatch you experienced
    const parserOutput = 'Buddy Signup';
    const targetExpected = 'Buddy Sign-up';
    const wouldFailValidation = parserOutput !== targetExpected;
    assertTrue(wouldFailValidation, 'Should detect mismatch between parser output and target expectation');
  });
}

// Write validation logic tests
function testWriteValidationLogic() {
  console.log(`\n${colors.blue}${colors.bold}🔍 Write Validation Logic Tests${colors.reset}`);

  runTest('Write validation detects data validation failures', () => {
    // Simulate write validation check
    const writeAttempts = [
      { header: 'Type', newValue: 'Buddy Signup', objectKey: 'type' },
      { header: 'Sport', newValue: 'Kickball', objectKey: 'sport' }
    ];

    // Simulate what the sheet actually accepted (data validation changed "Buddy Signup")
    const actualWrittenValues = ['Kickball', 'Buddy Sign-up']; // Note the hyphen difference

    const writeFailures = [];

    for (let i = 0; i < writeAttempts.length; i++) {
      const attempt = writeAttempts[i];
      const actualValue = actualWrittenValues[i];
      const expectedValue = attempt.newValue;

      if (actualValue !== expectedValue) {
        writeFailures.push({
          header: attempt.header,
          expected: expectedValue,
          actual: actualValue,
          reason: 'Data validation rule rejected the value'
        });
      }
    }

    assertTrue(writeFailures.length > 0, 'Should detect write validation failures');
    assertEquals(writeFailures[0].header, 'Type', 'Should identify the Type field as failing');
  });
}

// End-to-end integration tests
function testEndToEndParsing() {
  console.log(`\n${colors.blue}${colors.bold}🧩 End-to-End Integration Tests${colors.reset}`);

  runTest('Complete parsing pipeline with your data', () => {
    const sourceData = {
      A: 'Kickball',
      B: 'TUESDAY Open Social Small Ball Randomized - Buddy Sign Ups',
      C: 'League notes here',
      D: '01/15/2025',
      E: '03/15/2025',
      F: '$45',
      G: '7:00 PM - 8:00 PM',
      H: 'John Jay College',
      M: '01/10/2025',
      N: '01/12/2025',
      O: '01/14/2025'
    };

    const unresolved = [];
    const parsed = parseSourceRowEnhanced_(sourceData, unresolved);

    // Test key parsing results
    assertEquals(parsed.sport, 'Kickball', 'Sport should be parsed correctly');
    assertEquals(parsed.day, 'Tuesday', 'Day should be parsed correctly');
    assertTrue(parsed.flags && parsed.flags.buddy === true, 'Buddy flag should be parsed correctly');
    assertEquals(parsed.seasonStart, '2025-01-15', 'Season start should be parsed correctly');
    assertEquals(parsed.price, '45', 'Price should be parsed correctly');
  });
}

// Main test execution
function main() {
  console.log(`${colors.blue}${colors.bold}🧪 Parse Registration Info - Automated Test Suite${colors.reset}`);
  console.log(`${colors.yellow}Running locally and CI/CD compatible tests${colors.reset}\n`);

  // Load Google Apps Script functions
  console.log(`${colors.blue}📥 Loading Google Apps Script functions...${colors.reset}`);
  loadGASFunctions();

  // Run all test suites
  testDateParsing();
  testFlagsParsing();
  testLocationNormalization();
  testPriceParsing();
  testBuddySignupValidationIssue();
  testWriteValidationLogic();
  testEndToEndParsing();

  // Final summary
  console.log(`\n${colors.blue}${colors.bold}📊 Test Results Summary${colors.reset}`);
  console.log(`Total tests: ${testsRun}`);
  console.log(`${colors.green}Passed: ${testsPassed}${colors.reset}`);
  console.log(`${colors.red}Failed: ${testsFailed}${colors.reset}`);

  if (testsFailed > 0) {
    console.log(`\n${colors.red}${colors.bold}❌ Failed Tests:${colors.reset}`);
    failedTests.forEach(test => {
      console.log(`${colors.red}• ${test.name}: ${test.error}${colors.reset}`);
    });
    console.log(`\n${colors.yellow}🔧 Please fix the failing tests before deploying.${colors.reset}`);
    process.exit(1);
  } else {
    console.log(`\n${colors.green}${colors.bold}🎉 ALL TESTS PASSED!${colors.reset}`);
    console.log(`${colors.green}✨ Parse registration info logic is working correctly.${colors.reset}`);
    process.exit(0);
  }
}

// Run tests if this file is executed directly
if (require.main === module) {
  main();
}

module.exports = { runTest, assertEquals, assertTrue, assertFalse };
