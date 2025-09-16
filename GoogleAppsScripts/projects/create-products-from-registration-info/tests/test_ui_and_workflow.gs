/**
 * Consolidated tests for UI, workflow, and user interaction functions
 * Combines tests for dialogs, editing flow, confirmation displays, and validation
 */

/**
 * Test confirmation display building
 */
function testConfirmationDisplays() {
  console.log('Testing confirmation displays...');
  
  const testData = {
    sportName: 'Kickball',
    dayOfPlay: 'Monday',
    division: 'Open',
    season: 'Fall',
    year: 2025,
    location: 'Test Location',
    price: 120,
    totalInventory: 100
  };
  
  try {
    const display = buildConfirmationDisplay_(testData);
    console.log(`  ✅ Confirmation display: ${display.includes('Kickball') && display.includes('Monday')}`);
  } catch (error) {
    console.log(`  ❌ Confirmation display: ${error.message}`);
  }
}

/**
 * Test error display building
 */
function testErrorDisplays() {
  console.log('Testing error displays...');
  
  const testData = {
    sportName: 'Kickball',
    dayOfPlay: 'Monday'
    // Missing required fields
  };
  
  const missingFields = ['division', 'season', 'year', 'location', 'price', 'totalInventory'];
  
  try {
    const display = buildErrorDisplay_(testData, missingFields);
    console.log(`  ✅ Error display: ${display.includes('Cannot create product') && display.includes('missing')}`);
  } catch (error) {
    console.log(`  ❌ Error display: ${error.message}`);
  }
}

/**
 * Test editing flow validation
 */
function testEditingFlow() {
  console.log('Testing editing flow...');
  
  const testData = {
    sportName: 'Kickball',
    dayOfPlay: 'Monday',
    division: 'Open',
    season: 'Fall',
    year: 2025,
    location: 'Test Location',
    price: 120,
    totalInventory: 100
  };
  
  try {
    // Test field validation
    const validResult = validateFieldInput_('price', '150', testData);
    const invalidResult = validateFieldInput_('price', 'invalid', testData);
    
    console.log(`  ✅ Price validation: ${validResult.ok === true && invalidResult.ok === false}`);
    
    // Test enum validation
    const enumResult = validateEnumValue_('division', 'open', 'Kickball');
    console.log(`  ✅ Enum validation: ${enumResult.valid === true && enumResult.normalizedValue === 'Open'}`);
    
  } catch (error) {
    console.log(`  ❌ Editing flow: ${error.message}`);
  }
}

/**
 * Test field list generation
 */
function testFieldListGeneration() {
  console.log('Testing field list generation...');
  
  const testData = {
    sportName: 'Kickball',
    dayOfPlay: 'Monday',
    division: 'Open',
    season: 'Fall',
    year: 2025,
    location: 'Test Location',
    price: 120,
    totalInventory: 100,
    numberVetSpotsToReleaseAtGoLive: 50
  };
  
  try {
    const fields = getEditableFieldsList_(testData);
    console.log(`  ✅ Field list: ${fields.length > 0 && fields[0].includes('Sport: Kickball')}`);
    
    // Test sport-specific filtering
    const pickleballData = { ...testData, sportName: 'Pickleball' };
    const pickleballFields = getEditableFieldsList_(pickleballData);
    const hasSportSubCategory = pickleballFields.some(f => f.includes('Sport Sub-Category'));
    console.log(`  ✅ Sport filtering: ${!hasSportSubCategory}`); // Should be filtered out for Pickleball
    
  } catch (error) {
    console.log(`  ❌ Field list generation: ${error.message}`);
  }
}

/**
 * Test data flattening and reconstruction
 */
function testDataFlattening() {
  console.log('Testing data flattening...');
  
  const nestedData = {
    sportName: 'Kickball',
    regularSeasonBasicDetails: {
      year: 2025,
      season: 'Fall',
      dayOfPlay: 'Monday',
      division: 'Open',
      location: 'Test Location'
    },
    inventoryInfo: {
      price: 120,
      totalInventory: 100
    }
  };
  
  try {
    const flattened = flattenProductData_(nestedData);
    console.log(`  ✅ Flattening: ${flattened.sportName === 'Kickball' && flattened.price === 120}`);
    
    const reconstructed = reconstructNestedStructure_(flattened);
    console.log(`  ✅ Reconstruction: ${reconstructed.regularSeasonBasicDetails.year === 2025}`);
    
  } catch (error) {
    console.log(`  ❌ Data flattening: ${error.message}`);
  }
}

/**
 * Test required field validation
 */
function testRequiredFieldValidation() {
  console.log('Testing required field validation...');
  
  const completeData = {
    sportName: 'Kickball',
    year: 2025,
    season: 'Fall',
    dayOfPlay: 'Monday',
    division: 'Open',
    location: 'Test Location',
    leagueStartTime: new Date(),
    leagueEndTime: new Date(),
    seasonStartDate: new Date(),
    seasonEndDate: new Date(),
    price: 120,
    totalInventory: 100
  };
  
  const incompleteData = {
    sportName: 'Kickball'
    // Missing required fields
  };
  
  try {
    const completeValidation = validateRequiredFields_(completeData);
    const incompleteValidation = validateRequiredFields_(incompleteData);
    
    console.log(`  ✅ Complete validation: ${completeValidation.isValid === true}`);
    console.log(`  ✅ Incomplete validation: ${incompleteValidation.isValid === false && incompleteValidation.missingFields.length > 0}`);
    
  } catch (error) {
    console.log(`  ❌ Required field validation: ${error.message}`);
  }
}

/**
 * Test enum options retrieval
 */
function testEnumOptions() {
  console.log('Testing enum options...');
  
  try {
    const sportOptions = getEnumOptionsForField_('sportName', 'Kickball');
    const locationOptions = getEnumOptionsForField_('location', 'Kickball');
    const invalidOptions = getEnumOptionsForField_('invalidField', 'Kickball');
    
    console.log(`  ✅ Sport options: ${Array.isArray(sportOptions) && sportOptions.length > 0}`);
    console.log(`  ✅ Location options: ${Array.isArray(locationOptions) && locationOptions.length > 0}`);
    console.log(`  ✅ Invalid options: ${invalidOptions === null}`);
    
  } catch (error) {
    console.log(`  ❌ Enum options: ${error.message}`);
  }
}

/**
 * Run all UI and workflow tests
 */
function runUIAndWorkflowTests() {
  console.log('🧪 Running UI and workflow tests...\n');
  
  testConfirmationDisplays();
  testErrorDisplays();
  testEditingFlow();
  testFieldListGeneration();
  testDataFlattening();
  testRequiredFieldValidation();
  testEnumOptions();
  
  console.log('\n✅ All UI and workflow tests completed');
}
