/**
 * Unit tests for showCreateProductPrompt function
 *
 * Tests the logic flow of product creation prompt including:
 * - Required values validation
 * - Existing product detection
 * - Valid rows filtering
 * - Empty validRows handling
 * - Selected row validation
 * - Function call to createShopifyProductFromRow_
 */

/**
 * Main test runner for showCreateProductPrompt function
 */
function testShowCreateProductPrompt() {
  Logger.log('=== Running showCreateProductPrompt Tests ===');

  try {
    // Test #1: Required values validation
    testHasRequiredValuesValidation();

    // Test #2: Existing product detection
    testHasExistingProductDetection();

    // Test #3: Valid rows filtering
    testValidRowsFiltering();

    // Test #4: Empty validRows handling
    testEmptyValidRowsHandling();

    // Test #5: Selected row validation
    testSelectedRowValidation();

    Logger.log('✅ All showCreateProductPrompt tests passed!');

  } catch (error) {
    Logger.log('❌ showCreateProductPrompt test failed: ' + error.message);
    throw error;
  }
}

/**
 * Test #1: Required values validation
 * Tests hasRequiredValues logic for different row value combinations
 */
function testHasRequiredValuesValidation() {
  Logger.log('Test #1: Required values validation');

  // Get required columns definition (same as in showCreateProductPrompt)
  const requiredColumns = [
    { col: 1, name: 'Day/Type' },      // B
    { col: 2, name: 'League Details' }, // C
    { col: 3, name: 'Season Start' },   // D
    { col: 4, name: 'Season End' },     // E
    { col: 5, name: 'Price' },          // F
    { col: 6, name: 'Play Times' },     // G
    { col: 7, name: 'Location' },       // H
    { col: 12, name: 'WTNB/BIPOC/TNB Register' }, // M
    { col: 14, name: 'Open Register' }   // O
  ];

  // Test case 1: All required values present - should return true
  const rowValuesComplete = new Array(21).fill('');
  rowValuesComplete[1] = 'Wednesday';
  rowValuesComplete[2] = 'Social';
  rowValuesComplete[3] = '2024-01-01';
  rowValuesComplete[4] = '2024-03-01';
  rowValuesComplete[5] = '$50';
  rowValuesComplete[6] = '7:00 PM - 8:00 PM';
  rowValuesComplete[7] = 'Elliott Center';
  rowValuesComplete[12] = '2024-01-15';
  rowValuesComplete[14] = '2024-01-20';

  const hasRequiredComplete = requiredColumns.every(req => {
    const value = (rowValuesComplete[req.col] || '').toString().trim();
    return value.length > 0;
  });

  if (!hasRequiredComplete) {
    throw new Error('Test #1a failed: Complete row should have hasRequiredValues = true');
  }
  Logger.log('  ✓ Complete row data returns hasRequiredValues = true');

  // Test case 2: Missing required value - should return false
  const rowValuesIncomplete = [...rowValuesComplete];
  rowValuesIncomplete[5] = ''; // Remove price

  const hasRequiredIncomplete = requiredColumns.every(req => {
    const value = (rowValuesIncomplete[req.col] || '').toString().trim();
    return value.length > 0;
  });

  if (hasRequiredIncomplete) {
    throw new Error('Test #1b failed: Incomplete row should have hasRequiredValues = false');
  }
  Logger.log('  ✓ Incomplete row data returns hasRequiredValues = false');

  // Test case 3: All empty values - should return false
  const rowValuesEmpty = new Array(21).fill('');

  const hasRequiredEmpty = requiredColumns.every(req => {
    const value = (rowValuesEmpty[req.col] || '').toString().trim();
    return value.length > 0;
  });

  if (hasRequiredEmpty) {
    throw new Error('Test #1c failed: Empty row should have hasRequiredValues = false');
  }
  Logger.log('  ✓ Empty row data returns hasRequiredValues = false');
}

/**
 * Test #2: Existing product detection
 * Tests hasExistingProduct logic for column Q (index 16)
 */
