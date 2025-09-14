/**
 * WAITLIST DEBUG FUNCTIONS
 * These functions help diagnose issues with the "get your current position" web app
 * Run these manually from the Google Apps Script editor
 */

/**
 * Manual diagnostic function to test the current spreadsheet state
 * Run this from the script editor to see what's happening
 */
function diagnoseWaitlistIssues() {
  console.log("🔍 === WAITLIST DIAGNOSTIC STARTING ===");

  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    console.log(`📊 Active sheet name: ${sheet.getName()}`);

    const values = sheet.getDataRange().getValues();
    console.log(`📈 Total rows: ${values.length}`);

    if (values.length === 0) {
      console.log("❌ CRITICAL: Spreadsheet is empty!");
      return;
    }

    const headers = values[0];
    console.log(`📋 Column headers (${headers.length} columns):`);
    headers.forEach((h, i) => {
      console.log(`  Column ${i}: "${h}"`);
    });

    // Check for expected columns
    const emailCol = headers.findIndex(h => h.toLowerCase().includes("email address"));
    const leagueCol = headers.findIndex(h => h.toLowerCase().includes("please select the league you want to sign up for"));
    const notesCol = headers.findIndex(h => h.toLowerCase().includes("notes"));

    console.log(`🎯 Column Detection:`);
    console.log(`  Email column: ${emailCol} ${emailCol >= 0 ? '✅' : '❌'}`);
    console.log(`  League column: ${leagueCol} ${leagueCol >= 0 ? '✅' : '❌'}`);
    console.log(`  Notes column: ${notesCol} ${notesCol >= 0 ? '✅' : '❌'}`);

    if (emailCol === -1 || leagueCol === -1) {
      console.log("❌ CRITICAL: Required columns not found! This explains the failure.");
      console.log("💡 Suggestion: Check if the Google Form has been updated or if you're looking at the wrong sheet.");
    }

    // Show sample data if we have it
    if (values.length > 1) {
      console.log(`📝 Sample data (first 3 rows):`);
      for (let i = 1; i <= Math.min(3, values.length - 1); i++) {
        const row = values[i];
        console.log(`  Row ${i}: ${row.slice(0, Math.min(5, row.length)).join(' | ')}...`);
      }
    }

    // Test with a specific email if we have data
    if (values.length > 1 && emailCol >= 0) {
      const testEmail = values[1][emailCol]; // Use the first email in the sheet
      if (testEmail) {
        console.log(`🧪 Testing getAllLeaguesForEmail with first email: ${testEmail}`);
        const result = getAllLeaguesForEmail(testEmail);
        console.log(`📊 Test result: Found ${result.leagues ? result.leagues.length : 0} leagues`);
        if (result.error) {
          console.log(`❌ Test error: ${result.error}`);
        }
        if (result.debugLog) {
          console.log(`🔍 Debug log from test:`);
          result.debugLog.forEach(log => console.log(`    ${log}`));
        }
      }
    }

  } catch (error) {
    console.log(`💥 Error in diagnostic: ${error.message}`);
    console.log(`📍 Stack trace: ${error.stack}`);
  }

  console.log("🏁 === WAITLIST DIAGNOSTIC COMPLETE ===");
}

/**
 * Test function to simulate a doGet call with specific parameters
 * Use this to test the web app functionality manually
 */
function testDoGetWithParams(email = "test@example.com", league = "Test League") {
  console.log(`🧪 Testing doGet with email: ${email}, league: ${league}`);

  // Simulate the event parameter object that doGet receives
  const mockEvent = {
    parameter: {
      email: email,
      league: league
    }
  };

  try {
    const result = getAllLeaguesForEmail(email);
    console.log(`📊 getAllLeaguesForEmail result:`);
    console.log(`  Found leagues: ${result.leagues ? result.leagues.length : 0}`);
    console.log(`  Error: ${result.error || 'none'}`);

    if (result.debugLog) {
      console.log(`🔍 Debug log:`);
      result.debugLog.forEach(log => console.log(`    ${log}`));
    }

    if (result.leagues && result.leagues.length > 0) {
      console.log(`✅ Would show success page with leagues:`);
      result.leagues.forEach(league => {
        console.log(`    ${league.league}: Position #${league.spot}`);
      });
    } else {
      console.log(`❌ Would show error page: No leagues found`);
    }

  } catch (error) {
    console.log(`💥 Error simulating doGet: ${error.message}`);
    console.log(`📍 Stack trace: ${error.stack}`);
  }
}

/**
 * Quick test to see if the web app can access the spreadsheet
 */
function quickSpreadsheetTest() {
  console.log("🔍 === QUICK SPREADSHEET TEST ===");

  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    console.log(`✅ Sheet access: OK`);
    console.log(`📊 Sheet name: ${sheet.getName()}`);

    const range = sheet.getDataRange();
    console.log(`✅ Data range access: OK`);
    console.log(`📈 Rows: ${range.getNumRows()}, Columns: ${range.getNumColumns()}`);

    if (range.getNumRows() > 0) {
      const firstRow = sheet.getRange(1, 1, 1, range.getNumColumns()).getValues()[0];
      console.log(`✅ First row data: OK`);
      console.log(`📋 Headers: ${firstRow.join(' | ')}`);
    }

    console.log("✅ Basic spreadsheet access is working!");

  } catch (error) {
    console.log(`❌ Spreadsheet access error: ${error.message}`);
    console.log(`📍 This might explain why the web app fails`);
  }

  console.log("🏁 === QUICK TEST COMPLETE ===");
}
