/**
 * Tests for parseColMNORegistrationDates_
 */
/// <reference path="../src/parsers/parseColMNORegistrationDates_.gs" />
/// <reference path="../src/helpers/dateParsers.gs" />

function test_mno_row5_expected_utc_() {
  const m = 'SECOND REGISTRATION\n\nWeds, Sept. 3rd, 6pm\n(through 5pm on 9/4)';
  const n = 'FIRST\nREGISTRATION\n\nTues, Sept. 2nd, 6pm\n(through 5pm on 5/3)';
  const o = 'THIRD\nREGISTRATION\n\nThurs, Sept. 4th, 6pm';
  const total = 364;
  const r = parseColMNORegistrationDates_(m, n, o, total);

  // Expect 6pm ET in early Sept → UTC-4, so 22:00Z
  function iso(d){ return d && typeof d.toISOString==='function' ? d.toISOString() : String(d); }
  if (!iso(r.vetRegistrationStartDateTime).includes('T22:00:00')) throw new Error('vet should be 22:00Z');
  if (!iso(r.earlyRegistrationStartDateTime).includes('T22:00:00')) throw new Error('early should be 22:00Z');
  if (!iso(r.openRegistrationStartDateTime).includes('T22:00:00')) throw new Error('open should be 22:00Z');
  if (r.numberVetSpotsToReleaseAtGoLive !== total) throw new Error('vet spots should default to total inventory');
}

/**
 * Comprehensive tests for parseColMNORegistrationDates_ function
 *
 * @fileoverview Test suite for registration dates parsing
 * @requires ../src/config/constants.gs
 * @requires ../src/helpers/normalizers.gs
 * @requires ../src/helpers/dateParsers.gs
 * @requires ../src/parsers/parseColMNORegistrationDates_.gs
 */

// Import references for editor support
/// <reference path="../src/config/constants.gs" />
/// <reference path="../src/helpers/normalizers.gs" />
/// <reference path="../src/helpers/dateParsers.gs" />
/// <reference path="../src/parsers/parseColMNORegistrationDates_.gs" />

/**
 * Main test function for parseColMNORegistrationDates_
 */
