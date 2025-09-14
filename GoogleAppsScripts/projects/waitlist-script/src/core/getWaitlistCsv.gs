/**
 * Local test function to fetch waitlist data from Google Sheets
 * This helps debug data access issues without deploying to web app
 */
function getWaitlistCsv() {
  try {
    console.log("🚀 Starting getWaitlistCsv...");

    // Sheet ID extracted from your URL
    const SHEET_ID = "1rrmEu6QKNnDoNJs2XnAD08W-7smUhFPKYnNC5y7iNI0";
    const GID = "1214906876"; // The specific sheet/tab ID

    console.log(`📊 Accessing sheet: ${SHEET_ID}`);
    console.log(`📋 Tab GID: ${GID}`);

    // Open the spreadsheet
    const spreadsheet = SpreadsheetApp.openById(SHEET_ID);
    console.log(`✅ Opened spreadsheet: ${spreadsheet.getName()}`);

    // Get all sheets to find the right one
    const sheets = spreadsheet.getSheets();
    console.log(`📄 Available sheets: ${sheets.map(s => `"${s.getName()}" (ID: ${s.getSheetId()})`).join(', ')}`);

    // Find the sheet with matching GID
    let targetSheet = null;
    for (const sheet of sheets) {
      if (sheet.getSheetId().toString() === GID) {
        targetSheet = sheet;
        break;
      }
    }

    if (!targetSheet) {
      // If we can't find by GID, try the first sheet
      targetSheet = sheets[0];
      console.log(`⚠️ Could not find sheet with GID ${GID}, using first sheet: "${targetSheet.getName()}"`);
    } else {
      console.log(`🎯 Found target sheet: "${targetSheet.getName()}"`);
    }

    // Get all data
    const dataRange = targetSheet.getDataRange();
    const numRows = dataRange.getNumRows();
    const numCols = dataRange.getNumColumns();

    console.log(`📏 Sheet dimensions: ${numRows} rows x ${numCols} columns`);

    if (numRows === 0) {
      console.log("❌ No data found in sheet");
      return { success: false, error: "No data found" };
    }

    // Get the data
    const values = dataRange.getValues();

    console.log(`📊 Retrieved ${values.length} rows of data`);
    console.log(`🔤 Headers: ${values[0].join(' | ')}`);

    // Show first few data rows (excluding header)
    if (values.length > 1) {
      console.log("📝 First few data rows:");
      for (let i = 1; i <= Math.min(3, values.length - 1); i++) {
        console.log(`   Row ${i}: ${values[i].slice(0, 3).join(' | ')}...`);
      }
    }

    // Look for a specific test email
    const testEmail = "jdazz87@gmail.com";
    let foundRows = [];

    // Find email column (should be column 1 based on headers)
    const headers = values[0];
    const emailColIndex = headers.findIndex(header =>
      header.toLowerCase().includes('email')
    );

    console.log(`📧 Email column index: ${emailColIndex}`);

    if (emailColIndex >= 0) {
      for (let i = 1; i < values.length; i++) {
        if (values[i][emailColIndex] === testEmail) {
          foundRows.push({
            rowNumber: i + 1,
            data: values[i]
          });
        }
      }

      console.log(`🔍 Found ${foundRows.length} rows with email "${testEmail}"`);
      foundRows.forEach(row => {
        console.log(`   Row ${row.rowNumber}: ${row.data.slice(0, 6).join(' | ')}...`);
      });
    }

    return {
      success: true,
      totalRows: values.length,
      headers: values[0],
      sampleData: values.slice(1, 4), // First 3 data rows
      testEmailRows: foundRows,
      sheetName: targetSheet.getName()
    };

  } catch (error) {
    console.error("💥 Error in getWaitlistCsv:", error);
    console.error("📍 Error stack:", error.stack);

    return {
      success: false,
      error: error.message,
      stack: error.stack
    };
  }
}

/**
 * Test function to run getWaitlistCsv and display results
 */
function testGetWaitlistCsv() {
  console.log("🧪 Testing getWaitlistCsv function...");

  const result = getWaitlistCsv();

  if (result.success) {
    console.log("✅ SUCCESS!");
    console.log(`📊 Total rows: ${result.totalRows}`);
    console.log(`📄 Sheet name: ${result.sheetName}`);
    console.log(`🔤 Headers: ${result.headers.join(' | ')}`);
    console.log(`🔍 Test email rows found: ${result.testEmailRows.length}`);
  } else {
    console.log("❌ FAILED!");
    console.log(`💥 Error: ${result.error}`);
  }

  return result;
}
