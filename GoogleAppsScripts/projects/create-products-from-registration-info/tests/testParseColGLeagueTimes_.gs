/**
 * Tests for parseColGLeagueTimes_
 */
/// <reference path="../src/parsers/parseColGLeagueTimes_.gs" />

function test_times_double_range_row5_() {
  const s = 'Times: 12:45-2:45PM & 3:00-5:00PM';
  const r = parseColGLeagueTimes_(s);
  if (r.leagueStartTime !== '12:45 PM') throw new Error('start should be 12:45 PM');
  if (r.leagueEndTime !== '2:45 PM') throw new Error('end should be 2:45 PM');
  if (r.alternativeStartTime !== '3:00 PM') throw new Error('alt start should be 3:00 PM');
  if (r.alternativeEndTime !== '5:00 PM') throw new Error('alt end should be 5:00 PM');
}

/**
 * Tests for parseColGLeagueTimes_ function
 *
 * @fileoverview Test suite for league time parsing functionality
 * @requires ../src/config/constants.gs
 * @requires ../src/helpers/normalizers.gs
 * @requires ../src/parsers/parseColGLeagueTimes_.gs
 */

// Import references for editor support
/// <reference path="../src/config/constants.gs" />
/// <reference path="../src/helpers/normalizers.gs" />
/// <reference path="../src/parsers/parseColGLeagueTimes_.gs" />

/**
 * Main test function for parseColGLeagueTimes_
 * Tests various time input formats
 */
function testParseColGLeagueTimes_() {
  console.log('🧪 Running parseColGLeagueTimes_ comprehensive tests...');

  let passedTests = 0;
  let totalTests = 0;
  const failedTests = [];

  // Test 1: Single time range inputs
  totalTests++;
  const singleTimeResult = testSingleTimeRanges_();
  if (singleTimeResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 1 FAILED: Single time ranges - ${singleTimeResult}`);
  }

  // Test 2: Double time range inputs
  totalTests++;
  const doubleTimeResult = testDoubleTimeRanges_();
  if (doubleTimeResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 2 FAILED: Double time ranges - ${doubleTimeResult}`);
  }

  // Test 3: Invalid/unparseable inputs
  totalTests++;
  const invalidTimeResult = testInvalidTimeInputs_();
  if (invalidTimeResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 3 FAILED: Invalid time inputs - ${invalidTimeResult}`);
  }

  // Display results
  console.log(`\n📊 parseColGLeagueTimes_ Test Summary:`);
  console.log(`   Tests Run: ${totalTests}`);
  console.log(`   Tests Passed: ${passedTests}`);
  console.log(`   Tests Failed: ${failedTests.length}`);

  if (failedTests.length === 0) {
    console.log('✅ All parseColGLeagueTimes_ tests passed!');
  } else {
    console.log('❌ Some parseColGLeagueTimes_ tests failed!');
    for (const error of failedTests) {
      console.error(error);
    }
  }

  if (failedTests.length > 0) {
    throw new Error('❌ Some parseColGLeagueTimes tests failed!');
  }

  return passedTests === totalTests;
}

/**
 * Test single time range inputs
 * @returns {boolean|string} true if passed, error message if failed
 */
function testSingleTimeRanges_() {
  try {
    const testCases = [
      {
        input: "4-7:30PM",
        expectedLeagueStart: "4:00 PM",
        expectedLeagueEnd: "7:30 PM",
        description: "4-7:30PM"
      },
      {
        input: "12-3PM",
        expectedLeagueStart: "12:00 PM",
        expectedLeagueEnd: "3:00 PM",
        description: "12-3PM"
      },
      {
        input: "8-11pm",
        expectedLeagueStart: "8:00 PM",
        expectedLeagueEnd: "11:00 PM",
        description: "8-11pm"
      },
      {
        input: "6:30-10",
        expectedLeagueStart: "6:30 PM",
        expectedLeagueEnd: "10:00 PM",
        description: "6:30-10"
      },
      {
        input: "7-8:30pm",
        expectedLeagueStart: "7:00 PM",
        expectedLeagueEnd: "8:30 PM",
        description: "7-8:30pm"
      },
      {
        input: "Time: 8-10PM",
        expectedLeagueStart: "8:00 PM",
        expectedLeagueEnd: "10:00 PM",
        description: "Time: 8-10PM"
      },
      {
        input: "Time: 11-2PM",
        expectedLeagueStart: "11:00 AM",
        expectedLeagueEnd: "2:00 PM",
        description: "Time: 11-2PM"
      }
    ];

    for (const testCase of testCases) {
        const { leagueStartTime, leagueEndTime, alternativeStartTime, alternativeEndTime } =
        parseColGLeagueTimes_(testCase.input);

      if (leagueStartTime !== testCase.expectedLeagueStart) {
        return `League start time mismatch for ${testCase.description}: expected "${testCase.expectedLeagueStart}", got "${leagueStartTime}"`;
      }

      if (leagueEndTime !== testCase.expectedLeagueEnd) {
        return `League end time mismatch for ${testCase.description}: expected "${testCase.expectedLeagueEnd}", got "${leagueEndTime}"`;
      }

      // For single time ranges, alternative times should be null
      if (alternativeStartTime !== null) {
        return `Alternative start time should be null for ${testCase.description}: got "${alternativeStartTime}"`;
      }

      if (alternativeEndTime !== null) {
        return `Alternative end time should be null for ${testCase.description}: got "${alternativeEndTime}"`;
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testSingleTimeRanges_: ${error.toString()}`;
  }
}

