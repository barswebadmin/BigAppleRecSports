/**
 * Comprehensive tests for parseDateFlexibleDateTime_ function
 *
 * @fileoverview Test suite for flexible datetime parsing
 * @requires ../src/helpers/dateParsers.gs
 */

// Import references for editor support
/// <reference path="../src/helpers/dateParsers.gs" />

/**
 * Main test function for parseDateFlexibleDateTime_
 */
function testParseDateFlexibleDateTime_() {
  console.log('🧪 Running parseDateFlexibleDateTime_ comprehensive tests...');

  let passedTests = 0;
  let totalTests = 0;
  const failedTests = [];

  // Test 1: Enhanced datetime parsing with day names and various formats
  totalTests++;
  const enhancedResult = testEnhancedDateTimeParsing_();
  if (enhancedResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 1 FAILED: Enhanced datetime parsing - ${enhancedResult}`);
  }

  // Test 2: Time zone conversion (ET to UTC)
  totalTests++;
  const timezoneResult = testTimezoneConversion_();
  if (timezoneResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 2 FAILED: Timezone conversion - ${timezoneResult}`);
  }

  // Test 3: Various date formats with time
  totalTests++;
  const formatResult = testVariousDateFormats_();
  if (formatResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 3 FAILED: Various date formats - ${formatResult}`);
  }

  // Display results
  console.log(`\n📊 parseDateFlexibleDateTime_ Test Summary:`);
  console.log(`   Tests Run: ${totalTests}`);
  console.log(`   Tests Passed: ${passedTests}`);
  console.log(`   Tests Failed: ${failedTests.length}`);

  if (failedTests.length > 0) {
    failedTests.forEach(failure => console.log(failure));
    throw new Error('❌ Some parseDateFlexibleDateTime_ tests failed!');
  }
}

/**
 * Tests enhanced datetime parsing with day names and various formats.
 * @returns {boolean|string} True if all tests pass, or an error message.
 */
function testEnhancedDateTimeParsing_() {
  const testCases = [
    {
      input: "Sept 16th 7PM",
      expected: new Date('2025-09-16T23:00:00Z'), // 7PM ET = 11PM UTC
      description: "Sept 16th 7PM"
    },
    {
      input: "Weds, Sept. 3rd, 6pm",
      expected: new Date('2025-09-03T22:00:00Z'), // 6PM ET = 10PM UTC
      description: "Weds, Sept. 3rd, 6pm"
    },
    {
      input: "8/29/25 @ 7pm",
      expected: new Date('2025-08-29T23:00:00Z'), // 7PM ET = 11PM UTC
      description: "8/29/25 @ 7pm"
    },
    {
      input: "Weds, Sept. 3rd, 7pm",
      expected: new Date('2025-09-03T23:00:00Z'), // 7PM ET = 11PM UTC
      description: "Weds, Sept. 3rd, 7pm"
    }
  ];

  for (const testCase of testCases) {
    const result = parseDateFlexibleDateTime_(testCase.input, null, 'testField');

    if (!result || !(result instanceof Date)) {
      return `FAIL for "${testCase.description}": Expected Date object, got ${typeof result}`;
    }

    // Check if the date matches expected (allowing for small time differences)
    const timeDiff = Math.abs(result.getTime() - testCase.expected.getTime());
    if (timeDiff > 1000) { // Allow 1 second difference
      return `FAIL for "${testCase.description}": Expected ${testCase.expected.toISOString()}, got ${result.toISOString()}`;
    }

  }
  return true;
}

/**
 * Tests timezone conversion from ET to UTC.
 * @returns {boolean|string} True if all tests pass, or an error message.
 */
function testTimezoneConversion_() {
  const testCases = [
    {
      input: "9/16/25 7PM",
      expectedHour: 23, // 7PM ET = 11PM UTC (ET is UTC-4 during daylight saving)
      description: "7PM ET should be 11PM UTC"
    },
    {
      input: "9/3/25 6PM",
      expectedHour: 22, // 6PM ET = 10PM UTC
      description: "6PM ET should be 10PM UTC"
    },
    {
      input: "12/15/25 7PM", // Winter time: ET is UTC-5
      expectedHour: 0, // 7PM ET = 12AM UTC next day (UTC-5)
      description: "7PM ET (winter) should be 12AM UTC next day"
    }
  ];

  for (const testCase of testCases) {
    const result = parseDateFlexibleDateTime_(testCase.input, null, 'testField');

    if (!result || !(result instanceof Date)) {
      return `FAIL for "${testCase.description}": Expected Date object, got ${typeof result}`;
    }

    // For December (winter), check next day at midnight
    if (testCase.input.includes('12/15')) {
      const expectedDate = new Date('2025-12-16T00:00:00Z');
      const timeDiff = Math.abs(result.getTime() - expectedDate.getTime());
      if (timeDiff > 1000) {
        return `FAIL for "${testCase.description}": Expected ${expectedDate.toISOString()}, got ${result.toISOString()}`;
      }
    } else {
      if (result.getUTCHours() !== testCase.expectedHour) {
        return `FAIL for "${testCase.description}": Expected hour ${testCase.expectedHour}, got ${result.getUTCHours()}`;
      }
    }
  }
  return true;
}

/**
 * Tests various date formats with time.
 * @returns {boolean|string} True if all tests pass, or an error message.
 */
function testVariousDateFormats_() {
  const testCases = [
    {
      input: "September 16, 2025 7:00 PM",
      description: "Full month name with time"
    },
    {
      input: "Sep 16 7PM",
      description: "Abbreviated month"
    },
    {
      input: "9-16-25 19:00",
      description: "24-hour time format"
    },
    {
      input: "Monday, Sept 16th at 7pm",
      description: "Day name with formatted date"
    }
  ];

  for (const testCase of testCases) {
    const result = parseDateFlexibleDateTime_(testCase.input, null, 'testField');

    // Should parse successfully and return a Date object
    if (!result || !(result instanceof Date)) {
      return `FAIL for "${testCase.description}": Expected Date object, got ${typeof result} - ${result}`;
    }

    // Should be in September 2025
    if (result.getUTCFullYear() !== 2025 || result.getUTCMonth() !== 8) { // September is month 8 (0-indexed)
      return `FAIL for "${testCase.description}": Expected September 2025, got ${result.getUTCFullYear()}-${result.getUTCMonth() + 1}`;
    }

  }
  return true;
}
