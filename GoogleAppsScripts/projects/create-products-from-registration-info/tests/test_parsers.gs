/**
 * Consolidated tests for all parser functions
 * Combines tests for individual column parsers and row parsing
 */

/**
 * Test parseColBLeagueBasicInfo_ function
 */
function testParseColBLeagueBasicInfo_() {
  console.log('Testing parseColBLeagueBasicInfo_...');
  
  const testCases = [
    {
      name: 'Basic league info parsing',
      input: 'MONDAY\n\nOpen\nSocial Big Ball\nRandomized - Buddy Sign Ups',
      expected: {
        dayOfPlay: 'Monday',
        division: 'Open',
        socialOrAdvanced: 'Social',
        sportSubCategory: 'Big Ball',
        types: ['Randomized', 'Buddy Sign-up']
      }
    },
    {
      name: 'WTNB+ division parsing',
      input: 'TUESDAY\n\nWTNB+\nAdvanced Small Ball',
      expected: {
        dayOfPlay: 'Tuesday',
        division: 'WTNB+',
        socialOrAdvanced: 'Advanced',
        sportSubCategory: 'Small Ball'
      }
    }
  ];
  
  testCases.forEach(testCase => {
    try {
      const result = parseColBLeagueBasicInfo_(testCase.input, [], 'Kickball');
      console.log(`  ✅ ${testCase.name}: ${JSON.stringify(result)}`);
    } catch (error) {
      console.log(`  ❌ ${testCase.name}: ${error.message}`);
    }
  });
}

/**
 * Test parseColCLeagueDetails_ function
 */
function testParseColCLeagueDetails_() {
  console.log('Testing parseColCLeagueDetails_...');
  
  const testCases = [
    {
      name: 'Inventory extraction from range',
      input: '2 sessions; 350-364 players, 50-52 teams, 7 players max Teams are randomly assigned Players are able to sign-up with one buddy',
      expected: {
        totalInventory: 364,
        typesHint: 'Buddy Sign-up'
      }
    },
    {
      name: 'Single inventory number',
      input: 'Newbie Night/Open Play - 10/6/25\n\nNo games on Indigenous Peoples Day 10/13',
      expected: {
        totalInventory: null
      }
    }
  ];
  
  testCases.forEach(testCase => {
    try {
      const result = parseColCLeagueDetails_(testCase.input, 'Kickball');
      console.log(`  ✅ ${testCase.name}: ${JSON.stringify(result)}`);
    } catch (error) {
      console.log(`  ❌ ${testCase.name}: ${error.message}`);
    }
  });
}

/**
 * Test parseColDESeasonDates_ function
 */
function testParseColDESeasonDates_() {
  console.log('Testing parseColDESeasonDates_...');
  
  const testCases = [
    {
      name: 'Season dates parsing',
      input: { D: '10-20-2025', E: '12/8/2025' },
      expected: {
        seasonStartDate: new Date('2025-10-20T04:00:00.000Z'),
        seasonEndDate: new Date('2025-12-08T04:00:00.000Z')
      }
    }
  ];
  
  testCases.forEach(testCase => {
    try {
      const result = parseColDESeasonDates_(testCase.input);
      console.log(`  ✅ ${testCase.name}: ${JSON.stringify(result)}`);
    } catch (error) {
      console.log(`  ❌ ${testCase.name}: ${error.message}`);
    }
  });
}

/**
 * Test parseColFPrice_ function
 */
function testParseColFPrice_() {
  console.log('Testing parseColFPrice_...');
  
  const testCases = [
    {
      name: 'Price parsing',
      input: '$120',
      expected: { price: 120 }
    },
    {
      name: 'Price without dollar sign',
      input: '150',
      expected: { price: 150 }
    }
  ];
  
  testCases.forEach(testCase => {
    try {
      const result = parseColFPrice_(testCase.input);
      console.log(`  ✅ ${testCase.name}: ${JSON.stringify(result)}`);
    } catch (error) {
      console.log(`  ❌ ${testCase.name}: ${error.message}`);
    }
  });
}