/**
 * Test double time range inputs
 * @returns {boolean|string} true if passed, error message if failed
 */
function testDoubleTimeRanges_() {
  try {
    const testCases = [
      {
        input: "Times: 12:45-2:45PM & 3:00-5:00PM",
        expectedLeagueStart: "12:45 PM",
        expectedLeagueEnd: "2:45 PM",
        expectedAltStart: "3:00 PM",
        expectedAltEnd: "5:00 PM",
        description: "Times: 12:45-2:45PM & 3:00-5:00PM"
      }
    ];

    for (const testCase of testCases) {
      const { leagueStartTime, leagueEndTime, alternativeStartTime, alternativeEndTime } =
        parseColGLeagueTimes_(testCase.input);

      if (leagueStartTime !== testCase.expectedLeagueStart) {
        return `League start time mismatch for ${testCase.description}: expected "${testCase.expectedLeagueStart}", got "${leagueStartTime}"`;
      }

      if (leagueEndTime !== testCase.expectedLeagueEnd) {
        return `League end time mismatch for ${testCase.description}: expected "${testCase.expectedLeagueEnd}", got "${leagueEndTime}"`;
      }

      if (alternativeStartTime !== testCase.expectedAltStart) {
        return `Alternative start time mismatch for ${testCase.description}: expected "${testCase.expectedAltStart}", got "${alternativeStartTime}"`;
      }

      if (alternativeEndTime !== testCase.expectedAltEnd) {
        return `Alternative end time mismatch for ${testCase.description}: expected "${testCase.expectedAltEnd}", got "${alternativeEndTime}"`;
      }

    }

    return true;
  } catch (error) {
    return `ERROR in testDoubleTimeRanges_: ${error.toString()}`;
  }
}

/**
 * Test invalid/unparseable time inputs
 * @returns {boolean|string} true if passed, error message if failed
 */
function testInvalidTimeInputs_() {
  try {
    const testCases = [
      { input: "no times here", description: "No time information" },
      { input: "just some text", description: "Plain text" },
      { input: "123", description: "Just numbers" },
      { input: "meeting at 5", description: "No time range" },
      { input: "", description: "Empty string" },
      { input: null, description: "Null input" },
      { input: undefined, description: "Undefined input" }
    ];

    for (const testCase of testCases) {
      const { leagueStartTime, leagueEndTime, alternativeStartTime, alternativeEndTime } =
        parseColGLeagueTimes_(testCase.input);

      if (leagueStartTime !== null) {
        return `League start time should be null for ${testCase.description}: got "${leagueStartTime}"`;
      }

      if (leagueEndTime !== null) {
        return `League end time should be null for ${testCase.description}: got "${leagueEndTime}"`;
      }

      if (alternativeStartTime !== null) {
        return `Alternative start time should be null for ${testCase.description}: got "${alternativeStartTime}"`;
      }

      if (alternativeEndTime !== null) {
        return `Alternative end time should be null for ${testCase.description}: got "${alternativeEndTime}"`;
      }

    }

    return true;
  } catch (error) {
    return `ERROR in testInvalidTimeInputs_: ${error.toString()}`;
  }
}
