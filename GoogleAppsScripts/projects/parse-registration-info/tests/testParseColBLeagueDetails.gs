/**
 * Focused tests for parseColBLeagueDetails_ function
 * Tests each of the 5 fields individually for correct parsing and unresolved tracking
 *
 * @fileoverview Field-by-field test suite for parseColBLeagueDetails_
 */

// Import references for editor support
/// <reference path="../src/config/constants.gs" />
/// <reference path="../src/helpers/normalizers.gs" />
/// <reference path="../src/parsers/parseColBLeagueDetails.gs" />

/**
 * Main test function for parseColBLeagueDetails_
 * Tests each field individually
 */
function testParseColBLeagueDetails_() {
  console.log('🧪 Running parseColBLeagueDetails_ field-by-field tests...');
  console.log('TODO: add tests for other sports');

  let passedTests = 0;
  let totalTests = 0;
  const failedTests = [];

  // Initialize unresolved fields for testing (using Kickball as default)
  const baseUnresolved = initializeUnresolvedFields('Kickball');

  // Test 1: dayOfPlay field parsing
  totalTests++;
  const dayOfPlayResult = testDayOfPlayField_(baseUnresolved);
  if (dayOfPlayResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 1 FAILED: dayOfPlay field parsing - ${dayOfPlayResult}`);
  }

  // Test 2: division field parsing
  totalTests++;
  const divisionResult = testDivisionField_(baseUnresolved);
  if (divisionResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 2 FAILED: division field parsing - ${divisionResult}`);
  }

  // Test 3: sportSubCategory field parsing
  totalTests++;
  const sportSubCategoryResult = testSportSubCategoryField_(baseUnresolved);
  if (sportSubCategoryResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 3 FAILED: sportSubCategory field parsing - ${sportSubCategoryResult}`);
  }

  // Test 4: socialOrAdvanced field parsing
  totalTests++;
  const socialOrAdvancedResult = testSocialOrAdvancedField_(baseUnresolved);
  if (socialOrAdvancedResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 4 FAILED: socialOrAdvanced field parsing - ${socialOrAdvancedResult}`);
  }

  // Test 5: types field parsing
  totalTests++;
  const typesResult = testTypesField_(baseUnresolved);
  if (typesResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 5 FAILED: types field parsing - ${typesResult}`);
  }

  // Summary
  console.log(`\n📊 Test Summary:`);
  console.log(`   Tests Run: ${totalTests}`);
  console.log(`   Tests Passed: ${passedTests}`);
  console.log(`   Tests Failed: ${totalTests - passedTests}`);

  if (failedTests.length > 0) {
    console.log(`\n❌ Failed Tests:`);
    failedTests.forEach(failure => console.log(`   - ${failure}`));
  }

  if (passedTests === totalTests) {
    console.log('✅ All parseColBLeagueDetails_ field tests passed!');
    return true;
  } else {
    console.log('❌ Some parseColBLeagueDetails_ field tests failed!');
    return false;
  }
}

/**
 * Test #1: dayOfPlay field parsing
 * @param {Array<string>} baseUnresolved - Base unresolved fields array
 * @returns {boolean|string} True if all tests pass, error message if any fail
 */
function testDayOfPlayField_(baseUnresolved) {
  try {
    const tests = [
      {
        description: 'dayOfPlay found and extracted correctly',
        bColumnData: 'Tuesday\nSome other text',
        sportName: 'Kickball',
        expectedDayOfPlay: 'Tuesday',
        expectedInUnresolved: false
      },
      {
        description: 'dayOfPlay not found, remains in unresolved',
        bColumnData: '', // Completely empty
        sportName: 'Kickball',
        expectedDayOfPlay: '',
        expectedInUnresolved: true
      }
    ];

    for (const test of tests) {
      // Create a copy of the base unresolved array for this test
      const unresolved = [...baseUnresolved];

      const result = parseColBLeagueDetails_(test.bColumnData, unresolved, test.sportName);

      const dayOfPlayCorrect = result.dayOfPlay === test.expectedDayOfPlay;
      const unresolvedCorrect = unresolved.includes('dayOfPlay') === test.expectedInUnresolved;

      if (!dayOfPlayCorrect || !unresolvedCorrect) {
        return `${test.description} - Expected: dayOfPlay='${test.expectedDayOfPlay}', inUnresolved=${test.expectedInUnresolved}, Got: dayOfPlay='${result.dayOfPlay}', inUnresolved=${unresolved.includes('dayOfPlay')}`;
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testDayOfPlayField_: ${error.toString()}`;
  }
}

