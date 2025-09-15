/**
 * Tests for parseColFPrice_ function
 *
 * @fileoverview Test suite for price parsing functionality
 * @requires ../src/config/constants.gs
 * @requires ../src/helpers/normalizers.gs
 * @requires ../src/parsers/parseColFPrice_.gs
 */

// Import references for editor support
/// <reference path="../src/config/constants.gs" />
/// <reference path="../src/helpers/normalizers.gs" />
/// <reference path="../src/parsers/parseColFPrice_.gs" />

/**
 * Main test function for parseColFPrice_
 * Tests various price input formats
 */
function testParseColFPrice_() {
  console.log('🧪 Running parseColFPrice_ comprehensive tests...');

  let passedTests = 0;
  let totalTests = 0;
  const failedTests = [];

  // Test 1: Valid price inputs
  totalTests++;
  const validPriceResult = testValidPriceInputs_();
  if (validPriceResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 1 FAILED: Valid price inputs - ${validPriceResult}`);
  }

  // Test 2: Invalid price inputs
  totalTests++;
  const invalidPriceResult = testInvalidPriceInputs_();
  if (invalidPriceResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 2 FAILED: Invalid price inputs - ${invalidPriceResult}`);
  }

  // Test 3: Edge cases and empty inputs
  totalTests++;
  const edgeCasesResult = testPriceEdgeCases_();
  if (edgeCasesResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 3 FAILED: Edge cases - ${edgeCasesResult}`);
  }

  // Display results
  console.log(`\n📊 parseColFPrice_ Test Summary:`);
  console.log(`   Tests Run: ${totalTests}`);
  console.log(`   Tests Passed: ${passedTests}`);
  console.log(`   Tests Failed: ${failedTests.length}`);

  if (failedTests.length === 0) {
    console.log('✅ All parseColFPrice_ tests passed!');
  } else {
    console.log('❌ Some parseColFPrice_ tests failed!');
    failedTests.forEach(error => console.error(error));
  }

  if (failedTests.length > 0) {
    throw new Error('❌ Some parsePriceNumber_ tests failed!');
  }

  return passedTests === totalTests;
}

/**
 * Test valid price inputs that should return a number
 * @returns {boolean|string} true if passed, error message if failed
 */
function testValidPriceInputs_() {
  try {
    const testCases = [
      { input: "150", expectedPrice: 150, description: "String number" },
      { input: "$150", expectedPrice: 150, description: "String with dollar sign" },
      { input: 150, expectedPrice: 150, description: "Number input" },
      { input: "$99.99", expectedPrice: 99.99, description: "Decimal price with dollar sign" },
      { input: "99.99", expectedPrice: 99.99, description: "Decimal price string" },
      { input: "$0", expectedPrice: 0, description: "Zero price" },
      { input: "0", expectedPrice: 0, description: "Zero price string" }
    ];

    for (const testCase of testCases) {
      const { price } = parseColFPrice_(testCase.input);

      if (price !== testCase.expectedPrice) {
        return `Price mismatch for ${testCase.description}: expected ${testCase.expectedPrice}, got ${price}`;
      }

    }

    return true;
  } catch (error) {
    return `ERROR in testValidPriceInputs_: ${error.toString()}`;
  }
}

/**
 * Test invalid price inputs that should return null
 * @returns {boolean|string} true if passed, error message if failed
 */
function testInvalidPriceInputs_() {
  try {
    const testCases = [
      { input: "abc", description: "Non-numeric string" },
      { input: "$abc", description: "Dollar sign with letters" },
      { input: "150abc", description: "Mixed numbers and letters" },
      { input: "$150abc", description: "Dollar sign with mixed content" },
      { input: "free", description: "Word instead of number" },
      { input: "$free", description: "Dollar sign with word" },
      { input: "1$50", description: "Dollar sign in middle" },
      { input: "15$0", description: "Dollar sign in wrong position" },
      { input: "$1$50", description: "Multiple dollar signs" }
    ];

    for (const testCase of testCases) {
      const { price } = parseColFPrice_(testCase.input);

      if (price !== null) {
        return `Invalid price should return null for ${testCase.description}: got ${price}`;
      }

    }

    return true;
  } catch (error) {
    return `ERROR in testInvalidPriceInputs_: ${error.toString()}`;
  }
}

/**
 * Test edge cases like empty inputs, null, undefined
 * @returns {boolean|string} true if passed, error message if failed
 */
function testPriceEdgeCases_() {
  try {
    const testCases = [
      { input: "", description: "Empty string" },
      { input: "   ", description: "Whitespace only" },
      { input: null, description: "Null input" },
      { input: undefined, description: "Undefined input" },
      { input: "$", description: "Dollar sign only" },
      { input: ".", description: "Decimal point only" },
      { input: "$.", description: "Dollar sign and decimal point only" }
    ];

    for (const testCase of testCases) {
      const { price } = parseColFPrice_(testCase.input);

      if (price !== null) {
        return `Edge case should return null for ${testCase.description}: got ${price}`;
      }

    }

    return true;
  } catch (error) {
    return `ERROR in testPriceEdgeCases_: ${error.toString()}`;
  }
}
