/**
 * Comprehensive tests for parseColCLeagueDetails_ function
 *
 * @fileoverview Test suite for column C league details parsing
 * @requires ../src/parsers/parseColC.gs
 * @requires ../src/helpers/dateParsers.gs
 */

// Import references for editor support
/// <reference path="../src/parsers/parseColCLeagueDetails_.gs" />
/// <reference path="../src/helpers/dateParsers.gs" />

/**
 * Main test function for parseColCLeagueDetails_
 */
function testParseColCLeagueDetails_() {
  console.log('🧪 Running parseColCLeagueDetails_ comprehensive tests...');

  let passedTests = 0;
  let totalTests = 0;
  const failedTests = [];

  // Test 1: Parse comprehensive league details
  totalTests++;
  const comprehensiveResult = testComprehensiveLeagueDetails_();
  if (comprehensiveResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 1 FAILED: Comprehensive league details - ${comprehensiveResult}`);
  }

  // Test 2: Parse empty/null input
  totalTests++;
  const emptyInputResult = testEmptyInput_();
  if (emptyInputResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 2 FAILED: Empty input handling - ${emptyInputResult}`);
  }

  // Test 3: Parse partial data
  totalTests++;
  const partialDataResult = testPartialData_();
  if (partialDataResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 3 FAILED: Partial data parsing - ${partialDataResult}`);
  }

  // Display results
  console.log(`\n📊 parseColCLeagueDetails_ Test Summary:`);
  console.log(`   Tests Run: ${totalTests}`);
  console.log(`   Tests Passed: ${passedTests}`);
  console.log(`   Tests Failed: ${failedTests.length}`);

  if (failedTests.length > 0) {
    for (const failure of failedTests) {
      console.log(failure);
    }
    throw new Error('❌ Some parseColCLeagueDetails_ tests failed!');
  }
}

/**
 * Test comprehensive league details parsing with the provided example
 * @returns {boolean|string} True if all tests pass, or an error message.
 */
function testComprehensiveLeagueDetails_() {
  const colCValue = `Total # of Weeks: 9
Regular Season: 8 weeks
Tournament Date:
Closing Party: Date TBD

Skipping 11/25
Tournament Date: Dec 9

# of Teams: 16
# of Players: 64 (4 players per team)

All teams play two 45 min matches per night`;

  const result = parseColCLeagueDetails_(colCValue);

  // Validate expected parsed values
  if (result.closingPartyDate !== 'TBD') {
    return `FAIL: Expected closingPartyDate to be 'TBD', got ${result.closingPartyDate}`;
  }

  // Validate offDates array
  if (!Array.isArray(result.offDates)) {
    return `FAIL: Expected offDates to be an array, got ${typeof result.offDates}`;
  }

  if (result.offDates.length !== 1) {
    return `FAIL: Expected offDates to have 1 element, got ${result.offDates.length}`;
  }

  // Check if the date is correct (11/25 -> should be next occurrence)
  // Since we're testing "11/25" and it's September 2025, the next occurrence would be November 25, 2025
  const actualOffDateStr = result.offDates[0].toISOString();
  if (!actualOffDateStr.includes('11-26T04:00:00')) {
    return `FAIL: Expected offDates[0] to be November 26 at 4AM UTC (11/25 EST converted), got ${actualOffDateStr}`;
  }

  // Validate tournament date
  const expectedTournamentDate = new Date('2025-12-10T04:00:00Z');
  if (!result.tournamentDate || result.tournamentDate.toISOString() !== expectedTournamentDate.toISOString()) {
    return `FAIL: Expected tournamentDate to be ${expectedTournamentDate.toISOString()}, got ${result.tournamentDate?.toISOString()}`;
  }

  // Validate total inventory
  if (result.totalInventory !== 64) {
    return `FAIL: Expected totalInventory to be 64, got ${result.totalInventory}`;
  }

  // New: verify we capture Buddy Sign-up hint when present
  const row5Sample = `2 sessions; 350-364 players, 50-52 teams, 7 players max
Teams are randomly assigned
Players are able to sign-up with one buddy
Times: 12:45-2:45PM & 3:00-5:00PM

NOTE: SKIPPING 11/9 to accommodate for all sports charity awards event.`;
  const row5Res = parseColCLeagueDetails_(row5Sample);
  if (row5Res.totalInventory !== 364) {
    return `FAIL: Expected 364 inventory from range, got ${row5Res.totalInventory}`;
  }
  if (!Array.isArray(row5Res.typesHint) || row5Res.typesHint.indexOf('Buddy Sign-up') === -1) {
    return 'FAIL: Expected typesHint to include Buddy Sign-up';
  }

  return true;
}

/**
 * Test empty/null input handling
 * @returns {boolean|string} True if all tests pass, or an error message.
 */
function testEmptyInput_() {
  const testCases = [
    { input: '', description: 'Empty string' },
    { input: null, description: 'Null input' },
    { input: undefined, description: 'Undefined input' },
    { input: '   ', description: 'Whitespace only' }
  ];

  for (const testCase of testCases) {
    const result = parseColCLeagueDetails_(testCase.input);

    // Should return default values for empty input
    if (result.closingPartyDate !== null) {
      return `FAIL for ${testCase.description}: Expected closingPartyDate to be null, got ${result.closingPartyDate}`;
    }

    if (!Array.isArray(result.offDates) || result.offDates.length !== 0) {
      return `FAIL for ${testCase.description}: Expected offDates to be empty array, got ${result.offDates}`;
    }

    if (result.tournamentDate !== null) {
      return `FAIL for ${testCase.description}: Expected tournamentDate to be null, got ${result.tournamentDate}`;
    }

    if (result.totalInventory !== null) {
      return `FAIL for ${testCase.description}: Expected totalInventory to be null, got ${result.totalInventory}`;
    }
  }

  return true;
}

/**
 * Test partial data parsing
 * @returns {boolean|string} True if all tests pass, or an error message.
 */
function testPartialData_() {
  // Test with only some fields present
  const partialData = `Closing Party: Dec 15
# of Players: 32

Skipping 12/25`;

  const result = parseColCLeagueDetails_(partialData);

  // Should parse what's available
  const expectedClosingDate = new Date('2025-12-16T04:00:00Z'); // Dec 15 -> Dec 16 4AM UTC
  if (!result.closingPartyDate || result.closingPartyDate.toISOString() !== expectedClosingDate.toISOString()) {
    return `FAIL: Expected closingPartyDate to be ${expectedClosingDate.toISOString()}, got ${result.closingPartyDate?.toISOString()}`;
  }

  if (result.totalInventory !== 32) {
    return `FAIL: Expected totalInventory to be 32, got ${result.totalInventory}`;
  }

  // Should have one off date for 12/25
  if (!Array.isArray(result.offDates) || result.offDates.length !== 1) {
    return `FAIL: Expected offDates to have 1 element, got ${result.offDates?.length}`;
  }

  const expectedOffDate = new Date('2025-12-26T04:00:00Z'); // Dec 25 -> Dec 26 4AM UTC
  if (result.offDates[0].toISOString() !== expectedOffDate.toISOString()) {
    return `FAIL: Expected offDates[0] to be ${expectedOffDate.toISOString()}, got ${result.offDates[0].toISOString()}`;
  }

  // Tournament date should be null since it wasn't provided
  if (result.tournamentDate !== null) {
    return `FAIL: Expected tournamentDate to be null, got ${result.tournamentDate}`;
  }

  return true;
}
