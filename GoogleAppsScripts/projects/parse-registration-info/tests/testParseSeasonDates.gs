/**
 * Test suite for parseSeasonDates_ function
 * Tests flexible date parsing with various formats
 *
 * @fileoverview Comprehensive tests for season date parsing
 * @requires ../src/parsers/parseSeasonDates.gs
 * @requires ../src/config/constants.gs
 * @requires ../src/helpers/normalizers.gs
 */

// Import references for editor support
/// <reference path="../src/parsers/parseSeasonDates.gs" />
/// <reference path="../src/config/constants.gs" />
/// <reference path="../src/helpers/normalizers.gs" />

/**
 * Main test function for parseSeasonDates_
 * Tests various date formats and edge cases
 */
function testParseSeasonDates_() {
  console.log('🧪 Running parseSeasonDates_ comprehensive tests...');

  let passedTests = 0;
  let totalTests = 0;
  const failedTests = [];

  // Initialize unresolved fields for testing (using Kickball as default)
  const baseUnresolved = initializeUnresolvedFields('Kickball');

  // Test 1: Numeric date formats
  totalTests++;
  const numericFormatResult = testNumericDateFormats_(baseUnresolved);
  if (numericFormatResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 1 FAILED: Numeric date formats - ${numericFormatResult}`);
  }

  // Test 2: Text-based date formats
  totalTests++;
  const textFormatResult = testTextDateFormats_(baseUnresolved);
  if (textFormatResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 2 FAILED: Text date formats - ${textFormatResult}`);
  }

  // Test 3: Ordinal date formats (with "th", "st", etc.)
  totalTests++;
  const ordinalFormatResult = testOrdinalDateFormats_(baseUnresolved);
  if (ordinalFormatResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 3 FAILED: Ordinal date formats - ${ordinalFormatResult}`);
  }

  // Test 4: Season and year derivation
  totalTests++;
  const seasonYearResult = testSeasonYearDerivation_(baseUnresolved);
  if (seasonYearResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 4 FAILED: Season/year derivation - ${seasonYearResult}`);
  }

  // Test 5: Edge cases and error handling
  totalTests++;
  const edgeCasesResult = testEdgeCases_(baseUnresolved);
  if (edgeCasesResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 5 FAILED: Edge cases - ${edgeCasesResult}`);
  }

  // Test 6: UTC timestamp consistency
  totalTests++;
  const utcTimestampResult = testUTCTimestampConsistency_(baseUnresolved);
  if (utcTimestampResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 6 FAILED: UTC timestamp consistency - ${utcTimestampResult}`);
  }

  // Display results
  console.log(`\n📊 parseSeasonDates_ Test Summary:`);
  console.log(`   Tests Run: ${totalTests}`);
  console.log(`   Tests Passed: ${passedTests}`);
  console.log(`   Tests Failed: ${totalTests - passedTests}`);

  if (failedTests.length > 0) {
    console.log('\n❌ Failed Tests:');
    failedTests.forEach(failure => console.log(`   ${failure}`));
    console.log('❌ Some parseSeasonDates_ tests failed!');
  } else {
    console.log('✅ All parseSeasonDates_ tests passed!');
  }

  return passedTests === totalTests;
}

/**
 * Test numeric date formats: M/d/yy, M/d/yyyy, M-d-yy, M-d-yyyy
 * @param {Array<string>} baseUnresolved - Base unresolved fields array
 * @returns {boolean|string} true if passed, error message if failed
 */
