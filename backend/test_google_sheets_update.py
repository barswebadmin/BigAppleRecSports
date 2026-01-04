#!/usr/bin/env python3
"""
Test script for Google Sheets write functionality.

This demonstrates how to update position titles in the leadership spreadsheet.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.integrations.google import GoogleSheetsClient
from config import config


def example_update_position_titles():
    """
    Example: Update position titles in a specific column to match standardized format.
    
    This would typically be used to:
    1. Fetch the current spreadsheet
    2. Parse it to find positions
    3. Update position titles to match hierarchy.yaml or Shopify About page
    """
    
    # Initialize client
    client = GoogleSheetsClient()
    print(f"✅ Initialized client with service account: {client.service_account_email}")
    print(f"📧 Make sure the spreadsheet is shared with EDIT permissions to this email!\n")
    
    # Example spreadsheet ID (replace with actual)
    sheet_id = "YOUR_SPREADSHEET_ID_HERE"
    
    # Example: Fetch current data (commented out - requires valid sheet_id)
    print("📥 Example: Fetching current data")
    print("   (Requires valid spreadsheet ID)\n")
    # current_data = client.fetch_sheet_as_csv(sheet_id, range_name="A1:E10")
    # print(f"   Found {len(current_data)} rows\n")
    
    # Example: Update a specific range
    print("📝 Example 1: Update a single range")
    new_values = [
        ["Position Title", "Name", "Email"],  # Header row
        ["Commissioner", "Chase Tucker", "chase@bigapplerecsports.com"],
        ["Vice Commissioner", "Stephen Torres", "stephen@bigapplerecsports.com"]
    ]
    
    # Uncomment to actually update:
    # result = client.update_sheet_values(sheet_id, "A1:C3", new_values)
    # print(f"   ✅ Updated {result['updatedCells']} cells\n")
    print("   (Commented out - remove comment to actually update)\n")
    
    # Example: Batch update multiple ranges
    print("📝 Example 2: Batch update multiple ranges (more efficient)")
    updates = [
        {
            'range': 'A1:A1',
            'values': [['STANDARDIZED POSITION TITLE']]  # Update header
        },
        {
            'range': 'A2:A5',
            'values': [
                ['Commissioner'],
                ['Vice Commissioner'],
                ['Commissioner of WTNB+ Players'],
                ['Secretary']
            ]  # Update position titles
        }
    ]
    
    # Uncomment to actually update:
    # result = client.batch_update_sheet_values(sheet_id, updates)
    # print(f"   ✅ Batch updated {result['totalUpdatedCells']} cells\n")
    print("   (Commented out - remove comment to actually update)\n")


def example_standardize_position_column():
    """
    Example: Standardize all position titles in column A to match hierarchy.yaml.
    
    This is a more realistic use case for the leadership workflow.
    """
    from config.leadership import load_hierarchy_config
    
    print("🔄 Example: Standardize position titles based on hierarchy.yaml\n")
    
    # Load expected positions from hierarchy.yaml
    hierarchy = load_hierarchy_config()
    print(f"📊 Loaded {len(hierarchy.sections)} sections from hierarchy.yaml")
    
    # Build a mapping of all expected position titles
    expected_titles = {}
    for section_name, section_data in hierarchy.sections.items():
        for position in section_data.positions:
            role_key = position.role_key
            title = position.title
            expected_titles[role_key] = title
    
    print(f"📋 Found {len(expected_titles)} expected position titles\n")
    
    # Example workflow:
    # 1. Fetch current spreadsheet
    # 2. Parse each position row
    # 3. Match position to hierarchy (using CSV parser logic)
    # 4. Replace fuzzy/inconsistent title with standardized title from hierarchy.yaml
    # 5. Batch update all position titles in one API call
    
    print("Example standardized titles:")
    for i, (role_key, title) in enumerate(list(expected_titles.items())[:5], 1):
        print(f"   {i}. {role_key}: '{title}'")
    
    print("\n💡 To implement:")
    print("   1. Fetch spreadsheet with client.fetch_sheet_as_csv()")
    print("   2. Parse rows and match to hierarchy using LeadershipCSVParser")
    print("   3. Build updates list with standardized titles")
    print("   4. Call client.batch_update_sheet_values() to update all at once")


if __name__ == "__main__":
    print("=" * 80)
    print("Google Sheets Write Access Test")
    print("=" * 80)
    print()
    
    try:
        example_update_position_titles()
        print()
        example_standardize_position_column()
        
        print("\n" + "=" * 80)
        print("✅ Examples completed successfully!")
        print("\n📝 Next steps:")
        print("   1. Share your spreadsheet with the service account (EDIT permissions)")
        print("   2. Update the sheet_id in this script")
        print("   3. Uncomment the actual update lines")
        print("   4. Run this script to test updates")
        print("=" * 80)
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure you've set up Google Service Account credentials.")
        print("   See: GOOGLE_SHEETS_SETUP_GUIDE.md")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

