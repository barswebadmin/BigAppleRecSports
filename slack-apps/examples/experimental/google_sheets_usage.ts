#!/usr/bin/env deno run --allow-net --allow-env --allow-read

import { firebaseClient } from "@bars/firebase";
import { googleClient } from "@bars/google";
import { getAdminUserEmail } from "@bars/shared/config/environment.ts";

/**
 * Comprehensive examples of Google Sheets operations using the new client architecture
 */

async function demonstrateGoogleSheets() {
  console.log("📊 Google Sheets Integration Examples\n");

  const adminEmail = getAdminUserEmail();

  // Example spreadsheet ID (replace with your actual ID)
  const EXAMPLE_SPREADSHEET_ID = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms";

  try {
    console.log("1. Reading from Google Sheets...");

    // Get authenticated Sheets client
    const sheets = await googleClient.sheets(adminEmail);

    // Read data from a sheet
    const response = await sheets.spreadsheets.values.get({
      spreadsheetId: EXAMPLE_SPREADSHEET_ID,
      range: "Class Data!A2:E", // Skip header row
    });

    const data = response.data.values || [];
    console.log(`   ✅ Read ${data.length} rows from Google Sheets`);
    console.log(`   📋 Sample data:`, data.slice(0, 2)); // Show first 2 rows

    console.log("\n2. Writing to Google Sheets...");

    // Write new data to a sheet
    const testData = [
      ["Player Name", "League", "Position", "Email", "Status"],
      ["John Doe", "Spring Basketball", "1", "john@example.com", "Active"],
      ["Jane Smith", "Spring Basketball", "2", "jane@example.com", "Waitlist"]
    ];

    await sheets.spreadsheets.values.update({
      spreadsheetId: EXAMPLE_SPREADSHEET_ID,
      range: "Test Data!A1:E3",
      valueInputOption: 'RAW',
      requestBody: {
        values: testData,
      },
    });

    console.log("   ✅ Wrote test data to Google Sheets");

    console.log("\n3. Appending to Google Sheets...");

    // Append new entries to existing data
    const newEntries = [
      ["Bob Johnson", "Spring Soccer", "3", "bob@example.com", "Active"],
      ["Alice Brown", "Spring Soccer", "4", "alice@example.com", "Waitlist"]
    ];

    await sheets.spreadsheets.values.append({
      spreadsheetId: EXAMPLE_SPREADSHEET_ID,
      range: "Test Data!A:E",
      valueInputOption: 'RAW',
      requestBody: {
        values: newEntries,
      },
    });

    console.log("   ✅ Appended new entries to Google Sheets");

    console.log("\n4. Advanced Sheets operations...");

    // Example: Get sheet metadata
    const sheetInfo = await sheets.spreadsheets.get({
      spreadsheetId: EXAMPLE_SPREADSHEET_ID,
    });

    console.log(`   ✅ Spreadsheet title: ${sheetInfo.data.properties?.title}`);
    console.log(`   📋 Number of sheets: ${sheetInfo.data.sheets?.length}`);

    // Example: Batch operations
    const batchResponse = await sheets.spreadsheets.values.batchGet({
      spreadsheetId: EXAMPLE_SPREADSHEET_ID,
      ranges: ["Test Data!A:A", "Test Data!B:B"],  // Get multiple ranges at once
    });

    console.log(`   ✅ Batch read completed: ${batchResponse.data.valueRanges?.length} ranges`);

    console.log("\n🎉 Google Sheets integration is working perfectly!");
    console.log("\n📋 What this demonstrates:");
    console.log("   ✅ Domain-wide delegation allows access without user auth");
    console.log("   ✅ Same credentials work for all bots");
    console.log("   ✅ Full Google Sheets API access available");
    console.log("   ✅ Clear client separation: googleClient for Google APIs");
    console.log("   ✅ Advanced API access when needed");

  } catch (error) {
    console.error(`❌ Google Sheets example failed: ${error.message}`);

    if (error.message.includes("Unable to parse range")) {
      console.log("\n💡 Tip: Update EXAMPLE_SPREADSHEET_ID with your actual spreadsheet");
    }

    if (error.message.includes("Insufficient permissions")) {
      console.log("\n💡 Tip: Check domain-wide delegation setup in Google Admin Console");
    }
  }
}

async function waitlistSheetsExample() {
  console.log("\n📋 Practical Waitlist + Sheets Example\n");

  const adminEmail = getAdminUserEmail();

  // Your actual waitlist spreadsheet ID would go here
  const WAITLIST_SPREADSHEET_ID = Deno.env.get("WAITLIST_SPREADSHEET_ID");

  if (!WAITLIST_SPREADSHEET_ID) {
    console.log("⚠️  WAITLIST_SPREADSHEET_ID not set, skipping practical example");
    return;
  }

  try {
    // 1. Read current waitlist from sheets
    const sheets = await googleClient.sheets(adminEmail);
    const response = await sheets.spreadsheets.values.get({
      spreadsheetId: WAITLIST_SPREADSHEET_ID,
      range: "Waitlist!A2:F1000",  // Assuming columns: Name, League, Email, Phone, Position, Notes
    });

    const waitlistData = response.data.values || [];
    console.log(`📊 Current waitlist has ${waitlistData.length} entries`);

    // 2. Store in Firestore for real-time Slack operations
    for (const [index, row] of waitlistData.entries()) {
      if (row.length >= 3) { // Ensure minimum data
        const waitlistEntry = {
          player_name: row[0],
          league_id: row[1],
          email: row[2],
          phone: row[3] || "",
          position: parseInt(row[4]) || (index + 1),
          notes: row[5] || "",
          created_at: new Date(),
          source: "google_sheets",
          sheets_row: index + 2, // Track original row for updates
          notified: false
        };

        // Check if already exists to avoid duplicates
        const existing = await firebaseClient.queryCollection(
          "waitlists",
          "sheets_row",
          "==",
          waitlistEntry.sheets_row
        );

        if (existing.length === 0) {
          await firebaseClient.addDoc("waitlists", waitlistEntry);
          console.log(`   ✅ Added ${waitlistEntry.player_name} to Firestore`);
        }
      }
    }

    // 3. Example: When someone gets off waitlist, update sheets
    const updateSheetsWhenPromoted = async (playerName: string, leagueId: string) => {
      // Find the row in sheets data
      const rowIndex = waitlistData.findIndex(row =>
        row[0] === playerName && row[1] === leagueId
      );

      if (rowIndex !== -1) {
        // Update the status column (assuming column G for status)
        await sheets.spreadsheets.values.update({
          spreadsheetId: WAITLIST_SPREADSHEET_ID,
          range: `Waitlist!G${rowIndex + 2}`, // +2 because array is 0-indexed and we skip header
          valueInputOption: 'RAW',
          requestBody: {
            values: [["PROMOTED"]],
          },
        });

        console.log(`   ✅ Updated ${playerName} status to PROMOTED in sheets`);
      }
    };

    // Example usage (commented out to avoid actual changes)
    // await updateSheetsWhenPromoted("John Doe", "Spring Basketball");

    console.log("\n🎯 This example shows how to:");
    console.log("   ✅ Read waitlist data from existing Google Sheets");
    console.log("   ✅ Store in Firestore for fast Slack bot operations");
    console.log("   ✅ Update sheets when status changes");
    console.log("   ✅ Maintain sync between both systems");
    console.log("   ✅ Use clear client separation (googleClient + firebaseClient)");

  } catch (error) {
    console.error(`❌ Waitlist sheets example failed: ${error.message}`);
  }
}

if (import.meta.main) {
  await demonstrateGoogleSheets();
  await waitlistSheetsExample();
}