function testNumericDateFormats_(baseUnresolved) {
  try {
    const testCases = [
      { start: '10/15/25', end: '12/10/25', expectedStartUTC: '2025-10-15T04:00:00.000Z', expectedEndUTC: '2025-12-10T04:00:00.000Z' },
      { start: '10/15/2025', end: '12/10/2025', expectedStartUTC: '2025-10-15T04:00:00.000Z', expectedEndUTC: '2025-12-10T04:00:00.000Z' },
      { start: '10-15-25', end: '12-10-25', expectedStartUTC: '2025-10-15T04:00:00.000Z', expectedEndUTC: '2025-12-10T04:00:00.000Z' },
      { start: '10-15-2025', end: '12-10-2025', expectedStartUTC: '2025-10-15T04:00:00.000Z', expectedEndUTC: '2025-12-10T04:00:00.000Z' },
      { start: '1/5/25', end: '3/20/25', expectedStartUTC: '2025-01-05T04:00:00.000Z', expectedEndUTC: '2025-03-20T04:00:00.000Z' }
    ];

    for (const testCase of testCases) {
      const unresolved = [...baseUnresolved];
      const result = parseSeasonDates_(testCase.start, testCase.end, unresolved);

      if (!result.seasonStartDate || result.seasonStartDate.toISOString() !== testCase.expectedStartUTC) {
        return `Start date mismatch for "${testCase.start}": expected ${testCase.expectedStartUTC}, got ${result.seasonStartDate?.toISOString()}`;
      }

      if (!result.seasonEndDate || result.seasonEndDate.toISOString() !== testCase.expectedEndUTC) {
        return `End date mismatch for "${testCase.end}": expected ${testCase.expectedEndUTC}, got ${result.seasonEndDate?.toISOString()}`;
      }

      // Validate that all season-related fields were removed from unresolved
      const expectedRemainingFields = baseUnresolved.filter(field =>
        !['seasonStartDate', 'seasonEndDate', 'season', 'year'].includes(field)
      );
      if (JSON.stringify(result.updatedUnresolved.sort()) !== JSON.stringify(expectedRemainingFields.sort())) {
        return `Unresolved fields mismatch for "${testCase.start}/${testCase.end}": expected [${expectedRemainingFields.join(', ')}], got [${result.updatedUnresolved.join(', ')}]`;
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testNumericDateFormats_: ${error.toString()}`;
  }
}

/**
 * Test text-based date formats: "October 12", "Oct 14"
 * @param {Array<string>} baseUnresolved - Base unresolved fields array
 * @returns {boolean|string} true if passed, error message if failed
 */
function testTextDateFormats_(baseUnresolved) {
  try {
    const currentYear = new Date().getFullYear();
    const testCases = [
      { start: 'October 15', expectedStartUTC: `${currentYear}-10-15T04:00:00.000Z` },
      { start: 'Oct 15', expectedStartUTC: `${currentYear}-10-15T04:00:00.000Z` },
      { start: 'December 10', expectedStartUTC: `${currentYear}-12-10T04:00:00.000Z` },
      { start: 'Dec 10', expectedStartUTC: `${currentYear}-12-10T04:00:00.000Z` },
      { start: 'January 5', expectedStartUTC: `${currentYear}-01-05T04:00:00.000Z` },
      { start: 'Jan 5', expectedStartUTC: `${currentYear}-01-05T04:00:00.000Z` }
    ];

    for (const testCase of testCases) {
      const unresolved = [...baseUnresolved];
      const result = parseSeasonDates_(testCase.start, '', unresolved);

      if (!result.seasonStartDate || result.seasonStartDate.toISOString() !== testCase.expectedStartUTC) {
        return `Start date mismatch for "${testCase.start}": expected ${testCase.expectedStartUTC}, got ${result.seasonStartDate?.toISOString()}`;
      }

      // Validate that season-related fields (except seasonEndDate) were removed from unresolved
      const expectedRemainingFields = baseUnresolved.filter(field =>
        !['seasonStartDate', 'season', 'year'].includes(field)
      );
      if (JSON.stringify(result.updatedUnresolved.sort()) !== JSON.stringify(expectedRemainingFields.sort())) {
        return `Unresolved fields mismatch for "${testCase.start}": expected [${expectedRemainingFields.join(', ')}], got [${result.updatedUnresolved.join(', ')}]`;
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testTextDateFormats_: ${error.toString()}`;
  }
}

/**
 * Test ordinal date formats: "Oct 14th", "October 12th"
 * @param {Array<string>} baseUnresolved - Base unresolved fields array
 * @returns {boolean|string} true if passed, error message if failed
 */
function testOrdinalDateFormats_(baseUnresolved) {
  try {
    const currentYear = new Date().getFullYear();
    const testCases = [
      { start: 'Oct 14th', expectedStartUTC: `${currentYear}-10-14T04:00:00.000Z` },
      { start: 'October 12th', expectedStartUTC: `${currentYear}-10-12T04:00:00.000Z` },
      { start: 'Dec 1st', expectedStartUTC: `${currentYear}-12-01T04:00:00.000Z` },
      { start: 'January 22nd', expectedStartUTC: `${currentYear}-01-22T04:00:00.000Z` },
      { start: 'Mar 3rd', expectedStartUTC: `${currentYear}-03-03T04:00:00.000Z` }
    ];

    for (const testCase of testCases) {
      const unresolved = [...baseUnresolved];
      const result = parseSeasonDates_(testCase.start, '', unresolved);

      if (!result.seasonStartDate || result.seasonStartDate.toISOString() !== testCase.expectedStartUTC) {
        return `Start date mismatch for "${testCase.start}": expected ${testCase.expectedStartUTC}, got ${result.seasonStartDate?.toISOString()}`;
      }

      // Validate that season-related fields (except seasonEndDate) were removed from unresolved
      const expectedRemainingFields = baseUnresolved.filter(field =>
        !['seasonStartDate', 'season', 'year'].includes(field)
      );
      if (JSON.stringify(result.updatedUnresolved.sort()) !== JSON.stringify(expectedRemainingFields.sort())) {
        return `Unresolved fields mismatch for "${testCase.start}": expected [${expectedRemainingFields.join(', ')}], got [${result.updatedUnresolved.join(', ')}]`;
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testOrdinalDateFormats_: ${error.toString()}`;
  }
}

/**
 * Test season and year derivation accuracy
 * @param {Array<string>} baseUnresolved - Base unresolved fields array
 * @returns {boolean|string} true if passed, error message if failed
 */
function testSeasonYearDerivation_(baseUnresolved) {
  try {
    const testCases = [
      { start: '10/15/25', expectedSeason: 'Fall', expectedYear: 2025 },
      { start: '12/10/25', expectedSeason: 'Winter', expectedYear: 2025 },
      { start: '3/15/26', expectedSeason: 'Spring', expectedYear: 2026 },
      { start: '6/20/26', expectedSeason: 'Summer', expectedYear: 2026 },
      { start: 'October 15', expectedSeason: 'Fall', expectedYear: calculateYearIfNotProvided('October 15') }
    ];

    for (const testCase of testCases) {
      const unresolved = [...baseUnresolved];
      const result = parseSeasonDates_(testCase.start, '', unresolved);

      if (result.season !== testCase.expectedSeason) {
        return `Season mismatch for "${testCase.start}": expected ${testCase.expectedSeason}, got ${result.season}`;
      }

      if (result.year !== testCase.expectedYear) {
        return `Year mismatch for "${testCase.start}": expected ${testCase.expectedYear}, got ${result.year}`;
      }

      // Validate that season-related fields (except seasonEndDate) were removed from unresolved
      const expectedRemainingFields = baseUnresolved.filter(field =>
        !['seasonStartDate', 'season', 'year'].includes(field)
      );
      if (JSON.stringify(result.updatedUnresolved.sort()) !== JSON.stringify(expectedRemainingFields.sort())) {
        return `Unresolved fields mismatch for "${testCase.start}": expected [${expectedRemainingFields.join(', ')}], got [${result.updatedUnresolved.join(', ')}]`;
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testSeasonYearDerivation_: ${error.toString()}`;
  }
}

/**
 * Test edge cases and error handling
 * @param {Array<string>} baseUnresolved - Base unresolved fields array
 * @returns {boolean|string} true if passed, error message if failed
 */
function testEdgeCases_(baseUnresolved) {
  try {
    // Test empty/null/undefined inputs
    const edgeCases = [
      { start: '', end: '', expectedStartDate: null, expectedEndDate: null },
      { start: null, end: null, expectedStartDate: null, expectedEndDate: null },
      { start: undefined, end: undefined, expectedStartDate: null, expectedEndDate: null },
      { start: '   ', end: '   ', expectedStartDate: null, expectedEndDate: null },
      { start: 'invalid date', end: 'another invalid', expectedStartDate: null, expectedEndDate: null }
    ];

    for (const testCase of edgeCases) {
      const unresolved = [...baseUnresolved];
      const result = parseSeasonDates_(testCase.start, testCase.end, unresolved);

      if (result.seasonStartDate !== testCase.expectedStartDate) {
        return `Edge case start date mismatch for "${testCase.start}": expected ${testCase.expectedStartDate}, got ${result.seasonStartDate}`;
      }

      if (result.seasonEndDate !== testCase.expectedEndDate) {
        return `Edge case end date mismatch for "${testCase.end}": expected ${testCase.expectedEndDate}, got ${result.seasonEndDate}`;
      }

      // For invalid dates, all season-related fields should remain in unresolved
      if (testCase.expectedStartDate === null) {
        if (JSON.stringify(result.updatedUnresolved.sort()) !== JSON.stringify(baseUnresolved.sort())) {
          return `Edge case unresolved mismatch for invalid dates: expected [${baseUnresolved.join(', ')}], got [${result.updatedUnresolved.join(', ')}]`;
        }
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testEdgeCases_: ${error.toString()}`;
  }
}


/**
 * Test UTC timestamp consistency (October 12th should return Date('2025-10-13T04:00:00Z'))
 * @param {Array<string>} baseUnresolved - Base unresolved fields array
 * @returns {boolean|string} true if passed, error message if failed
 */
function testUTCTimestampConsistency_(baseUnresolved) {
  try {
    // Test the specific example from requirements
    const unresolved = [...baseUnresolved];
    const result = parseSeasonDates_('October 12', '', unresolved);

    const expectedYear = calculateYearIfNotProvided('October 12');
    const expectedUTC = `${expectedYear}-10-13T04:00:00.000Z`; // October 12th -> 13th at 4AM UTC

    if (!result.seasonStartDate || result.seasonStartDate.toISOString() !== expectedUTC) {
      return `UTC timestamp mismatch for "October 12": expected ${expectedUTC}, got ${result.seasonStartDate?.toISOString()}`;
    }

    // Test that all dates are consistently at 4:00 AM UTC
    const timeTestCases = ['10/15/25', 'Dec 25th', 'January 1'];

    for (const dateStr of timeTestCases) {
      const testUnresolved = [...baseUnresolved];
      const testResult = parseSeasonDates_(dateStr, '', testUnresolved);
      if (testResult.seasonStartDate) {
        const date = testResult.seasonStartDate;
        if (date.getUTCHours() !== 4 || date.getUTCMinutes() !== 0 || date.getUTCSeconds() !== 0) {
          return `Time not 4:00 AM UTC for "${dateStr}": got ${date.getUTCHours()}:${date.getUTCMinutes()}:${date.getUTCSeconds()} UTC`;
        }

        // Validate unresolved field tracking for each test case
        const expectedRemainingFields = baseUnresolved.filter(field =>
          !['seasonStartDate', 'season', 'year'].includes(field)
        );
        if (JSON.stringify(testResult.updatedUnresolved.sort()) !== JSON.stringify(expectedRemainingFields.sort())) {
          return `Unresolved fields mismatch for "${dateStr}": expected [${expectedRemainingFields.join(', ')}], got [${testResult.updatedUnresolved.join(', ')}]`;
        }
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testUTCTimestampConsistency_: ${error.toString()}`;
  }
}
