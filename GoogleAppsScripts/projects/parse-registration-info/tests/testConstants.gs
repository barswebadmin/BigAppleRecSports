/**
 * Unit tests for constants.gs
 * Tests comprehensive field lists, sport-specific irrelevant fields, and enum values
 */

/**
 * Main test runner for constants validation
 */
function testConstants() {
  Logger.log('🧪 Starting constants validation tests...');

  let passedTests = 0;
  let totalTests = 0;

  // Test 1: comprehensiveProductCreateFields exists and has all expected fields
  totalTests++;
  if (testComprehensiveProductCreateFields()) {
    passedTests++;
    Logger.log('✅ Test 1 PASSED: comprehensiveProductCreateFields validation');
  } else {
    Logger.log('❌ Test 1 FAILED: comprehensiveProductCreateFields validation');
  }

  // Test 2: irrelevantFieldsForSport exists and has all sports
  totalTests++;
  if (testIrrelevantFieldsForSport()) {
    passedTests++;
    Logger.log('✅ Test 2 PASSED: irrelevantFieldsForSport validation');
  } else {
    Logger.log('❌ Test 2 FAILED: irrelevantFieldsForSport validation');
  }

  // Test 3: productFieldEnums exists and has all enum fields
  totalTests++;
  if (testProductFieldEnums()) {
    passedTests++;
    Logger.log('✅ Test 3 PASSED: productFieldEnums validation');
  } else {
    Logger.log('❌ Test 3 FAILED: productFieldEnums validation');
  }

  // Test 4: Cross-validation between constants
  totalTests++;
  if (testConstantsCrossValidation()) {
    passedTests++;
    Logger.log('✅ Test 4 PASSED: Constants cross-validation');
  } else {
    Logger.log('❌ Test 4 FAILED: Constants cross-validation');
  }

  Logger.log(`\n📊 Constants Test Results: ${passedTests}/${totalTests} tests passed`);
  if (passedTests === totalTests) {
    Logger.log('✅ All constants tests passed!');
    return true;
  } else {
    Logger.log('❌ Some constants tests failed!');
    return false;
  }
}

/**
 * Test 1: Validate comprehensiveProductCreateFields
 */
function testComprehensiveProductCreateFields() {
  try {
    // Check that the constant exists
    if (typeof comprehensiveProductCreateFields === 'undefined') {
      Logger.log('comprehensiveProductCreateFields is not defined');
      return false;
    }

    // Check that it's an array
    if (!Array.isArray(comprehensiveProductCreateFields)) {
      Logger.log('comprehensiveProductCreateFields is not an array');
      return false;
    }

    // Expected fields based on expected_product_json_payload.js
    const expectedFields = [
      'sportName',
      'division',
      'season',
      'year',
      'dayOfPlay',
      'location',
      'sportSubCategory',
      'socialOrAdvanced',
      'types',
      'newPlayerOrientationDateTime',
      'scoutNightDateTime',
      'openingPartyDate',
      'seasonStartDate',
      'seasonEndDate',
      'offDates',
      'rainDate',
      'closingPartyDate',
      'vetRegistrationStartDateTime',
      'earlyRegistrationStartDateTime',
      'openRegistrationStartDateTime',
      'leagueStartTime',
      'leagueEndTime',
      'alternativeStartTime',
      'alternativeEndTime',
      'price',
      'totalInventory',
      'numberVetSpotsToReleaseAtGoLive'
    ];

    // Check that all expected fields are present
    for (const field of expectedFields) {
      if (!comprehensiveProductCreateFields.includes(field)) {
        Logger.log(`Missing field in comprehensiveProductCreateFields: ${field}`);
        return false;
      }
    }

    // Check that no unexpected fields are present
    for (const field of comprehensiveProductCreateFields) {
      if (!expectedFields.includes(field)) {
        Logger.log(`Unexpected field in comprehensiveProductCreateFields: ${field}`);
        return false;
      }
    }

    // Check minimum number of fields
    if (comprehensiveProductCreateFields.length < 25) {
      Logger.log(`comprehensiveProductCreateFields has too few fields: ${comprehensiveProductCreateFields.length}`);
      return false;
    }

    return true;
  } catch (error) {
    Logger.log(`Test 1 error: ${error.message}`);
    return false;
  }
}

