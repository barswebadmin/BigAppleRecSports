/**
 * Tests for parseColBLeagueBasicInfo_
 */
/// <reference path="../src/parsers/parseColBLeagueBasicInfo_.gs" />

function test_b_col_types_randomized_() {
  const b = 'SATURDAY\nOpen\nRandomized';
  const r = parseColBLeagueBasicInfo_(b, 'Kickball');
  if (r.types.join(',').indexOf('Randomized') === -1) throw new Error('types should include Randomized');
}

function test_b_col_division_enforced_() {
  const b = 'SATURDAY\nAdvanced\nRandomized';
  const r = parseColBLeagueBasicInfo_(b, 'Kickball');
  if (r.division !== '') throw new Error('division must only be Open or WTNB+');
}

/**
 * Focused tests for parseColBLeagueBasicInfo_ function
 * Tests each of the 5 fields individually for correct parsing and unresolved tracking
 *
 * @fileoverview Field-by-field test suite for parseColBLeagueBasicInfo_
 */

// Import references for editor support
/// <reference path="../src/config/constants.gs" />
/// <reference path="../src/helpers/normalizers.gs" />
/// <reference path="../src/parsers/parseColBLeagueBasicInfo_.gs" />

/**
 * Main test function for parseColBLeagueBasicInfo_
 * Tests each field individually
 */
function testparseColBLeagueBasicInfo_() {
  console.log('🧪 Running parseColBLeagueBasicInfo_ field-by-field tests...');
  console.log('TODO: add tests for other sports');

  let passedTests = 0;
  let totalTests = 0;
  const failedTests = [];

  // Test 1: dayOfPlay field parsing
  totalTests++;
  const dayOfPlayResult = testDayOfPlayField_();
  if (dayOfPlayResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 1 FAILED: dayOfPlay field parsing - ${dayOfPlayResult}`);
  }

  // Test 2: division field parsing
  totalTests++;
  const divisionResult = testDivisionField_();
  if (divisionResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 2 FAILED: division field parsing - ${divisionResult}`);
  }

  // Test 3: sportSubCategory field parsing
  totalTests++;
  const sportSubCategoryResult = testSportSubCategoryField_();
  if (sportSubCategoryResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 3 FAILED: sportSubCategory field parsing - ${sportSubCategoryResult}`);
  }

  // Test 4: socialOrAdvanced field parsing
  totalTests++;
  const socialOrAdvancedResult = testSocialOrAdvancedField_();
  if (socialOrAdvancedResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 4 FAILED: socialOrAdvanced field parsing - ${socialOrAdvancedResult}`);
  }

  // Test 5: types field parsing
  totalTests++;
  const typesResult = testTypesField_();
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
    for (const failure of failedTests) {
      console.log(`   - ${failure}`);
    }
  }

  if (passedTests === totalTests) {
    console.log('✅ All parseColBLeagueBasicInfo_ field tests passed!');
    return true;
  } else {
    console.log('❌ Some parseColBLeagueBasicInfo_ field tests failed!');
    return false;
  }
}

/**
 * Test #1: dayOfPlay field parsing
 * @returns {boolean|string} True if all tests pass, error message if any fail
 */