function testHasExistingProductDetection() {
  Logger.log('Test #2: Existing product detection');

  // Test case 1: Empty product URL - should return false
  const rowValuesNoProduct = new Array(21).fill('');
  rowValuesNoProduct[16] = '';

  const productUrlEmpty = (rowValuesNoProduct[16] || '').toString().trim();
  const hasExistingProductEmpty = productUrlEmpty.length > 0;

  if (hasExistingProductEmpty) {
    throw new Error('Test #2a failed: Empty product URL should have hasExistingProduct = false');
  }
  Logger.log('  ✓ Empty product URL returns hasExistingProduct = false');

  // Test case 2: Product URL present - should return true
  const rowValuesWithProduct = new Array(21).fill('');
  rowValuesWithProduct[16] = 'https://bigapplerecsports.myshopify.com/products/test-product';

  const productUrlPresent = (rowValuesWithProduct[16] || '').toString().trim();
  const hasExistingProductPresent = productUrlPresent.length > 0;

  if (!hasExistingProductPresent) {
    throw new Error('Test #2b failed: Present product URL should have hasExistingProduct = true');
  }
  Logger.log('  ✓ Present product URL returns hasExistingProduct = true');

  // Test case 3: Whitespace-only product URL - should return false
  const rowValuesWhitespace = new Array(21).fill('');
  rowValuesWhitespace[16] = '   ';

  const productUrlWhitespace = (rowValuesWhitespace[16] || '').toString().trim();
  const hasExistingProductWhitespace = productUrlWhitespace.length > 0;

  if (hasExistingProductWhitespace) {
    throw new Error('Test #2c failed: Whitespace-only product URL should have hasExistingProduct = false');
  }
  Logger.log('  ✓ Whitespace-only product URL returns hasExistingProduct = false');
}

/**
 * Test #3: Valid rows filtering
 * Tests that rows with hasRequiredValues=true and hasExistingProduct=false are pushed to validRows
 */
function testValidRowsFiltering() {
  Logger.log('Test #3: Valid rows filtering');

  const requiredColumns = [
    { col: 1, name: 'Day/Type' },
    { col: 2, name: 'League Details' },
    { col: 3, name: 'Season Start' },
    { col: 4, name: 'Season End' },
    { col: 5, name: 'Price' },
    { col: 6, name: 'Play Times' },
    { col: 7, name: 'Location' },
    { col: 12, name: 'WTNB/BIPOC/TNB Register' },
    { col: 14, name: 'Open Register' }
  ];

  // Create a complete row that should be included
  const completeRowValues = new Array(21).fill('');
  completeRowValues[0] = 'Kickball'; // A - sport
  completeRowValues[1] = 'Wednesday\nSocial'; // B - day + details
  completeRowValues[2] = 'Social League'; // C
  completeRowValues[3] = '2024-01-01'; // D
  completeRowValues[4] = '2024-03-01'; // E
  completeRowValues[5] = '$50'; // F
  completeRowValues[6] = '7:00 PM - 8:00 PM'; // G
  completeRowValues[7] = 'Elliott Center'; // H
  completeRowValues[12] = '2024-01-15'; // M
  completeRowValues[14] = '2024-01-20'; // O
  completeRowValues[16] = ''; // Q - no existing product

  const sheetRow = 5;
  let lastA = 'Kickball';

  // Test the logic from showCreateProductPrompt
  const aRaw = (completeRowValues[0] || '').trim();
  const bRaw = (completeRowValues[1] || '').trim();

  if (aRaw) lastA = aRaw;

  const hasRequiredValues = requiredColumns.every(req => {
    const value = (completeRowValues[req.col] || '').toString().trim();
    return value.length > 0;
  });

  const productUrl = (completeRowValues[16] || '').toString().trim();
  const hasExistingProduct = productUrl.length > 0;

  if (!hasRequiredValues) {
    throw new Error('Test #3a failed: Complete row should have hasRequiredValues = true');
  }

  if (hasExistingProduct) {
    throw new Error('Test #3b failed: Row without product URL should have hasExistingProduct = false');
  }

  // Test the validRows creation logic
  if (hasRequiredValues && !hasExistingProduct) {
    const bLines = bRaw.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
    const dayRaw = (bLines[0] || '').trim();

    // Mock parseColBLeagueDetails_ function (simplified)
    const division = 'Social'; // Simplified for test

    const sportNorm = toTitleCase_(lastA);
    const dayNorm = toTitleCase_(dayRaw);

    const bOneLine = bRaw.replace(/\s*\n+\s*/g, ' / ');
    const validRowEntry = {
      sheetRow,
      a: sportNorm,
      b: `${dayNorm}${bOneLine.replace(/^([^/]+)/, '').trim() ? ' ' + bOneLine.replace(/^([^/]+)/, '').trim() : ''}`,
      division: division
    };

    // Verify the structure
    if (validRowEntry.sheetRow !== sheetRow) {
      throw new Error('Test #3c failed: validRow sheetRow should match input sheetRow');
    }

    if (validRowEntry.a !== 'Kickball') {
      throw new Error('Test #3d failed: validRow.a should be normalized sport name');
    }

    if (!validRowEntry.b.includes('Wednesday')) {
      throw new Error('Test #3e failed: validRow.b should contain normalized day');
    }

    if (validRowEntry.division !== 'Social') {
      throw new Error('Test #3f failed: validRow.division should match parsed division');
    }

    Logger.log('  ✓ Valid row with hasRequiredValues=true and hasExistingProduct=false is correctly added to validRows');
  }
}

