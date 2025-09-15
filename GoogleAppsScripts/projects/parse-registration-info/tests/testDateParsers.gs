/**
 * Comprehensive tests for dateParsers.gs functions
 *
 * @fileoverview Test suite for date parsing utilities
 * @requires ../src/helpers/dateParsers.gs
 */

// Import references for editor support
/// <reference path="../src/helpers/dateParsers.gs" />

/**
 * Main test function for dateParsers functions
 */
function testDateParsers_() {
  console.log('🧪 Running dateParsers comprehensive tests...');

  let passedTests = 0;
  let totalTests = 0;
  const failedTests = [];

  // Test 1: calculateYearIfNotProvided function
  totalTests++;
  const yearCalculationResult = testCalculateYearIfNotProvided_();
  if (yearCalculationResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 1 FAILED: calculateYearIfNotProvided - ${yearCalculationResult}`);
  }

  // Test 2: parseFlexibleDate_ function
  totalTests++;
  const flexibleDateResult = testParseFlexibleDate_();
  if (flexibleDateResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 2 FAILED: parseFlexibleDate_ - ${flexibleDateResult}`);
  }

  // Test 3: parseMonthName_ function
  totalTests++;
  const monthNameResult = testParseMonthName_();
  if (monthNameResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 3 FAILED: parseMonthName_ - ${monthNameResult}`);
  }

  // Test 4: normalizeYear_ function
  totalTests++;
  const normalizeYearResult = testNormalizeYear_();
  if (normalizeYearResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 4 FAILED: normalizeYear_ - ${normalizeYearResult}`);
  }

  // Display results
  console.log(`\n📊 dateParsers Test Summary:`);
  console.log(`   Tests Run: ${totalTests}`);
  console.log(`   Tests Passed: ${passedTests}`);
  console.log(`   Tests Failed: ${failedTests.length}`);

  if (failedTests.length > 0) {
    failedTests.forEach(failure => console.log(failure));
    throw new Error('❌ Some dateParsers tests failed!');
  }
}

/**
 * Test calculateYearIfNotProvided function
 * @returns {boolean|string} True if all tests pass, or an error message.
 */
function testCalculateYearIfNotProvided_() {
  const currentYear = new Date().getFullYear();

  const testCases = [
    // Test dates in the future (this year)
    { input: 'October 15', description: 'October 15 (future date this year)' },
    { input: 'December 25', description: 'December 25 (future date this year)' },
    { input: '10/15', description: '10/15 (numeric format, future)' },
    { input: '12-25', description: '12-25 (dash format, future)' },

    // Test past dates (should use next year)
    { input: 'January 1', description: 'January 1 (past date, should use next year)' },
    { input: 'March 15', description: 'March 15 (might be past, depending on current date)' },
    { input: '1/1', description: '1/1 (numeric, past date)' },

    // Test edge cases
    { input: '', description: 'Empty string' },
    { input: null, description: 'Null input' },
    { input: 'invalid date', description: 'Invalid date string' },
    { input: 'Oct 32nd', description: 'Invalid day' }
  ];

  for (const testCase of testCases) {
    const result = calculateYearIfNotProvided(testCase.input);

    // Result should be a valid year (current or next)
    if (typeof result !== 'number' || result < currentYear || result > currentYear + 1) {
      return `FAIL for "${testCase.description}": Expected ${currentYear} or ${currentYear + 1}, got ${result}`;
    }

    // For invalid inputs, should return current year
    if ((!testCase.input || testCase.input === 'invalid date' || testCase.input === 'Oct 32nd') && result !== currentYear) {
      return `FAIL for "${testCase.description}": Invalid input should return current year ${currentYear}, got ${result}`;
    }
  }

  // Test specific logic with known dates
  const now = new Date();
  const currentMonth = now.getMonth() + 1;
  const currentDay = now.getDate();

  // Test October 15 specifically (should be current year since we're in September)
  const oct15Result = calculateYearIfNotProvided('October 15');
  if (oct15Result !== currentYear) {
    return `FAIL: October 15 should use current year ${currentYear}, got ${oct15Result}`;
  }

  // Test a past date like January 1 (should be next year)
  const jan1Result = calculateYearIfNotProvided('January 1');
  if (jan1Result !== currentYear + 1) {
    return `FAIL: January 1 should use next year ${currentYear + 1}, got ${jan1Result}`;
  }

  return true;
}

/**
 * Test parseFlexibleDate_ function
 * @returns {boolean|string} True if all tests pass, or an error message.
 */
