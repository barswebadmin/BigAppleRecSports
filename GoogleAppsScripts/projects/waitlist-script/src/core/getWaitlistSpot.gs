
/**
 * Get all leagues that an email appears in the waitlist for
 * Returns: {leagues: [{league: "League Name", spot: 1}, ...], debugLog: [...]}
 */
function getAllLeaguesForEmail(email) {
  const debugLog = [];
  debugLog.push(`🔍 Getting all leagues for email: ${email}`);

  try {
    // Use the same method as getWaitlistSpot
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    const values = sheet.getDataRange().getValues();
    const headers = values[0];
    const dataRows = values.slice(1);

    debugLog.push(`📊 Found ${dataRows.length} total rows`);

    // Find column indices - use same logic as getWaitlistSpot
    const emailCol = headers.findIndex(h => h.toLowerCase().includes("email address"));
    const leagueCol = headers.findIndex(h => h.toLowerCase().includes("please select the league you want to sign up for"));
    const notesCol = headers.findIndex(h => h.toLowerCase().includes("notes"));

    if (emailCol === -1 || leagueCol === -1) {
      debugLog.push(`❌ Required columns not found. Email col: ${emailCol}, League col: ${leagueCol}`);
      return { leagues: [], debugLog };
    }

    debugLog.push(`📍 Column indices - Email: ${emailCol}, League: ${leagueCol}, Notes: ${notesCol}`);

    // Find all leagues for this email and track first occurrence
    const leagueData = new Map(); // league -> {spot: number, firstRowIndex: number}
    let matchingRows = 0;

    dataRows.forEach((row, index) => {
      const rowEmail = row[emailCol];
      const rowLeague = row[leagueCol];

      // Skip processed or canceled rows
      const notesVal = (row[notesCol] || "").toLowerCase();
      if (notesVal.includes("processed") || notesVal.includes("canceled")) return;

      if (rowEmail && rowEmail.toLowerCase().trim() === email.toLowerCase().trim()) {
        matchingRows++;

        if (rowLeague && rowLeague.trim()) {
          let league = rowLeague;

          // Handle league field - might be an array
          if (Array.isArray(rowLeague)) {
            league = rowLeague.filter(val => val && val.toString().trim()).pop() || "";
          }
          league = league.toString().trim();

          // Only keep the first occurrence of each email/league combination
          if (league && !leagueData.has(league)) {
            // Calculate position for this league
            let earlierCount = 0;
            for (let i = 0; i <= index; i++) {
              const checkRow = dataRows[i];
              const checkEmail = checkRow[emailCol];
              let checkLeague = checkRow[leagueCol];

              // Skip processed or canceled rows in position calculation too
              const checkNotesVal = (checkRow[notesCol] || "").toLowerCase();
              if (checkNotesVal.includes("processed") || checkNotesVal.includes("canceled")) continue;

              if (Array.isArray(checkLeague)) {
                checkLeague = checkLeague.filter(val => val && val.toString().trim()).pop() || "";
              }
              checkLeague = checkLeague ? checkLeague.toString().trim() : "";

              if (checkLeague === league &&
                  checkEmail && checkEmail.toLowerCase().trim() !== email.toLowerCase().trim()) {
                earlierCount++;
              }
            }

            leagueData.set(league, {
              spot: earlierCount + 1,
              firstRowIndex: index
            });

            debugLog.push(`✅ Found league "${league}" - Position: ${earlierCount + 1}`);
          }
        }
      }
    });

    debugLog.push(`🎯 Found ${matchingRows} total rows for email, ${leagueData.size} unique leagues`);

    // Convert to array format
    const leagues = Array.from(leagueData.entries()).map(([league, data]) => ({
      league: league,
      spot: data.spot
    }));

    return { leagues, debugLog };

  } catch (error) {
    debugLog.push(`💥 Error in getAllLeaguesForEmail: ${error.message}`);
    return { leagues: [], debugLog, error: error.message };
  }
}

