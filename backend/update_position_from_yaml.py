#!/usr/bin/env python3
"""
Update position titles in the leadership spreadsheet to match hierarchy.yaml.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.integrations.google import GoogleSheetsClient
from config.leadership import load_hierarchy_config, normalize_title


def main():
    if len(sys.argv) < 2:
        print("❌ Usage: python3 backend/update_position_from_yaml.py <sheet_url_or_id>")
        sys.exit(1)
    
    sheet_url = sys.argv[1].strip()
    
    print("=" * 80)
    print("Update Position Titles to Match hierarchy.yaml")
    print("=" * 80)
    print()
    
    # Initialize client
    print("📊 Initializing Google Sheets client...")
    client = GoogleSheetsClient()
    print(f"✅ Service account: {client.service_account_email}\n")
    
    # Extract sheet ID
    sheet_id = client.extract_sheet_id_from_url(sheet_url)
    print(f"📄 Sheet ID: {sheet_id}\n")
    
    # Load hierarchy config
    print("📋 Loading hierarchy.yaml...")
    hierarchy = load_hierarchy_config()
    print(f"✅ Loaded {len(hierarchy.sections)} sections with expected titles\n")
    
    # Build a map of normalized title -> standardized title
    title_map = {}
    for section_name, section_data in hierarchy.sections.items():
        for position in section_data.positions:
            normalized = normalize_title(position.title)
            title_map[normalized] = position.title
    
    print(f"📊 Built mapping for {len(title_map)} expected position titles\n")
    
    # Fetch current spreadsheet data
    print("📥 Fetching spreadsheet data...")
    try:
        data = client.fetch_sheet_as_csv(sheet_id, "A1:E100")
        print(f"✅ Fetched {len(data)} rows\n")
    except PermissionError as e:
        print(f"❌ Permission error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        sys.exit(1)
    
    # Find position titles (typically in column A or first column with "position" in header)
    print("🔍 Scanning for position titles...")
    
    # Look for position column (usually first column or has "position" in header)
    position_col_idx = 0  # Default to column A
    
    # Find positions that don't match YAML (case-insensitive, normalized)
    mismatches = []
    for row_idx, row in enumerate(data, start=1):
        if row_idx <= 5:  # Skip header rows
            continue
        
        if len(row) > position_col_idx:
            current_title = row[position_col_idx].strip()
            
            if not current_title or current_title.lower() == "vacant":
                continue
            
            # Check if this looks like a position title (not a name, email, etc.)
            normalized_current = normalize_title(current_title)
            
            # Check if it's in our expected titles
            if normalized_current in title_map:
                standardized = title_map[normalized_current]
                
                # If the current title doesn't exactly match the standardized one
                if current_title != standardized:
                    mismatches.append({
                        'row': row_idx,
                        'cell': f"A{row_idx}",
                        'current': current_title,
                        'standardized': standardized,
                        'normalized': normalized_current
                    })
    
    if not mismatches:
        print("✅ All position titles already match hierarchy.yaml!")
        print("   No updates needed.")
        sys.exit(0)
    
    print(f"\n📊 Found {len(mismatches)} position titles that need standardization:\n")
    
    # Show first 10 mismatches
    for i, mismatch in enumerate(mismatches[:10], 1):
        print(f"   {i}. Row {mismatch['row']} (Cell {mismatch['cell']}):")
        print(f"      Current:      '{mismatch['current']}'")
        print(f"      Should be:    '{mismatch['standardized']}'")
        print()
    
    if len(mismatches) > 10:
        print(f"   ... and {len(mismatches) - 10} more\n")
    
    # Update the first mismatch as a test
    print("🔄 Updating the first mismatch as a test...\n")
    first = mismatches[0]
    
    try:
        result = client.update_sheet_values(
            sheet_id,
            first['cell'],
            [[first['standardized']]]
        )
        
        print(f"✅ SUCCESS! Updated cell {first['cell']}")
        print(f"   From: '{first['current']}'")
        print(f"   To:   '{first['standardized']}'")
        print(f"   Updated {result['updatedCells']} cell(s)")
        
        # Verify the update
        print("\n📥 Verifying update...")
        updated_data = client.fetch_sheet_as_csv(sheet_id, first['cell'])
        print(f"   Cell {first['cell']} now contains: '{updated_data[0][0]}'")
        
        print("\n🎉 Update confirmed!")
        print(f"\n💡 Remaining mismatches: {len(mismatches) - 1}")
        print("   Run this script again to update more, or implement batch update for all.")
        
    except PermissionError as e:
        print(f"❌ Permission error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error updating: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)