/**
 * Test 2: Validate irrelevantFieldsForSport
 */
function testIrrelevantFieldsForSport() {
  try {
    // Check that the constant exists
    if (typeof irrelevantFieldsForSport === 'undefined') {
      Logger.log('irrelevantFieldsForSport is not defined');
      return false;
    }

    // Check that it's an object
    if (typeof irrelevantFieldsForSport !== 'object' || irrelevantFieldsForSport === null) {
      Logger.log('irrelevantFieldsForSport is not an object');
      return false;
    }

    // Expected sports
    const expectedSports = ['Dodgeball', 'Kickball', 'Bowling', 'Pickleball'];

    // Check that all expected sports are present
    for (const sport of expectedSports) {
      if (!(sport in irrelevantFieldsForSport)) {
        Logger.log(`Missing sport in irrelevantFieldsForSport: ${sport}`);
        return false;
      }

      // Check that each sport has an array of fields
      if (!Array.isArray(irrelevantFieldsForSport[sport])) {
        Logger.log(`irrelevantFieldsForSport[${sport}] is not an array`);
        return false;
      }
    }

    // Check that no unexpected sports are present
    for (const sport in irrelevantFieldsForSport) {
      if (!expectedSports.includes(sport)) {
        Logger.log(`Unexpected sport in irrelevantFieldsForSport: ${sport}`);
        return false;
      }
    }

    // Validate specific sport requirements
    const sportValidations = {
      'Kickball': ['sportSubCategory', 'alternativeStartTime', 'alternativeEndTime', 'openingPartyDate'],
      'Dodgeball': ['scoutNightDateTime', 'rainDate', 'alternativeStartTime', 'alternativeEndTime', 'openingPartyDate'],
      'Bowling': ['sportSubCategory', 'socialOrAdvanced', 'newPlayerOrientationDateTime', 'scoutNightDateTime', 'openingPartyDate', 'rainDate'],
      'Pickleball': ['sportSubCategory', 'newPlayerOrientationDateTime', 'scoutNightDateTime', 'rainDate', 'alternativeStartTime', 'alternativeEndTime', 'openingPartyDate']
    };

    for (const [sport, requiredFields] of Object.entries(sportValidations)) {
      for (const field of requiredFields) {
        if (!irrelevantFieldsForSport[sport].includes(field)) {
          Logger.log(`Missing irrelevant field for ${sport}: ${field}`);
          return false;
        }
      }
    }

    return true;
  } catch (error) {
    Logger.log(`Test 2 error: ${error.message}`);
    return false;
  }
}

/**
 * Test 3: Validate productFieldEnums
 */
