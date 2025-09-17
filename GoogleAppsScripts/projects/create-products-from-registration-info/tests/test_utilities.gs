/**
 * Consolidated tests for utility functions
 * Combines tests for formatting, validation, date parsing, and constants
 */

/**
 * Test format validators
 */
function testFormatValidators() {
  console.log('Testing format validators...');
  
  try {
    // Test date validation
    const validDate = isDateMMDDYYYY_('10/15/2025');
    const invalidDate = isDateMMDDYYYY_('2025/10/15');
    console.log(`  ✅ Date validation: ${validDate === true && invalidDate === false}`);
    
    // Test time validation
    const validTime = isTime12h_('8:00 PM');
    const invalidTime = isTime12h_('20:00');
    console.log(`  ✅ Time validation: ${validTime === true && invalidTime === false}`);
    
    // Test time range validation
    const validRange = isTimeRange12h_('8:00 PM - 11:00 PM');
    const invalidRange = isTimeRange12h_('8 PM - 11 PM');
    console.log(`  ✅ Time range validation: ${validRange === true && invalidRange === false}`);
    
    // Test ISO 8601 validation
    const validISO = isISO8601_('2025-09-17T23:00:00Z');
    const invalidISO = isISO8601_('2025-09-17 23:00');
    console.log(`  ✅ ISO validation: ${validISO === true && invalidISO === false}`);
    
    // Test datetime validation
    const validDateTime = isDateTimeAllowed_('2025-09-17T23:00:00Z');
    const validDateTime2 = isDateTimeAllowed_('09/17/2025 11:00 PM');
    const invalidDateTime = isDateTimeAllowed_('invalid');
    console.log(`  ✅ DateTime validation: ${validDateTime === true && validDateTime2 === true && invalidDateTime === false}`);
    
  } catch (error) {
    console.log(`  ❌ Format validators: ${error.message}`);
  }
}

/**
 * Test date formatting functions
 */
function testDateFormatting() {
  console.log('Testing date formatting...');
  
  const testDate = new Date('2025-10-15T14:30:00Z');
  
  try {
    const mdYY = formatDateMdYY_(testDate);
    const mdYYhm = formatDateTimeMdYYhm_(testDate);
    const sheetDate = formatDateForSheet_(testDate);
    const sheetDateTime = formatDateTimeForSheet_(testDate);
    const sheetTime = formatTimeForSheet_(testDate);
    const displayDateTime = formatDateTimeForDisplay_(testDate);
    
    console.log(`  ✅ M/d/yy format: ${mdYY === '10/15/25'}`);
    console.log(`  ✅ M/d/yy h:mm AM/PM format: ${mdYYhm === '10/15/25 2:30 PM'}`);
    console.log(`  ✅ Sheet date format: ${sheetDate === '10/15/2025'}`);
    console.log(`  ✅ Sheet datetime format: ${sheetDateTime === '10/15/2025 2:30 PM'}`);
    console.log(`  ✅ Sheet time format: ${sheetTime === '2:30 PM'}`);
    console.log(`  ✅ Display datetime format: ${displayDateTime === '10/15/25 at 2:30 PM'}`);
    
  } catch (error) {
    console.log(`  ❌ Date formatting: ${error.message}`);
  }
}

/**
 * Test value formatting
 */
function testValueFormatting() {
  console.log('Testing value formatting...');
  
  try {
    // Test price formatting
    const priceFormatted = formatValue(120, 'Price', 'price');
    console.log(`  ✅ Price formatting: ${priceFormatted === 'Price: $120'}`);
    
    // Test time formatting
    const timeFormatted = formatValue(new Date('2025-01-01T20:00:00Z'), 'Start Time', 'time');
    console.log(`  ✅ Time formatting: ${timeFormatted.includes('Start Time: 8:00 PM')}`);
    
    // Test datetime formatting
    const datetimeFormatted = formatValue(new Date('2025-10-15T14:30:00Z'), 'Registration', 'datetime');
    console.log(`  ✅ DateTime formatting: ${datetimeFormatted.includes('Registration: 10/15/25 2:30 PM')}`);
    
    // Test date formatting
    const dateFormatted = formatValue(new Date('2025-10-15T04:00:00Z'), 'Start Date', 'date');
    console.log(`  ✅ Date formatting: ${dateFormatted.includes('Start Date: 10/15/25')}`);
    
    // Test TBD handling
    const tbdFormatted = formatValue('TBD', 'End Date', 'date');
    console.log(`  ✅ TBD formatting: ${tbdFormatted === 'End Date: TBD'}`);
    
    // Test null handling
    const nullFormatted = formatValue(null, 'Missing Field', 'default');
    console.log(`  ✅ Null formatting: ${nullFormatted === 'Missing Field: [Not Found]'}`);
    
  } catch (error) {
    console.log(`  ❌ Value formatting: ${error.message}`);
  }
}