function testDayOfPlayField_() {
  try {
    const tests = [
      {
        description: 'dayOfPlay found and extracted correctly',
        bColumnData: 'Tuesday\nSome other text',
        sportName: 'Kickball',
        expectedDayOfPlay: 'Tuesday'
      },
      {
        description: 'dayOfPlay not found, remains in unresolved',
        bColumnData: '', // Completely empty
        sportName: 'Kickball',
        expectedDayOfPlay: ''
      }
    ];

    for (const test of tests) {

      const result = parseColBLeagueBasicInfo_(test.bColumnData, test.sportName);

      const dayOfPlayCorrect = result.dayOfPlay === test.expectedDayOfPlay;

      if (!dayOfPlayCorrect) {
        return `${test.description} - Expected: dayOfPlay='${test.expectedDayOfPlay}', Got: dayOfPlay='${result.dayOfPlay}'}`;
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testDayOfPlayField_: ${error.toString()}`;
  }
}

/**
 * Test #2: division field parsing
 * @returns {boolean|string} True if all tests pass, error message if any fail
 */
function testDivisionField_() {
  try {
    const tests = [
      {
        description: 'division "Open" found and extracted correctly',
        bColumnData: 'Tuesday\nOpen Division\nSome text',
        sportName: 'Kickball',
        expectedDivision: 'Open',
      },
      {
        description: 'division "WTNB+" found and extracted correctly',
        bColumnData: 'Tuesday\nWTNB Division\nSome text',
        sportName: 'Kickball',
        expectedDivision: 'WTNB+'
      },
      {
        description: 'division not found',
        bColumnData: 'Tuesday\nNo division keywords\nSome text',
        sportName: 'Kickball',
        expectedDivision: ''
      }
    ];

    for (const test of tests) {
      const result = parseColBLeagueBasicInfo_(test.bColumnData, test.sportName);

      const divisionCorrect = result.division === test.expectedDivision;

      if (!divisionCorrect) {
        return `${test.description} - Expected: division='${test.expectedDivision}', Got: division='${result.division}'}`;
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testDivisionField_: ${error.toString()}`;
  }
}

/**
 * Test #3: sportSubCategory field parsing
 * @returns {boolean|string} True if all tests pass, error message if any fail
 */
function testSportSubCategoryField_() {
  try {
    const tests = [
      {
        description: 'sportSubCategory "Small Ball" found for Dodgeball',
        bColumnData: 'Tuesday\nSmall Ball\nSome text',
        sportName: 'Dodgeball',
        expectedSportSubCategory: 'Small Ball'
      },
      {
        description: 'sportSubCategory "Big Ball" found for Dodgeball',
        bColumnData: 'Tuesday\n8.5 inch ball\nSome text',
        sportName: 'Dodgeball',
        expectedSportSubCategory: 'Big Ball'
      },
      {
        description: 'sportSubCategory not extracted for non-Dodgeball sport',
        bColumnData: 'Tuesday\nSmall Ball\nSome text',
        sportName: 'Kickball',
        expectedSportSubCategory: ''
      }
    ];

    for (const test of tests) {
      const result = parseColBLeagueBasicInfo_(test.bColumnData, test.sportName);

      const sportSubCategoryCorrect = result.sportSubCategory === test.expectedSportSubCategory;

      if (!sportSubCategoryCorrect ) {
        return `${test.description} - Expected: sportSubCategory='${test.expectedSportSubCategory}', Got: sportSubCategory='${result.sportSubCategory}'}`;
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testSportSubCategoryField_: ${error.toString()}`;
  }
}

/**
 * Test #4: socialOrAdvanced field parsing
 * @returns {boolean|string} True if all tests pass, error message if any fail
 */
function testSocialOrAdvancedField_() {
  try {
    const tests = [
      {
        description: 'socialOrAdvanced found and extracted correctly',
        bColumnData: 'Tuesday\nSocial League\nSome text',
        sportName: 'Kickball',
        expectedSocialOrAdvanced: 'Social League',

      },
      {
        description: 'socialOrAdvanced "Advanced" found and extracted correctly',
        bColumnData: 'Tuesday\nAdvanced Division\nSome text',
        sportName: 'Pickleball',
        expectedSocialOrAdvanced: 'Advanced Division',

      },
      {
        description: 'socialOrAdvanced not found, remains in unresolved',
        bColumnData: 'Tuesday\nNo keywords here\nSome text',
        sportName: 'Kickball',
        expectedSocialOrAdvanced: '',
      }
    ];

    for (const test of tests) {


      const result = parseColBLeagueBasicInfo_(test.bColumnData, test.sportName);

      const socialOrAdvancedCorrect = result.socialOrAdvanced === test.expectedSocialOrAdvanced;

      if (!socialOrAdvancedCorrect ) {
        return `${test.description} - Expected: socialOrAdvanced='${test.expectedSocialOrAdvanced}', Got: socialOrAdvanced='${result.socialOrAdvanced}'}`;
      }
    }

    return true;
  } catch (error) {
    return `ERROR in testSocialOrAdvancedField_: ${error.toString()}`;
  }
}

/**
 * Test #5: types field parsing
 * @returns {boolean|string} True if all tests pass, error message if any fail
 */
function testTypesField_() {
  try {
    const tests = [
      {
        description: 'types "Randomized Teams" found and extracted correctly',
        bColumnData: 'Tuesday\nRandomized Teams\nSome text',
        sportName: 'Kickball',
        expectedTypes: ['Randomized Teams']

      },
      {
        description: 'types "Draft" found and extracted correctly',
        bColumnData: 'Tuesday\nDraft League\nSome text',
        sportName: 'Kickball',
        expectedTypes: ['Draft']

      },
      {
        description: 'types combination found and extracted correctly',
        bColumnData: 'Tuesday\nRandomized Teams\nBuddy sign-up available\nSome text',
        sportName: 'Kickball',
        expectedTypes: ['Randomized Teams, Buddy Sign-up']

      },
      {
        description: 'types not found, remains in unresolved',
        bColumnData: 'Tuesday\nNo type keywords\nSome text',
        sportName: 'Kickball',
        expectedTypes: []

      }
    ];

    for (const test of tests) {


      const result = parseColBLeagueBasicInfo_(test.bColumnData, test.sportName);

      const typesCorrect = arraysEqual(result.types, test.expectedTypes);

      if (!typesCorrect ) {
        return `${test.description} - Expected: types=${JSON.stringify(test.expectedTypes)}, Got: types=${JSON.stringify(result.types)}`;
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
