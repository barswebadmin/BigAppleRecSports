#!/usr/bin/env python3
"""
Quick test to update a single position title in the leadership spreadsheet.

Usage:
    python3 backend/test_update_position.py <sheet_url_or_id>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.integrations.google import GoogleSheetsClient


def main():
    if len(sys.argv) < 2:
        print("❌ Usage: python3 backend/test_update_position.py <sheet_url_or_id>")
        sys.exit(1)
    
    sheet_url = sys.argv[1].strip()
    
    if not sheet_url:
        print("❌ No URL provided")
        sys.exit(1)
    
    print("\n📊 Initializing Google Sheets client...")
    client = GoogleSheetsClient()
    print(f"✅ Service account: {client.service_account_email}\n")
    
    # Extract sheet ID
    sheet_id = client.extract_sheet_id_from_url(sheet_url)
    print(f"📄 Sheet ID: {sheet_id}\n")
    
    # Fetch current data to see what we're working with
    print("📥 Fetching first 20 rows...")
    try:
        data = client.fetch_sheet_as_csv(sheet_id, "A1:E20")
        print(f"✅ Fetched {len(data)} rows\n")
        
        # Show first few rows
        print("📋 First 5 rows:")
        for i, row in enumerate(data[:5], 1):
            print(f"   {i}. {' | '.join(row[:5])}")
        print()
        
    except PermissionError as e:
        print(f"❌ Permission error: {e}")
        print("\n💡 Make sure the spreadsheet is shared with EDIT permissions to:")
        print(f"   {client.service_account_email}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        sys.exit(1)
    
    # Now let's try to update a single cell as a test
    print("🔄 Testing write access...")
    print("   Will update cell A1 with 'STANDARDIZED POSITION TITLE'\n")
    
    try:
        # Update just the A1 cell
        result = client.update_sheet_values(
            sheet_id,
            "A1:A1",
            [["STANDARDIZED POSITION TITLE"]]
        )
        
        print(f"\n✅ SUCCESS! Updated {result['updatedCells']} cell(s)")
        print(f"   Updated range: {result['updatedRange']}")
        
        # Verify the update
        print("\n📥 Verifying update...")
        updated_data = client.fetch_sheet_as_csv(sheet_id, "A1:A1")
        print(f"   A1 now contains: '{updated_data[0][0]}'")
        
        print("\n🎉 Write access confirmed! You can now update position titles.")
        
    except PermissionError as e:
        print(f"\n❌ Permission error: {e}")
        print("\n💡 The service account needs EDIT (not just VIEW) permissions.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error updating data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 80)
    print("Google Sheets Write Test")
    print("=" * 80)
    print()
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)