function testParseFlexibleDate_() {
  const testCases = [
    // Test with explicit years
    { input: '10/15/25', expectedYear: 2025, description: '10/15/25 format' },
    { input: '12/10/2025', expectedYear: 2025, description: '12/10/2025 format' },
    { input: '3-15-26', expectedYear: 2026, description: '3-15-26 format' },

    // Test text formats with years
    { input: 'October 15, 2025', expectedYear: 2025, description: 'October 15, 2025 format' },
    { input: 'Dec 25th, 2025', expectedYear: 2025, description: 'Dec 25th, 2025 format' },

    // Test text formats without years (should use calculateYearIfNotProvided logic)
    { input: 'October 15', expectedYear: calculateYearIfNotProvided('October 15'), description: 'October 15 (no year)' },
    { input: 'January 1', expectedYear: calculateYearIfNotProvided('January 1'), description: 'January 1 (no year)' },

    // Test invalid inputs
    { input: '', expected: null, description: 'Empty string' },
    { input: 'invalid', expected: null, description: 'Invalid date' },
    { input: null, expected: null, description: 'Null input' }
  ];

  for (const testCase of testCases) {
    const result = parseFlexibleDate_(testCase.input);

    if (testCase.expected === null) {
      if (result !== null) {
        return `FAIL for "${testCase.description}": Expected null, got ${result}`;
      }
    } else {
      if (!result || !(result instanceof Date)) {
        return `FAIL for "${testCase.description}": Expected Date object, got ${typeof result}`;
      }

      if (testCase.expectedYear && result.getFullYear() !== testCase.expectedYear) {
        return `FAIL for "${testCase.description}": Expected year ${testCase.expectedYear}, got ${result.getFullYear()}`;
      }
    }
  }

  return true;
}

/**
 * Test parseMonthName_ function
 * @returns {boolean|string} True if all tests pass, or an error message.
 */
function testParseMonthName_() {
  const testCases = [
    // Full month names
    { input: 'January', expected: 1 },
    { input: 'February', expected: 2 },
    { input: 'March', expected: 3 },
    { input: 'April', expected: 4 },
    { input: 'May', expected: 5 },
    { input: 'June', expected: 6 },
    { input: 'July', expected: 7 },
    { input: 'August', expected: 8 },
    { input: 'September', expected: 9 },
    { input: 'October', expected: 10 },
    { input: 'November', expected: 11 },
    { input: 'December', expected: 12 },

    // Abbreviated month names
    { input: 'Jan', expected: 1 },
    { input: 'Feb', expected: 2 },
    { input: 'Mar', expected: 3 },
    { input: 'Apr', expected: 4 },
    { input: 'Jun', expected: 6 },
    { input: 'Jul', expected: 7 },
    { input: 'Aug', expected: 8 },
    { input: 'Sep', expected: 9 },
    { input: 'Sept', expected: 9 },
    { input: 'Oct', expected: 10 },
    { input: 'Nov', expected: 11 },
    { input: 'Dec', expected: 12 },

    // Case insensitive
    { input: 'JANUARY', expected: 1 },
    { input: 'october', expected: 10 },
    { input: 'DeCeMbEr', expected: 12 },

    // Invalid inputs
    { input: 'InvalidMonth', expected: null },
    { input: '', expected: null },
    { input: null, expected: null },
    { input: '13', expected: null }
  ];

  for (const testCase of testCases) {
    const result = parseMonthName_(testCase.input);

    if (result !== testCase.expected) {
      return `FAIL for "${testCase.input}": Expected ${testCase.expected}, got ${result}`;
    }
  }

  return true;
}

/**
 * Test normalizeYear_ function
 * @returns {boolean|string} True if all tests pass, or an error message.
 */
function testNormalizeYear_() {
  const testCases = [
    // 2-digit years (00-30 = 2000s, 31-99 = 1900s)
    { input: 0, expected: 2000 },
    { input: 25, expected: 2025 },
    { input: 30, expected: 2030 },
    { input: 31, expected: 1931 },
    { input: 50, expected: 1950 },
    { input: 99, expected: 1999 },

    // 4-digit years (should remain unchanged)
    { input: 2000, expected: 2000 },
    { input: 2025, expected: 2025 },
    { input: 1995, expected: 1995 }
  ];

  for (const testCase of testCases) {
    const result = normalizeYear_(testCase.input);

    if (result !== testCase.expected) {
      return `FAIL for year ${testCase.input}: Expected ${testCase.expected}, got ${result}`;
    }
  }

  return true;
}
