/**
 * Test HTML template variable resolution
 * Ensures all template variables are properly set and no undefined/null fields cause template errors
 */

/// <reference path="../src/core/portedFromProductCreateSheet/createShopifyProduct.gs" />

function testHtmlTemplateVariables() {
  console.log('🧪 Running HTML Template Variables Tests...');

  let passed = 0;
  let failed = 0;

  // Test case 1: Complete product data - all template variables should be resolved
  try {
    testCompleteProductDataTemplateVariables_();
    passed++;
    console.log('✅ PASS: Complete product data template variables');
  } catch (error) {
    failed++;
    console.log(`❌ FAIL: Complete product data template variables - ${error.message}`);
  }

  // Test case 2: Minimal product data - missing fields should have empty string fallbacks
  try {
    testMinimalProductDataTemplateVariables_();
    passed++;
    console.log('✅ PASS: Minimal product data template variables');
  } catch (error) {
    failed++;
    console.log(`❌ FAIL: Minimal product data template variables - ${error.message}`);
  }

  // Test case 3: Nested structure validation - all nested fields should be flattened
  try {
    testNestedFieldsFlattening_();
    passed++;
    console.log('✅ PASS: Nested fields flattening');
  } catch (error) {
    failed++;
    console.log(`❌ FAIL: Nested fields flattening - ${error.message}`);
  }

  // Test case 4: Template variable type validation - no undefined/null values
  try {
    testTemplateVariableTypes_();
    passed++;
    console.log('✅ PASS: Template variable types validation');
  } catch (error) {
    failed++;
    console.log(`❌ FAIL: Template variable types validation - ${error.message}`);
  }

  // Test case 5: HTML template generation without errors
  try {
    testHtmlTemplateGeneration_();
    passed++;
    console.log('✅ PASS: HTML template generation');
  } catch (error) {
    failed++;
    console.log(`❌ FAIL: HTML template generation - ${error.message}`);
  }

  console.log(`\n📊 HTML Template Variables Test Summary:`);
  console.log(`   Tests Run: ${passed + failed}`);
  console.log(`   Tests Passed: ${passed}`);
  console.log(`   Tests Failed: ${failed}`);

  if (failed === 0) {
    console.log('✅ All HTML template variable tests passed!');
  } else {
    console.log(`❌ ${failed} HTML template variable test(s) failed!`);
  }
}

/**
 * Test that complete product data results in all template variables being set
 */
function testCompleteProductDataTemplateVariables_() {
  const completeProductData = {
    sportName: "Pickleball",
    division: "Open",
    season: "Fall",
    year: "2025",
    dayOfPlay: "Tuesday",
    location: "Gotham Pickleball",
    leagueStartTime: "8:00 PM",
    leagueEndTime: "11:00 PM",
    alternativeStartTime: null,
    alternativeEndTime: null,
    optionalLeagueInfo: {
      socialOrAdvanced: "Competitive/Advanced",
      sportSubCategory: "",
      types: ["Buddy Sign-up"]
    },
    importantDates: {
      seasonStartDate: "2025-10-15T04:00:00.000Z",
      seasonEndDate: "2025-12-10T04:00:00.000Z",
      offDates: ["2025-11-26T04:00:00.000Z"],
      newPlayerOrientationDateTime: null,
      scoutNightDateTime: null,
      openingPartyDate: null,
      rainDate: null,
      closingPartyDate: "TBD",
      vetRegistrationStartDateTime: "2025-09-16T23:00:00.000Z",
      earlyRegistrationStartDateTime: "2025-09-16T23:00:00.000Z",
      openRegistrationStartDateTime: "2025-09-17T23:00:00.000Z"
    },
    inventoryInfo: {
      price: 150,
      totalInventory: 64,
      numberVetSpotsToReleaseAtGoLive: 40
    }
  };

  // Mock HTML template creation
  const templateVariables = mockTemplateVariableAssignment_(completeProductData);

  // Verify critical fields are set
  const criticalFields = [
    'sportName', 'dayOfPlay', 'division', 'season', 'year', 'location',
    'seasonStartDate', 'seasonEndDate', 'price', 'totalInventory',
    'leagueStartTime', 'leagueEndTime', 'socialOrAdvanced'
  ];

  criticalFields.forEach(field => {
    if (templateVariables[field] === undefined) {
      throw new Error(`Critical field '${field}' is undefined in template variables`);
    }
    if (templateVariables[field] === null) {
      throw new Error(`Critical field '${field}' is null in template variables (should be empty string)`);
    }
  });
}

/**
 * Test that minimal product data doesn't cause undefined template variables
 */
function testMinimalProductDataTemplateVariables_() {
  const minimalProductData = {
    sportName: "Kickball",
    dayOfPlay: "Wednesday"
  };

  // Mock HTML template creation
  const templateVariables = mockTemplateVariableAssignment_(minimalProductData);

  // Verify that even missing fields have empty string fallbacks
  const expectedFields = [
    'seasonStartDate', 'seasonEndDate', 'price', 'totalInventory',
    'socialOrAdvanced', 'sportSubCategory', 'location'
  ];

  expectedFields.forEach(field => {
    if (templateVariables[field] === undefined) {
      throw new Error(`Field '${field}' should have empty string fallback, got undefined`);
    }
    if (templateVariables[field] === null) {
      throw new Error(`Field '${field}' should have empty string fallback, got null`);
    }
  });
}

/**
 * Test that nested fields are properly flattened for template access
 */