/**
 * Test #2: division field parsing
 * @param {Array<string>} baseUnresolved - Base unresolved fields array
 * @returns {boolean|string} True if all tests pass, error message if any fail
 */
function testDivisionField_(baseUnresolved) {
  try {
    const tests = [
      {
        description: 'division "Open" found and extracted correctly',
        bColumnData: 'Tuesday\nOpen Division\nSome text',
        sportName: 'Kickball',
        expectedDivision: 'Open',
        expectedInUnresolved: false
      },
      {
        description: 'division "WTNB+" found and extracted correctly',
        bColumnData: 'Tuesday\nWTNB Division\nSome text',
        sportName: 'Kickball',
        expectedDivision: 'WTNB+',
        expectedInUnresolved: false
      },
      {
        description: 'division not found, remains in unresolved',
        bColumnData: 'Tuesday\nNo division keywords\nSome text',
        sportName: 'Kickball',
        expectedDivision: '',
        expectedInUnresolved: true
      }
    ];

    for (const test of tests) {
      // Create a copy of the base unresolved array for this test
      const unresolved = [...baseUnresolved];
      const result = parseColBLeagueDetails_(test.bColumnData, unresolved, test.sportName);

      const divisionCorrect = result.division === test.expectedDivision;
      const unresolvedCorrect = unresolved.includes('division') === test.expectedInUnresolved;

      if (!divisionCorrect || !unresolvedCorrect) {
        return `${test.description} - Expected: division='${test.expectedDivision}', inUnresolved=${test.expectedInUnresolved}, Got: division='${result.division}', inUnresolved=${unresolved.includes('division')}`;
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testDivisionField_: ${error.toString()}`;
  }
}

/**
 * Test #3: sportSubCategory field parsing
 * @param {Array<string>} baseUnresolved - Base unresolved fields array
 * @returns {boolean|string} True if all tests pass, error message if any fail
 */
function testSportSubCategoryField_(baseUnresolved) {
  try {
    const tests = [
      {
        description: 'sportSubCategory "Small Ball" found for Dodgeball',
        bColumnData: 'Tuesday\nSmall Ball\nSome text',
        sportName: 'Dodgeball',
        expectedSportSubCategory: 'Small Ball',
        expectedInUnresolved: false
      },
      {
        description: 'sportSubCategory "Big Ball" found for Dodgeball',
        bColumnData: 'Tuesday\n8.5 inch ball\nSome text',
        sportName: 'Dodgeball',
        expectedSportSubCategory: 'Big Ball',
        expectedInUnresolved: false
      },
      {
        description: 'sportSubCategory not extracted for non-Dodgeball sport',
        bColumnData: 'Tuesday\nSmall Ball\nSome text',
        sportName: 'Kickball',
        expectedSportSubCategory: '',
        expectedInUnresolved: true
      }
    ];

    for (const test of tests) {
      // Create a copy of the base unresolved array for this test
      const unresolved = [...baseUnresolved];
      const result = parseColBLeagueDetails_(test.bColumnData, unresolved, test.sportName);

      const sportSubCategoryCorrect = result.sportSubCategory === test.expectedSportSubCategory;
      const unresolvedCorrect = unresolved.includes('sportSubCategory') === test.expectedInUnresolved;

      if (!sportSubCategoryCorrect || !unresolvedCorrect) {
        return `${test.description} - Expected: sportSubCategory='${test.expectedSportSubCategory}', inUnresolved=${test.expectedInUnresolved}, Got: sportSubCategory='${result.sportSubCategory}', inUnresolved=${unresolved.includes('sportSubCategory')}`;
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testSportSubCategoryField_: ${error.toString()}`;
  }
}

/**
 * Test #4: socialOrAdvanced field parsing
 * @param {Array<string>} baseUnresolved - Base unresolved fields array
 * @returns {boolean|string} True if all tests pass, error message if any fail
 */
function testSocialOrAdvancedField_(baseUnresolved) {
  try {
    const tests = [
      {
        description: 'socialOrAdvanced found and extracted correctly',
        bColumnData: 'Tuesday\nSocial League\nSome text',
        sportName: 'Kickball',
        expectedSocialOrAdvanced: 'Social League',
        expectedInUnresolved: false
      },
      {
        description: 'socialOrAdvanced "Advanced" found and extracted correctly',
        bColumnData: 'Tuesday\nAdvanced Division\nSome text',
        sportName: 'Pickleball',
        expectedSocialOrAdvanced: 'Advanced Division',
        expectedInUnresolved: false
      },
      {
        description: 'socialOrAdvanced not found, remains in unresolved',
        bColumnData: 'Tuesday\nNo keywords here\nSome text',
        sportName: 'Kickball',
        expectedSocialOrAdvanced: '',
        expectedInUnresolved: true
      }
    ];

    for (const test of tests) {
      // Create a copy of the base unresolved array for this test
      const unresolved = [...baseUnresolved];
      const result = parseColBLeagueDetails_(test.bColumnData, unresolved, test.sportName);

      const socialOrAdvancedCorrect = result.socialOrAdvanced === test.expectedSocialOrAdvanced;
      const unresolvedCorrect = unresolved.includes('socialOrAdvanced') === test.expectedInUnresolved;

      if (!socialOrAdvancedCorrect || !unresolvedCorrect) {
        return `${test.description} - Expected: socialOrAdvanced='${test.expectedSocialOrAdvanced}', inUnresolved=${test.expectedInUnresolved}, Got: socialOrAdvanced='${result.socialOrAdvanced}', inUnresolved=${unresolved.includes('socialOrAdvanced')}`;
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testSocialOrAdvancedField_: ${error.toString()}`;
  }
}

/**
 * Test #5: types field parsing
 * @param {Array<string>} baseUnresolved - Base unresolved fields array
 * @returns {boolean|string} True if all tests pass, error message if any fail
 */
function testTypesField_(baseUnresolved) {
  try {
    const tests = [
      {
        description: 'types "Randomized Teams" found and extracted correctly',
        bColumnData: 'Tuesday\nRandomized Teams\nSome text',
        sportName: 'Kickball',
        expectedTypes: ['Randomized Teams'],
        expectedInUnresolved: false
      },
      {
        description: 'types "Draft" found and extracted correctly',
        bColumnData: 'Tuesday\nDraft League\nSome text',
        sportName: 'Kickball',
        expectedTypes: ['Draft'],
        expectedInUnresolved: false
      },
      {
        description: 'types combination found and extracted correctly',
        bColumnData: 'Tuesday\nRandomized Teams\nBuddy sign-up available\nSome text',
        sportName: 'Kickball',
        expectedTypes: ['Randomized Teams, Buddy Sign-up'],
        expectedInUnresolved: false
      },
      {
        description: 'types not found, remains in unresolved',
        bColumnData: 'Tuesday\nNo type keywords\nSome text',
        sportName: 'Kickball',
        expectedTypes: [],
        expectedInUnresolved: true
      }
    ];

    for (const test of tests) {
      // Create a copy of the base unresolved array for this test
      const unresolved = [...baseUnresolved];
      const result = parseColBLeagueDetails_(test.bColumnData, unresolved, test.sportName);

      const typesCorrect = arraysEqual(result.types, test.expectedTypes);
      const unresolvedCorrect = unresolved.includes('types') === test.expectedInUnresolved;

      if (!typesCorrect || !unresolvedCorrect) {
        return `${test.description} - Expected: types=${JSON.stringify(test.expectedTypes)}, inUnresolved=${test.expectedInUnresolved}, Got: types=${JSON.stringify(result.types)}, inUnresolved=${unresolved.includes('types')}`;
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testTypesField_: ${error.toString()}`;
  }
}

/**
 * Helper function to compare arrays for equality
 * @param {Array} arr1 - First array
 * @param {Array} arr2 - Second array
 * @returns {boolean} True if arrays are equal
 */
function arraysEqual(arr1, arr2) {
  if (!Array.isArray(arr1) || !Array.isArray(arr2)) return false;
  if (arr1.length !== arr2.length) return false;
  return arr1.every((val, i) => val === arr2[i]);
}