function getWaitlistSpot(email, league, timestampStr = null, debugLog = []) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const header = data[0];

  const normalize = val => val?.toString().trim().toLowerCase();
  const timestampCol = 0;
  const emailCol = header.findIndex(h => h.toLowerCase().includes("email address"));
  const leagueCol = header.findIndex(h => h.toLowerCase().includes("please select the league you want to sign up for"));
  const notesCol = header.findIndex(h => h.toLowerCase().includes("notes"));
  debugLog.push(`Looking for:`);
  debugLog.push(`email: ${email}`);
  debugLog.push(`league: ${league}`);
  if (timestampStr) {
    try {
      const submittedTimestamp = new Date(timestampStr);
      debugLog.push(`timestamp: ${submittedTimestamp.toISOString()}`);
    } catch (error) {
      debugLog.push(`timestamp: ${timestampStr} (invalid - ignoring)`);
    }
  } else {
    debugLog.push(`timestamp: not provided (not needed for matching)`);
  }
  debugLog.push(`emailCol: ${emailCol}, leagueCol: ${leagueCol}, notesCol: ${notesCol}`);

  // 🔍 DEBUG: Show all available column headers
  debugLog.push(`All column headers:`);
  header.forEach((h, i) => {
    debugLog.push(`  Column ${i}: "${h}"`);
  });

  // 🔍 DEBUG: Try different league column searches
  const leagueCol2 = header.findIndex(h => h.toLowerCase().includes("season"));
  const leagueCol3 = header.findIndex(h => h.toLowerCase().includes("league"));
  debugLog.push(`Alternative league columns: season=${leagueCol2}, league=${leagueCol3}`);

  let foundIndex = -1;
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const notesVal = (row[notesCol] || "").toLowerCase();
    if (notesVal.includes("processed") || notesVal.includes("canceled")) continue;

    const rowEmail = normalize(row[emailCol]);

    // 🔍 DEBUG: Show raw league data for first few rows
    if (i <= 3) {
      debugLog.push(`Row ${i} raw league data (col ${leagueCol}): ${JSON.stringify(row[leagueCol])}`);
    }

    // Handle league field - might be a string or need special processing
    let rowLeague = row[leagueCol];
    if (Array.isArray(rowLeague)) {
      // If it's an array, get the last non-empty value
      rowLeague = rowLeague.filter(val => val && val.toString().trim()).pop() || "";
    }
    rowLeague = normalize(rowLeague);
    const rowTimestamp = new Date(row[timestampCol]);

    // Only log first few rows to avoid spam
    if (i <= 3) {
      debugLog.push(`Row ${i}: email=${rowEmail}, league=${rowLeague}, timestamp=${rowTimestamp.toISOString()}`);
    }

    // Match only on email and league (no timestamp checking)
    if (
      rowEmail === normalize(email) &&
      rowLeague === normalize(league)
    ) {
      foundIndex = i;
      debugLog.push(`✅ MATCH FOUND at row ${i}: email=${rowEmail}, league=${rowLeague}`);
      break;
    }
  }

  if (foundIndex === -1) return { found: false };

  const userTime = new Date(data[foundIndex][timestampCol]);
  let spot = 1;

  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const notesVal = (row[notesCol] || "").toLowerCase();
    if (notesVal.includes("processed") || notesVal.includes("canceled")) continue;

    // Handle league field - might be a string or need special processing
    let thisLeague = row[leagueCol];
    if (Array.isArray(thisLeague)) {
      // If it's an array, get the last non-empty value
      thisLeague = thisLeague.filter(val => val && val.toString().trim()).pop() || "";
    }
    thisLeague = normalize(thisLeague);
    const thisTimestamp = new Date(row[timestampCol]);

    if (thisLeague === normalize(league) && thisTimestamp < userTime) {
      spot++;
    }
  }

  debugLog.push(`✅ Found row index: ${foundIndex}`);
  debugLog.push(`Computed spot: #${spot}`);

  return { found: true, spot };
}

function sendDebugEmail(debugLog, e) {
  const emailBody = `
    <h3>⚠️ Waitlist Debug - Could Not Match</h3>
    <p>Here are the diagnostics from the doGet call:</p>
    <pre>${debugLog.join("\n")}</pre>
    <h4>Raw Query Params:</h4>
    <pre>${JSON.stringify(e.parameter, null, 2)}</pre>
  `;

  MailApp.sendEmail({
    to: DEBUG_EMAIL,
    subject: "❌ Waitlist Spot Debug Failure",
    htmlBody: emailBody
  });
}

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
 * Debug function to check what URL ScriptApp.getService().getUrl() returns
 * This helps debug web app deployment issues
 */
function checkWebAppUrl() {
  console.log("🔍 === WEB APP URL CHECK ===");

  try {
    const currentUrl = ScriptApp.getService().getUrl();
    console.log(`📍 Current ScriptApp.getService().getUrl(): ${currentUrl}`);

    // Test if the URL is accessible
    console.log("🧪 Testing URL accessibility...");

    // Create a test URL with dummy parameters
    const testUrl = `${currentUrl}?email=test@example.com&league=Test League`;
    console.log(`🔗 Test URL would be: ${testUrl}`);

    // Check if this looks like a proper web app URL
    if (currentUrl && currentUrl.includes('script.google.com/macros/s/') && currentUrl.endsWith('/exec')) {
      console.log("✅ URL format looks correct for a web app deployment");
    } else {
      console.log("❌ URL format does NOT look like a web app deployment");
      console.log("💡 This might explain why the links don't work!");
    }

  } catch (error) {
    console.log(`❌ Error getting web app URL: ${error.message}`);
    console.log(`📍 Stack trace: ${error.stack}`);
  }

  console.log("🏁 === WEB APP URL CHECK COMPLETE ===");
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