function testNestedFieldsFlattening_() {
  const nestedProductData = {
    sportName: "Bowling",
    importantDates: {
      seasonStartDate: "2025-10-01T04:00:00.000Z",
      seasonEndDate: "2025-12-15T04:00:00.000Z"
    },
    inventoryInfo: {
      price: 120,
      totalInventory: 48
    },
    optionalLeagueInfo: {
      socialOrAdvanced: "Social",
      types: ["Individual Sign-up"]
    }
  };

  const templateVariables = mockTemplateVariableAssignment_(nestedProductData);

  // Verify nested fields are accessible at top level
  if (templateVariables.seasonStartDate !== "2025-10-01T04:00:00.000Z") {
    throw new Error(`seasonStartDate not properly flattened: got ${templateVariables.seasonStartDate}`);
  }

  if (templateVariables.price !== 120) {
    throw new Error(`price not properly flattened: got ${templateVariables.price}`);
  }

  if (templateVariables.socialOrAdvanced !== "Social") {
    throw new Error(`socialOrAdvanced not properly flattened: got ${templateVariables.socialOrAdvanced}`);
  }

  // Verify arrays are preserved
  if (!Array.isArray(templateVariables.types)) {
    throw new Error(`types array not preserved: got ${typeof templateVariables.types}`);
  }
}

/**
 * Test that all template variables have valid types (no undefined/null)
 */
function testTemplateVariableTypes_() {
  const testProductData = {
    sportName: "Dodgeball",
    importantDates: {
      seasonStartDate: "2025-11-01T04:00:00.000Z",
      seasonEndDate: null, // Intentionally null to test fallback
      offDates: []
    },
    inventoryInfo: {
      price: 100
      // totalInventory intentionally missing
    },
    optionalLeagueInfo: {
      sportSubCategory: "Big Ball"
      // socialOrAdvanced intentionally missing
    }
  };

  const templateVariables = mockTemplateVariableAssignment_(testProductData);

  // Check all template variables
  Object.keys(templateVariables).forEach(key => {
    const value = templateVariables[key];

    if (value === undefined) {
      throw new Error(`Template variable '${key}' is undefined`);
    }

    if (value === null) {
      throw new Error(`Template variable '${key}' is null (should be empty string)`);
    }

    // Check that strings are properly handled
    if (typeof value === 'string' && value === 'undefined') {
      throw new Error(`Template variable '${key}' contains string 'undefined'`);
    }

    if (typeof value === 'string' && value === 'null') {
      throw new Error(`Template variable '${key}' contains string 'null'`);
    }
  });
}

/**
 * Test that HTML template can be generated without errors
 */
function testHtmlTemplateGeneration_() {
  const productData = {
    sportName: "Pickleball",
    dayOfPlay: "Thursday",
    division: "Open",
    season: "Fall",
    year: "2025",
    location: "Test Location",
    importantDates: {
      seasonStartDate: "2025-10-15T04:00:00.000Z",
      seasonEndDate: "2025-12-10T04:00:00.000Z"
    },
    inventoryInfo: {
      price: 150,
      totalInventory: 64
    }
  };

  // This should not throw any template resolution errors
  try {
    const templateVariables = mockTemplateVariableAssignment_(productData);

    // ALL template variables that are actually used in the HTML template
    // These MUST be defined or the template will fail
    const allTemplateFields = [
      'unresolvedWarningHtml',
      'sportName',
      'dayOfPlay',
      'division',
      'season',
      'year',
      'seasonStartDate',
      'seasonEndDate',
      'price',
      'location',
      'playTimes',      // ⚠️ Missing from productData!
      'leagueDetails',  // ⚠️ Missing from productData!
      'totalInventory'
    ];

    const missingFields = [];

    allTemplateFields.forEach(field => {
      // Simulate template evaluation: <?= field ?>
      const templateValue = templateVariables[field];
      if (templateValue === undefined) {
        missingFields.push(`${field} is undefined`);
      }
      if (templateValue === null) {
        missingFields.push(`${field} is null`);
      }
    });

    if (missingFields.length > 0) {
      throw new Error(`Template fields would cause evaluation errors: ${missingFields.join(', ')}`);
    }

  } catch (error) {
    throw new Error(`HTML template generation failed: ${error.message}`);
  }
}

/**
 * Mock the template variable assignment logic from createShopifyProduct.gs
 * This replicates the actual logic but returns the variables for testing
 */
function mockTemplateVariableAssignment_(productData) {
  const templateVariables = {};

  // Flatten nested structure for template access
  const flatData = flattenProductData_(productData);

  // First set all top-level fields from original productData
  Object.keys(productData).forEach(key => {
    if (typeof productData[key] !== 'object' || productData[key] === null || Array.isArray(productData[key])) {
      templateVariables[key] = productData[key] || '';
    }
  });

  // Then set all flattened nested fields
  Object.keys(flatData).forEach(key => {
    // Only set if not already set from top-level (avoid overwriting)
    if (!(key in templateVariables)) {
      templateVariables[key] = flatData[key] || '';
    }
  });

  // Add the special template variables that are set separately
  templateVariables.unresolvedWarningHtml = '';  // This would be set by the actual dialog logic

  // Add missing template variables that are used in HTML but not in productData
  const leagueStartTime = flatData.leagueStartTime || '';
  const leagueEndTime = flatData.leagueEndTime || '';
  templateVariables.playTimes = (leagueStartTime && leagueEndTime) ? `${leagueStartTime} - ${leagueEndTime}` : '';
  templateVariables.leagueDetails = ''; // This can be filled manually by user

  return templateVariables;
}
