/**
 * Integration tests for parseSourceRowEnhanced_ function
 * Tests the complete row parsing logic with real-world data
 *
 * @fileoverview Integration tests for row parsing functionality
 * @requires ../src/parsers/_rowParser.gs
 */

/**
 * Integration Test: parseSourceRowEnhanced with realistic Pickleball data
 * Tests the complete parsing pipeline from raw spreadsheet data to structured payload
 */
function testParseSourceRowEnhanced() {
  Logger.log('Running Integration Test: parseSourceRowEnhanced with Pickleball data');

  try {
    // Test data matching the user's specification exactly
    // Convert array to object format expected by parseSourceRowEnhanced_
    const testRowData = {
      A: "PICKLEBALL",                                    // A: Sport Name
      B: `TUESDAY

Open
Competitive/Advanced
Buddy-Sign Up`,                                      // B: Day and League Details
      C: `Total # of Weeks: 9
Regular Season: 8 weeks
Tournament Date:
Closing Party: Date TBD

Skipping 11/25
Tournament Date: Dec 9

# of Teams: 16
# of Players: 64 (4 players per team)

All teams play two 45 min matches per night`,        // C: League Details and Notes
      D: "Oct 14th",                                     // D: Season Start Date
      E: "12/9/2025",                                    // E: Season End Date
      F: "150",                                          // F: Price
      G: "8-11pm",                                       // G: Play Times
      H: "Gotham Pickleball",                           // H: Location
      I: "pickleball.advanced@bigapplerecsports.com",   // I: League Email
      J: "6/8 attendance from Summer 2025",             // J: Notes/Requirements
      K: "",                                             // K: (empty)
      L: "",                                             // L: (empty)
      M: "Sept 16th 7PM",                               // M: Early Registration
      N: `Sept 15th 7PM

Only holding 40 vet spots`,                         // N: Vet Registration
      O: "Sept 17th 7PM"                                // O: Open Registration
    };

    // Expected result structure based on user specification
    const expectedResult = {
      sportName: "Pickleball",
      division: "Open",
      season: "Fall",
      year: "2025",
      dayOfPlay: "Tuesday",
      location: "Gotham Pickleball (46th and Vernon in LIC)",
      optionalLeagueInfo: {
        socialOrAdvanced: "Advanced"
      },
      importantDates: {
        seasonStartDate: new Date("2025-10-15T04:00:00Z"),
        seasonEndDate: new Date("2025-12-10T04:00:00Z"),
        offDates: [new Date('2025-11-25T04:00:00Z')],
        closingPartyDate: "TBD",
        vetRegistrationStartDateTime: new Date("2025-09-15T23:00:00Z"),
        earlyRegistrationStartDateTime: new Date("2025-09-16T23:00:00Z"),
        openRegistrationStartDateTime: new Date("2025-09-17T23:00:00Z")
      },
      leagueStartTime: "8:00 PM",
      leagueEndTime: "11:00 PM",
      inventoryInfo: {
        price: 150,
        totalInventory: 64,
        numberVetSpotsToReleaseAtGoLive: 40
      }
    };

    Logger.log('📋 Input test data:');
    Logger.log(`  A (Sport): "${testRowData.A}"`);
    Logger.log(`  B (Day/Details): "${testRowData.B}"`);
    Logger.log(`  C (Notes): "${testRowData.C}"`);
    Logger.log(`  D (Start): "${testRowData.D}"`);
    Logger.log(`  E (End): "${testRowData.E}"`);
    Logger.log(`  F (Price): "${testRowData.F}"`);
    Logger.log(`  G (Times): "${testRowData.G}"`);
    Logger.log(`  H (Location): "${testRowData.H}"`);
    Logger.log(`  M (Early Reg): "${testRowData.M}"`);
    Logger.log(`  N (Vet Reg): "${testRowData.N}"`);
    Logger.log(`  O (Open Reg): "${testRowData.O}"`);

    // Call the actual parseSourceRowEnhanced_ function
    Logger.log('🚀 Calling parseSourceRowEnhanced_...');
    const {parsed: actualResult} = parseSourceRowEnhanced_(testRowData);

    Logger.log('📤 Actual result:');
    Logger.log(JSON.stringify(actualResult, null, 2));

    Logger.log('📥 Expected result:');
    Logger.log(JSON.stringify(expectedResult, null, 2));

    // Detailed comparison logging
    Logger.log('🔍 Detailed field comparison:');

    // Top-level fields
    const topLevelFields = ['sportName', 'division', 'season', 'year', 'dayOfPlay', 'location', 'leagueStartTime', 'leagueEndTime'];
    let hasTopLevelErrors = false;

    for (const field of topLevelFields) {
      const actual = actualResult[field];
      const expected = expectedResult[field];
      const match = actual === expected;

      if (!match) hasTopLevelErrors = true;

      Logger.log(`  ${match ? '✅' : '❌'} ${field}: actual="${actual}" expected="${expected}"`);
    }

    // Optional league info
    Logger.log('  📋 optionalLeagueInfo:');
    let hasOptionalLeagueErrors = false;
    if (actualResult.optionalLeagueInfo && expectedResult.optionalLeagueInfo) {
      for (const field in expectedResult.optionalLeagueInfo) {
        const actual = actualResult.optionalLeagueInfo[field];
        const expected = expectedResult.optionalLeagueInfo[field];
        const match = actual === expected;

        if (!match) hasOptionalLeagueErrors = true;

        Logger.log(`    ${match ? '✅' : '❌'} ${field}: actual="${actual}" expected="${expected}"`);
      }
    } else {
      hasOptionalLeagueErrors = true;
      Logger.log(`    ❌ optionalLeagueInfo structure missing or incomplete`);
    }

    // Important dates
    Logger.log('  📅 importantDates:');
    let hasDateErrors = false;
    if (actualResult.importantDates && expectedResult.importantDates) {
      for (const field in expectedResult.importantDates) {
        const actual = actualResult.importantDates[field];
        const expected = expectedResult.importantDates[field];

        let match = false;
        if (expected instanceof Date && actual instanceof Date) {
          match = actual.getTime() === expected.getTime();
        } else if (Array.isArray(expected) && Array.isArray(actual)) {
          // Compare arrays (for offDates)
          match = expected.length === actual.length &&
                  expected.every((expectedItem, index) => {
                    const actualItem = actual[index];
                    if (expectedItem instanceof Date && actualItem instanceof Date) {
                      return expectedItem.getTime() === actualItem.getTime();
                    }
                    return expectedItem === actualItem;
                  });
        } else {
          match = actual === expected;
        }

        if (!match) hasDateErrors = true;

        let actualStr, expectedStr;
        if (Array.isArray(actual)) {
          actualStr = `[${actual.map(item => item instanceof Date ? item.toISOString() : item).join(', ')}]`;
        } else if (actual instanceof Date) {
          actualStr = actual.toISOString();
        } else {
          actualStr = actual;
        }

        if (Array.isArray(expected)) {
          expectedStr = `[${expected.map(item => item instanceof Date ? item.toISOString() : item).join(', ')}]`;
        } else if (expected instanceof Date) {
          expectedStr = expected.toISOString();
        } else {
          expectedStr = expected;
        }
        Logger.log(`    ${match ? '✅' : '❌'} ${field}: actual="${actualStr}" expected="${expectedStr}"`);
      }
    } else {
      hasDateErrors = true;
      Logger.log(`    ❌ importantDates structure missing or incomplete`);
    }

    // Inventory info
    Logger.log('  📦 inventoryInfo:');
    let hasInventoryErrors = false;
    if (actualResult.inventoryInfo && expectedResult.inventoryInfo) {
      for (const field in expectedResult.inventoryInfo) {
        const actual = actualResult.inventoryInfo[field];
        const expected = expectedResult.inventoryInfo[field];
        const match = actual === expected;

        if (!match) hasInventoryErrors = true;

        Logger.log(`    ${match ? '✅' : '❌'} ${field}: actual="${actual}" expected="${expected}"`);
      }
    } else {
      hasInventoryErrors = true;
      Logger.log(`    ❌ inventoryInfo structure missing or incomplete`);
    }

    // Overall test result
    const hasAnyErrors = hasTopLevelErrors || hasOptionalLeagueErrors || hasDateErrors || hasInventoryErrors;

    if (hasAnyErrors) {
      Logger.log('❌ Integration test FAILED: parseSourceRowEnhanced produces different results than expected');
      Logger.log('ℹ️ This is expected until parsing logic is updated to match the new requirements');
      return false;
    } else {
      Logger.log('✅ Integration test PASSED: parseSourceRowEnhanced matches expected output exactly');
      return true;
    }

  } catch (error) {
    Logger.log(`❌ Integration test ERROR: ${error.message}`);
    Logger.log(`Stack trace: ${error.stack}`);
    return false;
  }
}

/**
 * Helper function to run the integration test
 * Provides backward compatibility and easy access
 */
function runParseSourceRowEnhancedTest() {
  return testParseSourceRowEnhanced();
}

/**
 * Alternative entry point for test runner consistency
 */
function runTestParseSourceRowEnhanced() {
  return testParseSourceRowEnhanced();
}
