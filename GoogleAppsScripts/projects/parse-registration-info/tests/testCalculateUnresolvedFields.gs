/**
 * Tests for calculateUnresolvedFieldsForParsedData function
 *
 * @fileoverview Test suite for unresolved field calculation
 * @requires ../src/validators/fieldValidation.gs
 * @requires ../src/config/constants.gs
 */

// Import references for editor support
/// <reference path="../src/validators/fieldValidation.gs" />
/// <reference path="../src/config/constants.gs" />

/**
 * Main test function for calculateUnresolvedFieldsForParsedData
 */
function testCalculateUnresolvedFields_() {
  console.log('🧪 Running calculateUnresolvedFieldsForParsedData tests...');

  let passedTests = 0;
  let totalTests = 0;
  const failedTests = [];

  // Test 1: Complete parsed data should have minimal unresolved fields
  totalTests++;
  const completeDataResult = testCompleteData_();
  if (completeDataResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 1 FAILED: Complete data - ${completeDataResult}`);
  }

  // Test 2: Partial data should return appropriate unresolved fields
  totalTests++;
  const partialDataResult = testPartialData_();
  if (partialDataResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 2 FAILED: Partial data - ${partialDataResult}`);
  }

  // Test 3: Sport-specific irrelevant fields should be excluded
  totalTests++;
  const sportSpecificResult = testSportSpecificFiltering_();
  if (sportSpecificResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 3 FAILED: Sport-specific filtering - ${sportSpecificResult}`);
  }

  // Test 4: Invalid input handling
  totalTests++;
  const invalidInputResult = testInvalidInput_();
  if (invalidInputResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 4 FAILED: Invalid input - ${invalidInputResult}`);
  }

  // Test 5: Nested field detection
  totalTests++;
  const nestedFieldResult = testNestedFieldDetection_();
  if (nestedFieldResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 5 FAILED: Nested field detection - ${nestedFieldResult}`);
  }

  // Display results
  console.log(`\n📊 calculateUnresolvedFields Test Summary:`);
  console.log(`   Tests Run: ${totalTests}`);
  console.log(`   Tests Passed: ${passedTests}`);
  console.log(`   Tests Failed: ${failedTests.length}`);

  if (failedTests.length > 0) {
    for (const failure of failedTests) {
      console.log(failure);
    }
    throw new Error('❌ Some calculateUnresolvedFields tests failed!');
  }
}

/**
 * Test with complete parsed data
 * @returns {boolean|string} True if test passes, error message if failed
 */
function testCompleteData_() {
  const completeData = {
    sportName: 'Kickball',
    division: 'Open',
    season: 'Fall',
    year: 2025,
    dayOfPlay: 'Wednesday',
    location: 'DeWitt Clinton Park',
    optionalLeagueInfo: {
      socialOrAdvanced: 'Social',
      types: 'Buddy Sign-up'
    },
    importantDates: {
      newPlayerOrientationDateTime: new Date('2025-10-01T19:00:00Z'),
      scoutNightDateTime: new Date('2025-10-08T19:00:00Z'),
      openingPartyDate: new Date('2025-10-15T19:00:00Z'),
      seasonStartDate: new Date('2025-10-15T04:00:00Z'),
      seasonEndDate: new Date('2025-12-10T04:00:00Z'),
      offDates: [new Date('2025-11-26T04:00:00Z')],
      rainDate: new Date('2025-12-17T04:00:00Z'),
      closingPartyDate: new Date('2025-12-15T19:00:00Z'),
      vetRegistrationStartDateTime: new Date('2025-09-15T19:00:00Z'),
      earlyRegistrationStartDateTime: new Date('2025-09-10T19:00:00Z'),
      openRegistrationStartDateTime: new Date('2025-09-20T19:00:00Z')
    },
    leagueStartTime: '7:00 PM',
    leagueEndTime: '10:00 PM',
    inventoryInfo: {
      price: 150,
      totalInventory: 64,
      numberVetSpotsToReleaseAtGoLive: 40
    }
  };

  const unresolved = calculateUnresolvedFieldsForParsedData(completeData);

  // For Kickball, should exclude sportSubCategory, alternativeStartTime, alternativeEndTime
  // All other fields should be resolved
  if (unresolved.length > 0) {
    return `Expected no unresolved fields for complete Kickball data, got: ${unresolved.join(', ')}`;
  }

  return true;
}

/**
 * Test with partial data
 * @returns {boolean|string} True if test passes, error message if failed
 */
function testPartialData_() {
  const partialData = {
    sportName: 'Dodgeball',
    division: 'Open',
    season: 'Fall',
    year: 2025,
    dayOfPlay: 'Thursday',
    // Missing location
    optionalLeagueInfo: {
      sportSubCategory: 'Small Ball',
      socialOrAdvanced: 'Advanced'
      // Missing types
    },
    importantDates: {
      seasonStartDate: new Date('2025-10-15T04:00:00Z'),
      seasonEndDate: new Date('2025-12-10T04:00:00Z')
      // Missing many dates
    },
    leagueStartTime: '7:30 PM',
    leagueEndTime: '10:30 PM',
    inventoryInfo: {
      price: 175
      // Missing totalInventory and numberVetSpotsToReleaseAtGoLive
    }
  };

  const unresolved = calculateUnresolvedFieldsForParsedData(partialData);

  // Should find multiple missing fields but exclude irrelevant ones for Dodgeball
  const expectedUnresolvedFields = [
    'location',
    'types',
    'newPlayerOrientationDateTime',
    'openingPartyDate',
    'offDates',
    'closingPartyDate',
    'vetRegistrationStartDateTime',
    'earlyRegistrationStartDateTime',
    'openRegistrationStartDateTime',
    'totalInventory',
    'numberVetSpotsToReleaseAtGoLive'
  ];

  // Should NOT include irrelevant fields for Dodgeball: scoutNightDateTime, rainDate, alternativeStartTime, alternativeEndTime
  const irrelevantForDodgeball = ['scoutNightDateTime', 'rainDate', 'alternativeStartTime', 'alternativeEndTime'];

  for (const irrelevantField of irrelevantForDodgeball) {
    if (unresolved.includes(irrelevantField)) {
      return `Found irrelevant field "${irrelevantField}" in unresolved list for Dodgeball`;
    }
  }

  // Check that we found expected unresolved fields
  for (const expectedField of expectedUnresolvedFields) {
    if (!unresolved.includes(expectedField)) {
      return `Expected to find "${expectedField}" in unresolved list, but it was missing`;
    }
  }

  return true;
}

/**
 * Test sport-specific filtering
 * @returns {boolean|string} True if test passes, error message if failed
 */
function testSportSpecificFiltering_() {
  const bowlingData = {
    sportName: 'Bowling',
    division: 'Open',
    season: 'Winter',
    year: 2025,
    dayOfPlay: 'Friday',
    location: 'Frames Bowling Lounge',
    // Missing most optional fields
    importantDates: {
      seasonStartDate: new Date('2025-01-15T04:00:00Z'),
      seasonEndDate: new Date('2025-03-15T04:00:00Z')
    },
    leagueStartTime: '7:00 PM',
    leagueEndTime: '9:00 PM',
    inventoryInfo: {
      price: 200,
      totalInventory: 48,
      numberVetSpotsToReleaseAtGoLive: 24
    }
  };

  const unresolved = calculateUnresolvedFieldsForParsedData(bowlingData);

  // Should NOT include irrelevant fields for Bowling
  const irrelevantForBowling = [
    'sportSubCategory',
    'socialOrAdvanced',
    'newPlayerOrientationDateTime',
    'scoutNightDateTime',
    'openingPartyDate',
    'rainDate'
  ];

  for (const irrelevantField of irrelevantForBowling) {
    if (unresolved.includes(irrelevantField)) {
      return `Found irrelevant field "${irrelevantField}" in unresolved list for Bowling`;
    }
  }

  // Should include relevant missing fields
  const expectedUnresolvedFields = ['types', 'offDates', 'closingPartyDate'];
  for (const expectedField of expectedUnresolvedFields) {
    if (!unresolved.includes(expectedField)) {
      return `Expected to find "${expectedField}" in unresolved list for Bowling`;
    }
  }

  return true;
}

/**
 * Test invalid input handling
 * @returns {boolean|string} True if test passes, error message if failed
 */
function testInvalidInput_() {
  // Test null input
  const nullResult = calculateUnresolvedFieldsForParsedData(null);
  if (nullResult.length !== comprehensiveProductCreateFields.length) {
    return `Expected all fields unresolved for null input, got ${nullResult.length} fields`;
  }

  // Test empty object
  const emptyResult = calculateUnresolvedFieldsForParsedData({});
  if (emptyResult.length !== comprehensiveProductCreateFields.length) {
    return `Expected all fields unresolved for empty object, got ${emptyResult.length} fields`;
  }

  // Test object without sportName
  const noSportResult = calculateUnresolvedFieldsForParsedData({division: 'Open'});
  if (noSportResult.length !== comprehensiveProductCreateFields.length) {
    return `Expected all fields unresolved for object without sportName, got ${noSportResult.length} fields`;
  }

  return true;
}

/**
 * Test nested field detection
 * @returns {boolean|string} True if test passes, error message if failed
 */
function testNestedFieldDetection_() {
  const testData = {
    sportName: 'Pickleball',
    division: 'Open',
    season: 'Spring',
    year: 2025,
    dayOfPlay: 'Saturday',
    location: 'Chelsea Park',
    optionalLeagueInfo: {
      socialOrAdvanced: 'Mixed Social/Advanced',
      types: 'Random Team Assignment'
    },
    importantDates: {
      seasonStartDate: new Date('2025-04-15T04:00:00Z'),
      seasonEndDate: new Date('2025-06-15T04:00:00Z'),
      offDates: []
    },
    leagueStartTime: '10:00 AM',
    leagueEndTime: '12:00 PM',
    inventoryInfo: {
      price: 125,
      totalInventory: 32,
      numberVetSpotsToReleaseAtGoLive: 16
    }
  };

  const unresolved = calculateUnresolvedFieldsForParsedData(testData);

  // Should properly detect nested fields as resolved
  const nestedFieldsToCheck = ['socialOrAdvanced', 'types', 'seasonStartDate', 'price'];
  for (const field of nestedFieldsToCheck) {
    if (unresolved.includes(field)) {
      return `Nested field "${field}" was incorrectly marked as unresolved`;
    }
  }

  // Should detect that offDates is empty array (unresolved)
  if (!unresolved.includes('offDates')) {
    return `Empty array field "offDates" should be marked as unresolved`;
  }

  return true;
}