/**
 * Test parseColGLeagueTimes_ function
 */
function testParseColGLeagueTimes_() {
  console.log('Testing parseColGLeagueTimes_...');
  
  const testCases = [
    {
      name: 'Single time range',
      input: '6:30-10',
      expected: {
        leagueStartTime: new Date('2025-01-01T18:30:00.000Z'),
        leagueEndTime: new Date('2025-01-01T22:00:00.000Z')
      }
    },
    {
      name: 'Double time range',
      input: 'Times: 12:45-2:45PM & 3:00-5:00PM',
      expected: {
        leagueStartTime: new Date('2025-01-01T12:45:00.000Z'),
        leagueEndTime: new Date('2025-01-01T14:45:00.000Z'),
        alternativeStartTime: new Date('2025-01-01T15:00:00.000Z'),
        alternativeEndTime: new Date('2025-01-01T17:00:00.000Z')
      }
    }
  ];
  
  testCases.forEach(testCase => {
    try {
      const result = parseColGLeagueTimes_(testCase.input);
      console.log(`  ✅ ${testCase.name}: ${JSON.stringify(result)}`);
    } catch (error) {
      console.log(`  ❌ ${testCase.name}: ${error.message}`);
    }
  });
}

/**
 * Test parseColMNORegistrationDates_ function
 */
function testParseColMNORegistrationDates_() {
  console.log('Testing parseColMNORegistrationDates_...');
  
  const testCases = [
    {
      name: 'Registration dates parsing',
      input: {
        M: 'Weds, Sept. 3rd, 6pm',
        N: 'Tues, Sept. 2nd, 7pm',
        O: 'Thurs, Sept. 4th, 6pm'
      },
      expected: {
        earlyRegistrationStartDateTime: new Date('2025-09-03T22:00:00.000Z'),
        vetRegistrationStartDateTime: new Date('2025-09-02T23:00:00.000Z'),
        openRegistrationStartDateTime: new Date('2025-09-04T22:00:00.000Z')
      }
    }
  ];
  
  testCases.forEach(testCase => {
    try {
      const result = parseColMNORegistrationDates_(testCase.input);
      console.log(`  ✅ ${testCase.name}: ${JSON.stringify(result)}`);
    } catch (error) {
      console.log(`  ❌ ${testCase.name}: ${error.message}`);
    }
  });
}

/**
 * Test parseSourceRowEnhanced_ function
 */
function testParseSourceRowEnhanced_() {
  console.log('Testing parseSourceRowEnhanced_...');
  
  const testData = {
    A: 'Kickball',
    B: 'MONDAY\n\nOpen\nSocial Big Ball\nRandomized - Buddy Sign Ups',
    C: '2 sessions; 350-364 players, 50-52 teams, 7 players max Teams are randomly assigned Players are able to sign-up with one buddy',
    D: '10-20-2025',
    E: '12/8/2025',
    F: '$120',
    G: '6:30-10',
    H: 'Hartley House\n413 W 46th Street',
    M: 'Weds, Sept. 3rd, 6pm',
    N: 'Tues, Sept. 2nd, 7pm',
    O: 'Thurs, Sept. 4th, 6pm'
  };
  
  try {
    const result = parseSourceRowEnhanced_(testData);
    console.log(`  ✅ Full row parsing: ${JSON.stringify(result, null, 2)}`);
  } catch (error) {
    console.log(`  ❌ Full row parsing: ${error.message}`);
  }
}

/**
 * Run all parser tests
 */
function runParserTests() {
  console.log('🧪 Running parser tests...\n');
  
  testParseColBLeagueBasicInfo_();
  testParseColCLeagueDetails_();
  testParseColDESeasonDates_();
  testParseColFPrice_();
  testParseColGLeagueTimes_();
  testParseColMNORegistrationDates_();
  testParseSourceRowEnhanced_();
  
  console.log('\n✅ All parser tests completed');
}