function testParseColMNORegistrationDates_() {
  console.log('🧪 Running parseColMNORegistrationDates_ comprehensive tests...');

  let passedTests = 0;
  let totalTests = 0;
  const failedTests = [];

  // Test 1: All falsy inputs
  totalTests++;
  const falsyResult = testFalsyInputs_();
  if (falsyResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 1 FAILED: Falsy inputs - ${falsyResult}`);
  }

  // Test 2: Registration prefix removal
  totalTests++;
  const prefixResult = testRegistrationPrefixRemoval_();
  if (prefixResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 2 FAILED: Registration prefix removal - ${prefixResult}`);
  }

  // Test 3: Through/until suffix removal
  totalTests++;
  const suffixResult = testThroughUntilSuffixRemoval_();
  if (suffixResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 3 FAILED: Through/until suffix removal - ${suffixResult}`);
  }

  // Test 4: Veteran spots calculation
  totalTests++;
  const vetSpotsResult = testVetSpotsCalculation_();
  if (vetSpotsResult === true) {
    passedTests++;
  } else {
    failedTests.push(`Test 4 FAILED: Veteran spots calculation - ${vetSpotsResult}`);
  }

  // Display results
  console.log(`\n📊 parseColMNORegistrationDates_ Test Summary:`);
  console.log(`   Tests Run: ${totalTests}`);
  console.log(`   Tests Passed: ${passedTests}`);
  console.log(`   Tests Failed: ${failedTests.length}`);

  if (failedTests.length > 0) {
    for (const failure of failedTests) {
      console.log(failure);
    }
    throw new Error('❌ Some parseColMNORegistrationDates_ tests failed!');
  }
}

/**
 * Tests falsy inputs return null values.
 * @returns {boolean|string} True if all tests pass, or an error message.
 */
function testFalsyInputs_() {
  const testCases = [
    { m: null, n: null, o: null, description: "All null" },
    { m: '', n: '', o: '', description: "All empty strings" },
    { m: '   ', n: '   ', o: '   ', description: "All whitespace" },
    { m: 'valid date', n: null, o: '', description: "Mixed falsy" }
  ];

  for (const testCase of testCases) {
    const result = parseColMNORegistrationDates_(testCase.m, testCase.n, testCase.o, 100);

    // For falsy inputs, corresponding datetime should be null
    if ((!testCase.m || !testCase.m.trim()) && result.earlyRegistrationStartDateTime !== null) {
      return `FAIL for "${testCase.description}": earlyRegistrationStartDateTime should be null for falsy M input`;
    }
    if ((!testCase.n || !testCase.n.trim()) && result.vetRegistrationStartDateTime !== null) {
      return `FAIL for "${testCase.description}": vetRegistrationStartDateTime should be null for falsy N input`;
    }
    if ((!testCase.o || !testCase.o.trim()) && result.openRegistrationStartDateTime !== null) {
      return `FAIL for "${testCase.description}": openRegistrationStartDateTime should be null for falsy O input`;
    }
  }
  return true;
}

/**
 * Tests registration prefix removal.
 * @returns {boolean|string} True if all tests pass, or an error message.
 */
function testRegistrationPrefixRemoval_() {
  const testCases = [
    { input: "Early Registration Sept 16th 7PM", expected: "Sept 16th 7PM", description: "Early Registration prefix" },
    { input: "Veteran registration Wed Sept 3rd 6pm", expected: "Wed Sept 3rd 6pm", description: "Veteran registration prefix" },
    { input: "REGISTRATION 8/29/25 @ 7pm", expected: "8/29/25 @ 7pm", description: "REGISTRATION prefix (uppercase)" },
    { input: "Sept 16th 7PM", expected: "Sept 16th 7PM", description: "No registration prefix" }
  ];

  for (const testCase of testCases) {
    const cleaned = cleanRegistrationString_(testCase.input);
    if (cleaned !== testCase.expected) {
      return `FAIL for "${testCase.description}": Expected "${testCase.expected}", got "${cleaned}"`;
    }
  }
  return true;
}

/**
 * Tests through/until suffix removal.
 * @returns {boolean|string} True if all tests pass, or an error message.
 */
function testThroughUntilSuffixRemoval_() {
  const testCases = [
    { input: "Sept 16th 7PM through Oct 1st", expected: "Sept 16th 7PM", description: "through suffix" },
    { input: "Wed Sept 3rd 6pm until further notice", expected: "Wed Sept 3rd 6pm", description: "until suffix" },
    { input: "8/29/25 @ 7pm (through next week)", expected: "8/29/25 @ 7pm", description: "through with parentheses" },
    { input: "Sept 16th 7PM - until Sept 20th", expected: "Sept 16th 7PM", description: "until with dash" },
    { input: "Sept 16th 7PM", expected: "Sept 16th 7PM", description: "No through/until suffix" }
  ];

  for (const testCase of testCases) {
    const cleaned = cleanRegistrationString_(testCase.input);
    if (cleaned !== testCase.expected) {
      return `FAIL for "${testCase.description}": Expected "${testCase.expected}", got "${cleaned}"`;
    }
  }
  return true;
}

/**
 * Tests veteran spots calculation.
 * @returns {boolean|string} True if all tests pass, or an error message.
 */
function testVetSpotsCalculation_() {
  const testCases = [
    { input: "Veteran registration: 20 spots available", totalInventory: 100, expected: 20, description: "20 spots" },
    { input: "Vet reg: 15 through Oct 1st", totalInventory: 100, expected: 15, description: "15 through" },
    { input: "30 spots until further notice", totalInventory: 100, expected: 30, description: "30 until" },
    { input: "Sept 15th 7PM\n\nOnly holding 40 vet spots ", totalInventory: 100, expected: 40, description: "Multi-line with vet keyword" },
    { input: "Registration\n\nHolding 25 inventory spots", totalInventory: 100, expected: 25, description: "Multi-line with inventory keyword" },
    { input: "Early reg\n\n30 spot limit", totalInventory: 100, expected: 30, description: "Multi-line with spot keyword" },
    { input: "Veteran registration Wed Sept 3rd", totalInventory: 100, expected: 100, description: "No number found - use total inventory" },
    { input: "", totalInventory: 50, expected: 50, description: "Empty string - use total inventory" }
  ];

  for (const testCase of testCases) {
    const result = parseColMNORegistrationDates_('', testCase.input, '', testCase.totalInventory);

    if (result.numberVetSpotsToReleaseAtGoLive !== testCase.expected) {
      return `FAIL for "${testCase.description}": Expected ${testCase.expected}, got ${result.numberVetSpotsToReleaseAtGoLive}`;
    }
  }
  return true;
}