function testProductFieldEnums() {
  try {
    // Check that the constant exists
    if (typeof productFieldEnums === 'undefined') {
      Logger.log('productFieldEnums is not defined');
      return false;
    }

    // Check that it's an object
    if (typeof productFieldEnums !== 'object' || productFieldEnums === null) {
      Logger.log('productFieldEnums is not an object');
      return false;
    }

    // Expected enum fields
    const expectedEnumFields = [
      'sportName',
      'division',
      'season',
      'dayOfPlay',
      'location',
      'sportSubCategory',
      'socialOrAdvanced',
      'types'
    ];

    // Check that all expected enum fields are present
    for (const field of expectedEnumFields) {
      if (!(field in productFieldEnums)) {
        Logger.log(`Missing enum field in productFieldEnums: ${field}`);
        return false;
      }
    }

    // Validate specific enum values
    const enumValidations = {
      'sportName': ['Dodgeball', 'Kickball', 'Bowling', 'Pickleball'],
      'division': ['WTNB+', 'Open'],
      'season': ['Fall', 'Winter', 'Summer', 'Spring'],
      'dayOfPlay': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
      'sportSubCategory': ['Big Ball', 'Small Ball', 'Foam'],
      'socialOrAdvanced': ['Social', 'Advanced', 'Mixed Social/Advanced', 'Competitive/Advanced', 'Intermediate/Advanced'],
      'types': ['Draft', 'Randomized Teams', 'Buddy Sign-up', 'Sign up with a newbie (randomized otherwise)']
    };

    for (const [field, expectedValues] of Object.entries(enumValidations)) {
      if (!Array.isArray(productFieldEnums[field])) {
        Logger.log(`productFieldEnums[${field}] is not an array`);
        return false;
      }

      for (const value of expectedValues) {
        if (!productFieldEnums[field].includes(value)) {
          Logger.log(`Missing enum value for ${field}: ${value}`);
          return false;
        }
      }
    }

    // Validate location enum structure (sport-specific)
    if (typeof productFieldEnums.location !== 'object' || productFieldEnums.location === null) {
      Logger.log('productFieldEnums.location is not an object');
      return false;
    }

    const expectedSports = ['Dodgeball', 'Kickball', 'Bowling', 'Pickleball'];
    for (const sport of expectedSports) {
      if (!(sport in productFieldEnums.location)) {
        Logger.log(`Missing sport in productFieldEnums.location: ${sport}`);
        return false;
      }

      if (!Array.isArray(productFieldEnums.location[sport])) {
        Logger.log(`productFieldEnums.location[${sport}] is not an array`);
        return false;
      }

      if (productFieldEnums.location[sport].length === 0) {
        Logger.log(`productFieldEnums.location[${sport}] is empty`);
        return false;
      }
    }

    // Validate specific location requirements
    const locationValidations = {
      'Pickleball': ['Gotham Pickleball (46th and Vernon in LIC)', 'Pickle1 (7 Hanover Square in LIC)'],
      'Bowling': ['Frames Bowling Lounge (40th St and 9th Ave)', 'Bowlero Chelsea Piers (60 Chelsea Piers)']
    };

    for (const [sport, requiredLocations] of Object.entries(locationValidations)) {
      for (const location of requiredLocations) {
        if (!productFieldEnums.location[sport].includes(location)) {
          Logger.log(`Missing location for ${sport}: ${location}`);
          return false;
        }
      }
    }

    return true;
  } catch (error) {
    Logger.log(`Test 3 error: ${error.message}`);
    return false;
  }
}

/**
 * Test 4: Cross-validation between constants
 */
function testConstantsCrossValidation() {
  try {
    // Check that all irrelevant fields are in comprehensive fields
    for (const sport in irrelevantFieldsForSport) {
      for (const field of irrelevantFieldsForSport[sport]) {
        if (!comprehensiveProductCreateFields.includes(field)) {
          Logger.log(`Irrelevant field ${field} for ${sport} not found in comprehensiveProductCreateFields`);
          return false;
        }
      }
    }

    // Check that enum sport names match irrelevant fields sport keys
    const enumSports = productFieldEnums.sportName;
    const irrelevantSports = Object.keys(irrelevantFieldsForSport);

    for (const sport of enumSports) {
      if (!irrelevantSports.includes(sport)) {
        Logger.log(`Sport ${sport} in productFieldEnums.sportName not found in irrelevantFieldsForSport`);
        return false;
      }
    }

    for (const sport of irrelevantSports) {
      if (!enumSports.includes(sport)) {
        Logger.log(`Sport ${sport} in irrelevantFieldsForSport not found in productFieldEnums.sportName`);
        return false;
      }
    }

    // Check that location sports match other sport definitions
    const locationSports = Object.keys(productFieldEnums.location);

    for (const sport of enumSports) {
      if (!locationSports.includes(sport)) {
        Logger.log(`Sport ${sport} in productFieldEnums.sportName not found in productFieldEnums.location`);
        return false;
      }
    }

    return true;
  } catch (error) {
    Logger.log(`Test 4 error: ${error.message}`);
    return false;
  }
}
