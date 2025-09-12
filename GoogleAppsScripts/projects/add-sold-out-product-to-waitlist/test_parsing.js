/**
 * Simple tests for the parseLabel and sorting logic
 * Run these in the Apps Script editor console
 */

function testCreateFormattedLabel() {
  console.log('=== Testing createFormattedLabel ===');
  
  // Test complete data
  let result = createFormattedLabel({ sport: 'Dodgeball', day: 'Tuesday', division: 'Open', otherIdentifier: 'Special Event' });
  console.log('Complete:', result);
  console.assert(result === 'Dodgeball - Tuesday - Open Division - Special Event', 'Complete test failed');
  
  // Test missing otherIdentifier
  result = createFormattedLabel({ sport: 'Kickball', day: 'Monday', division: 'WTNB+' });
  console.log('No other:', result);
  console.assert(result === 'Kickball - Monday - WTNB+ Division', 'No other test failed');
  
  // Test only sport and day
  result = createFormattedLabel({ sport: 'Dodgeball', day: 'Wednesday' });
  console.log('Sport+Day:', result);
  console.assert(result === 'Dodgeball - Wednesday', 'Sport+Day test failed');
  
  // Test only otherIdentifier
  result = createFormattedLabel({ otherIdentifier: 'Kickball Classic' });
  console.log('Other only:', result);
  console.assert(result === 'Kickball Classic', 'Other only test failed');
  
  console.log('createFormattedLabel tests completed');
}

function testSortWaitlistOptions() {
  console.log('=== Testing sortWaitlistLabels ===');
  
  const testLabels = [
    'Spring Tournament 2025',
    'Dodgeball - Monday - Open Division',
    'Kickball - Tuesday - WTNB+ Division',
    'Dodgeball - Monday - WTNB Division',
    'Basketball Classic 2024',
    'Kickball - Sunday - Open Division',
    'Summer Event',
    'Dodgeball - Tuesday - Open Division'
  ];
  
  const sorted = sortWaitlistLabels([...testLabels]);
  console.log('Original:', testLabels);
  console.log('Sorted:', sorted);
  
  // Check that sports come first
  const sportsItems = sorted.filter(label => 
    ['Dodgeball', 'Kickball'].some(sport => label.includes(sport))
  );
  const nonSportsItems = sorted.filter(label => 
    !['Dodgeball', 'Kickball'].some(sport => label.includes(sport))
  );
  
  console.log('Sports items:', sportsItems);
  console.log('Non-sports items:', nonSportsItems);
  
  console.log('sortWaitlistLabels tests completed');
}

function testParseLabelForSorting() {
  console.log('=== Testing parseLabelForSorting ===');
  
  const testCases = [
    'Dodgeball - Monday - Open Division',
    'Kickball - Tuesday - WTNB+ Division', 
    'Spring Tournament 2025',
    'Basketball Classic'
  ];
  
  testCases.forEach(label => {
    const parsed = parseLabelForSorting(label);
    console.log(`Label: "${label}"`);
    console.log('Parsed:', parsed);
    console.log('---');
  });
  
  console.log('parseLabelForSorting tests completed');
}

function testReturnToDefault() {
  console.log('=== Testing returnToDefault ===');
  
  // Note: This test requires manual verification since it interacts with the actual form
  // To test this function:
  // 1. Make sure your form has multiple waitlist options
  // 2. Call returnToDefault() in the console
  // 3. Verify that only the sentinel option remains:
  //    "No waitlists currently available - registrations have not yet gone live / sold out"
  
  console.log('returnToDefault test setup:');
  console.log('1. Add some test options to your form first');
  console.log('2. Then call returnToDefault() manually');
  console.log('3. Verify only sentinel option remains');
  console.log('Expected sentinel:', NO_WAITLISTS_SENTINEL);
  
  // Test the return message format
  const expectedResult = { 
    message: 'Successfully reset waitlist form to default state', 
    sentinel: NO_WAITLISTS_SENTINEL 
  };
  console.log('Expected result format:', expectedResult);
  
  console.log('returnToDefault test completed (manual verification required)');
}

function testReturnToDefaultLive() {
  console.log('=== Live Test: returnToDefault ===');
  
  try {
    // Call the actual function
    const result = returnToDefault();
    console.log('✅ returnToDefault executed successfully');
    console.log('Result:', result);
    
    // Verify the result structure
    if (result.message && result.sentinel) {
      console.log('✅ Result has expected structure');
    } else {
      console.log('❌ Result missing expected properties');
    }
    
    if (result.sentinel === NO_WAITLISTS_SENTINEL) {
      console.log('✅ Sentinel value is correct');
    } else {
      console.log('❌ Sentinel value mismatch');
    }
    
  } catch (error) {
    console.log('❌ returnToDefault failed:', error.toString());
  }
  
  console.log('Live test completed - check your form to verify only sentinel option remains');
}

function testValidateIncomingData() {
  console.log('=== Testing validateIncomingData ===');
  
  // Test valid data
  try {
    validateIncomingData({ productUrl: 'https://example.com', sport: 'Dodgeball' });
    console.log('✅ Valid data accepted');
  } catch (error) {
    console.log('❌ Valid data rejected:', error.toString());
  }
  
  // Test missing productUrl
  try {
    validateIncomingData({ sport: 'Dodgeball' });
    console.log('❌ Missing productUrl accepted (should fail)');
  } catch (error) {
    console.log('✅ Missing productUrl rejected:', error.toString());
  }
  
  // Test empty productUrl
  try {
    validateIncomingData({ productUrl: '', sport: 'Dodgeball' });
    console.log('❌ Empty productUrl accepted (should fail)');
  } catch (error) {
    console.log('✅ Empty productUrl rejected:', error.toString());
  }
  
  // Test missing all other fields
  try {
    validateIncomingData({ productUrl: 'https://example.com' });
    console.log('❌ Missing all fields accepted (should fail)');
  } catch (error) {
    console.log('✅ Missing all fields rejected:', error.toString());
  }
  
  console.log('validateIncomingData tests completed');
}

function runAllTests() {
  testCreateFormattedLabel();
  console.log('');
  testSortWaitlistOptions(); 
  console.log('');
  testParseLabelForSorting();
  console.log('');
  testValidateIncomingData();
  console.log('');
  testReturnToDefault();
  console.log('');
  console.log('All tests completed!');
}