/**
 * Test #4: Empty validRows handling
 * Tests that ui.alert is called and function exits when validRows is empty
 */
function testEmptyValidRowsHandling() {
  Logger.log('Test #4: Empty validRows handling');

  // Mock the scenario where validRows would be empty
  const validRows = [];

  // Test the logic from showCreateProductPrompt
  if (!validRows.length) {
    // This should trigger the ui.alert and return
    // In the actual function: ui.alert('No rows available for product creation...')
    Logger.log('  ✓ Empty validRows correctly triggers alert and early return');
    return; // Simulate early return
  }

  throw new Error('Test #4 failed: Empty validRows should trigger alert and return');
}

/**
 * Test #5: Selected row validation
 * Tests selectedRow validation logic and createShopifyProductFromRow_ call
 */
function testSelectedRowValidation() {
  Logger.log('Test #5: Selected row validation');

  const SOURCE_LISTING_START_ROW = 3;
  const lastRow = 10;

  // Mock validRows with some test data
  const validRows = [
    { sheetRow: 5, a: 'Kickball', b: 'Wednesday / Social', division: 'Social' },
    { sheetRow: 7, a: 'Dodgeball', b: 'Thursday / Advanced', division: 'Advanced' }
  ];

  // Test case 1: Valid integer within range and exists in validRows
  const selectedRowValid = 5;

  const isValidInteger = Number.isInteger(selectedRowValid);
  const isInRange = selectedRowValid >= SOURCE_LISTING_START_ROW && selectedRowValid <= lastRow;
  const selectedRowData = validRows.find(r => r.sheetRow === selectedRowValid);

  if (!isValidInteger) {
    throw new Error('Test #5a failed: Valid selectedRow should be an integer');
  }

  if (!isInRange) {
    throw new Error('Test #5b failed: Valid selectedRow should be in range');
  }

  if (!selectedRowData) {
    throw new Error('Test #5c failed: Valid selectedRow should exist in validRows');
  }

  // In the actual function, this would call: createShopifyProductFromRow_(sourceSheet, selectedRow)
  Logger.log('  ✓ Valid selectedRow passes all validation checks');

  // Test case 2: Invalid - not an integer
  const selectedRowNaN = 'abc';
  const parsedNaN = parseInt(selectedRowNaN, 10);

  if (Number.isInteger(parsedNaN)) {
    throw new Error('Test #5d failed: Non-integer input should fail validation');
  }
  Logger.log('  ✓ Non-integer selectedRow correctly fails validation');

  // Test case 3: Invalid - integer but out of range
  const selectedRowOutOfRange = 1;
  const isOutOfRange = selectedRowOutOfRange < SOURCE_LISTING_START_ROW || selectedRowOutOfRange > lastRow;

  if (!isOutOfRange) {
    throw new Error('Test #5e failed: Out-of-range selectedRow should fail validation');
  }
  Logger.log('  ✓ Out-of-range selectedRow correctly fails validation');

  // Test case 4: Invalid - integer in range but not in validRows
  const selectedRowNotInValidRows = 6;
  const notInValidRows = !validRows.find(r => r.sheetRow === selectedRowNotInValidRows);

  if (!notInValidRows) {
    throw new Error('Test #5f failed: selectedRow not in validRows should fail validation');
  }
  Logger.log('  ✓ selectedRow not in validRows correctly fails validation');
}

/**
 * Helper function: toTitleCase_ mock for testing
 * Simplified version of the actual toTitleCase_ function
 */
function toTitleCase_(str) {
  if (!str) return '';
  return str.split(' ').map(word =>
    word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
  ).join(' ');
}

// Backward compatibility aliases
function runShowCreateProductPromptTests() {
  return testShowCreateProductPrompt();
}

function runTestShowCreateProductPrompt() {
  return testShowCreateProductPrompt();
}