/**
 * Test date parsing functions
 */
function testDateParsing() {
  console.log('Testing date parsing...');
  
  try {
    // Test flexible date parsing
    const flexibleDate1 = parseFlexibleDate_('10/15/2025', false);
    const flexibleDate2 = parseFlexibleDate_('10/15/25', false);
    const flexibleDate3 = parseFlexibleDate_('10/15', false);
    
    console.log(`  ✅ Flexible date parsing: ${flexibleDate1 instanceof Date && flexibleDate2 instanceof Date && flexibleDate3 instanceof Date}`);
    
    // Test enhanced datetime parsing
    const enhancedDateTime1 = parseEnhancedDateTime_('2025-09-17T23:00:00Z');
    const enhancedDateTime2 = parseEnhancedDateTime_('09/17/2025 11:00 PM');
    
    console.log(`  ✅ Enhanced datetime parsing: ${enhancedDateTime1 instanceof Date && enhancedDateTime2 instanceof Date}`);
    
  } catch (error) {
    console.log(`  ❌ Date parsing: ${error.message}`);
  }
}

/**
 * Test constants and configuration
 */
function testConstants() {
  console.log('Testing constants...');
  
  try {
    // Test product field enums
    const sportNames = productFieldEnums.sportName;
    const divisions = productFieldEnums.division;
    const seasons = productFieldEnums.season;
    
    console.log(`  ✅ Sport names: ${Array.isArray(sportNames) && sportNames.includes('Kickball')}`);
    console.log(`  ✅ Divisions: ${Array.isArray(divisions) && divisions.includes('Open') && divisions.includes('WTNB+')}`);
    console.log(`  ✅ Seasons: ${Array.isArray(seasons) && seasons.includes('Fall')}`);
    
    // Test irrelevant fields for sport
    const kickballIrrelevant = irrelevantFieldsForSport.Kickball;
    const pickleballIrrelevant = irrelevantFieldsForSport.Pickleball;
    
    console.log(`  ✅ Kickball irrelevant fields: ${Array.isArray(kickballIrrelevant) && kickballIrrelevant.includes('sportSubCategory')}`);
    console.log(`  ✅ Pickleball irrelevant fields: ${Array.isArray(pickleballIrrelevant) && pickleballIrrelevant.includes('sportSubCategory')}`);
    
  } catch (error) {
    console.log(`  ❌ Constants: ${error.message}`);
  }
}

/**
 * Test unresolved fields calculation
 */
function testUnresolvedFields() {
  console.log('Testing unresolved fields calculation...');
  
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
    sportName: 'Kickball',
    dayOfPlay: 'Monday'
    // Missing many required fields
  };
  
  try {
    const completeUnresolved = calculateUnresolvedFieldsForParsedData(completeData);
    const incompleteUnresolved = calculateUnresolvedFieldsForParsedData(incompleteData);
    
    console.log(`  ✅ Complete data unresolved: ${completeUnresolved.length === 0}`);
    console.log(`  ✅ Incomplete data unresolved: ${incompleteUnresolved.length > 0}`);
    
  } catch (error) {
    console.log(`  ❌ Unresolved fields: ${error.message}`);
  }
}

/**
 * Run all utility tests
 */
function runUtilityTests() {
  console.log('🧪 Running utility tests...\n');
  
  testFormatValidators();
  testDateFormatting();
  testValueFormatting();
  testDateParsing();
  testConstants();
  testUnresolvedFields();
  
  console.log('\n✅ All utility tests completed');
}
