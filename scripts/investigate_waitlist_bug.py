#!/usr/bin/env python3
"""
Investigate waitlist position calculation bug.
Checks Google Apps Script execution logs and Sheets revision history around 10:07 PM on 1/9/26.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("❌ Missing required packages. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)

# Configuration
SPREADSHEET_ID = "15YSo-Z6e3DP6drASxJ1nykvco0n_5la8yOiq2yuVPzk"
SCRIPT_ID = None  # Will need to find this from the project
TARGET_TIME = datetime(2026, 1, 9, 22, 7, 0)  # 10:07 PM on 1/9/26
TIME_WINDOW_MINUTES = 30  # Check 15 minutes before and after

REPO_ROOT = Path(__file__).parent.parent


def load_service_account() -> Optional[Dict[str, Any]]:
    """Load Google service account credentials."""
    # Try to find service account file
    possible_paths = [
        REPO_ROOT / "backend" / "google-service-account.json",
        REPO_ROOT / "google-service-account.json",
        REPO_ROOT / ".secrets" / "google-service-account.json",
    ]
    
    # Also check env var
    import os
    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if service_account_file:
        possible_paths.insert(0, Path(service_account_file))
    
    for path in possible_paths:
        if path.exists():
            print(f"✅ Found service account: {path}")
            with open(path, 'r') as f:
                return json.load(f)
    
    print("❌ Service account file not found. Checked:")
    for path in possible_paths:
        print(f"   - {path}")
    return None


def get_script_id_from_project() -> Optional[str]:
    """Try to find the script ID from the project's .clasp.json file."""
    clasp_json = REPO_ROOT / "GoogleAppsScripts" / "projects" / "waitlist-script-comprehensive" / ".clasp.json"
    if clasp_json.exists():
        with open(clasp_json, 'r') as f:
            data = json.load(f)
            script_id = data.get("scriptId")
            if script_id:
                print(f"✅ Found script ID: {script_id}")
                return script_id
    
    print("⚠️ Could not find script ID from .clasp.json")
    return None


def get_apps_script_executions(service, script_id: str, start_time: datetime, end_time: datetime) -> List[Dict]:
    """Get Apps Script execution logs for the time window."""
    try:
        print(f"\n🔍 Fetching Apps Script executions between {start_time} and {end_time}...")
        
        # Apps Script API doesn't have a direct execution log endpoint
        # We'll need to use the Apps Script API's projects.executions.list
        # But this requires the script to be deployed as an API executable
        
        # Alternative: Use Drive API to check file revisions
        # Or use Apps Script dashboard (requires manual check)
        
        print("⚠️ Apps Script execution logs require manual check in Apps Script dashboard")
        print(f"   Dashboard: https://script.google.com/home/projects/{script_id}/executions")
        print(f"   Time range: {start_time.isoformat()} to {end_time.isoformat()}")
        
        return []
    except HttpError as e:
        print(f"❌ Error fetching executions: {e}")
        return []


def get_sheets_revisions(service, spreadsheet_id: str, start_time: datetime, end_time: datetime) -> List[Dict]:
    """Get Sheets revision history for the time window."""
    try:
        print(f"\n🔍 Fetching Sheets revisions between {start_time} and {end_time}...")
        
        # Get all revisions
        revisions = service.revisions().list(
            spreadsheetId=spreadsheet_id
        ).execute()
        
        revisions_list = revisions.get('revisions', [])
        print(f"   Found {len(revisions_list)} total revisions")
        
        # Filter by time window
        target_revisions = []
        for rev in revisions_list:
            modified_time = datetime.fromisoformat(rev['modifiedTime'].replace('Z', '+00:00'))
            if start_time <= modified_time <= end_time:
                target_revisions.append(rev)
                print(f"   ✅ Revision at {modified_time}: {rev.get('id', 'unknown')}")
        
        return target_revisions
        
    except HttpError as e:
        print(f"❌ Error fetching revisions: {e}")
        return []


def get_sheet_data_at_revision(service, spreadsheet_id: str, revision_id: str, range_name: str = "A:Z") -> Optional[List[List]]:
    """Get sheet data at a specific revision."""
    try:
        print(f"\n📊 Fetching sheet data at revision {revision_id}...")
        
        # Get revision data
        revision = service.revisions().get(
            spreadsheetId=spreadsheet_id,
            revisionId=revision_id
        ).execute()
        
        # Note: Revisions API doesn't directly give us cell values
        # We need to use the Sheets API with the revision timestamp
        # Or export the revision as a snapshot
        
        print("⚠️ Getting cell values at a specific revision requires different approach")
        print("   Will need to check current state and compare with revision metadata")
        
        return None
        
    except HttpError as e:
        print(f"❌ Error fetching revision data: {e}")
        return None


def analyze_waitlist_calculation(sheet_data: List[List], email: str, league: str) -> Dict[str, Any]:
    """Analyze the waitlist calculation logic."""
    if not sheet_data or len(sheet_data) < 2:
        return {"error": "Invalid sheet data"}
    
    headers = sheet_data[0]
    
    # Find column indices
    email_col = next((i for i, h in enumerate(headers) if 'email' in str(h).lower()), -1)
    league_col = next((i for i, h in enumerate(headers) if 'league' in str(h).lower() or 'please select' in str(h).lower()), -1)
    timestamp_col = 0  # Usually first column
    notes_col = next((i for i, h in enumerate(headers) if 'notes' in str(h).lower()), -1)
    
    if email_col == -1 or league_col == -1:
        return {"error": "Required columns not found"}
    
    print(f"\n📊 Analyzing waitlist calculation:")
    print(f"   Email column: {email_col}")
    print(f"   League column: {league_col}")
    print(f"   Timestamp column: {timestamp_col}")
    print(f"   Notes column: {notes_col}")
    
    # Find user's entry
    user_row = None
    user_timestamp = None
    
    valid_entries = []
    skipped_rows = []
    
    for i in range(1, len(sheet_data)):
        row = sheet_data[i]
        row_email = str(row[email_col] if email_col < len(row) else '').strip().lower()
        row_league = str(row[league_col] if league_col < len(row) else '').strip()
        
        if row_email == email.lower() and row_league == league:
            user_row = i
            try:
                user_timestamp = datetime.fromisoformat(str(row[timestamp_col]))
            except:
                user_timestamp = None
            print(f"\n✅ Found user at row {i + 1}")
            print(f"   Email: {row_email}")
            print(f"   League: {row_league}")
            print(f"   Timestamp: {user_timestamp}")
        
        # Check if should skip (simplified - would need background colors)
        notes = str(row[notes_col] if notes_col >= 0 and notes_col < len(row) else '')
        skip_keywords = ['process', 'cancel', 'done', 'sent', 'sign', 'already', 'not found', 'no product', 'not sold']
        should_skip = any(keyword in notes.lower() for keyword in skip_keywords)
        
        if row_league == league:
            if should_skip:
                skipped_rows.append(i + 1)
            else:
                try:
                    entry_timestamp = datetime.fromisoformat(str(row[timestamp_col]))
                    valid_entries.append({
                        'row': i + 1,
                        'email': row_email,
                        'timestamp': entry_timestamp
                    })
                except:
                    pass
    
    if not user_timestamp:
        return {"error": "User not found in sheet"}
    
    # Calculate position
    earlier_count = sum(1 for entry in valid_entries if entry['timestamp'] < user_timestamp)
    calculated_position = earlier_count + 1
    
    return {
        "user_row": user_row + 1 if user_row else None,
        "user_timestamp": str(user_timestamp),
        "valid_entries_count": len(valid_entries),
        "skipped_rows": skipped_rows,
        "earlier_entries_count": earlier_count,
        "calculated_position": calculated_position,
        "valid_entries": valid_entries[:10]  # First 10 for debugging
    }


def main():
    """Main investigation function."""
    print("🔍 Waitlist Position Bug Investigation")
    print("=" * 60)
    print(f"Target time: {TARGET_TIME}")
    print(f"Time window: ±{TIME_WINDOW_MINUTES} minutes")
    print(f"Spreadsheet ID: {SPREADSHEET_ID}")
    
    # Load service account
    service_account_info = load_service_account()
    if not service_account_info:
        print("\n❌ Cannot proceed without service account credentials")
        return
    
    # Get script ID
    script_id = get_script_id_from_project()
    
    # Build services
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/script.scriptapp',
    ]
    
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=scopes
    )
    
    sheets_service = build('sheets', 'v4', credentials=credentials)
    drive_service = build('drive', 'v3', credentials=credentials)
    
    # Define time window
    start_time = TARGET_TIME - timedelta(minutes=TIME_WINDOW_MINUTES)
    end_time = TARGET_TIME + timedelta(minutes=TIME_WINDOW_MINUTES)
    
    # Get revisions
    revisions = get_sheets_revisions(drive_service, SPREADSHEET_ID, start_time, end_time)
    
    # Get current sheet data for analysis
    print(f"\n📊 Fetching current sheet data...")
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="A:Z"
        ).execute()
        
        sheet_data = result.get('values', [])
        print(f"   Got {len(sheet_data)} rows")
        
        # Analyze calculation (would need actual email/league from the bug report)
        print("\n⚠️ To analyze specific user, provide email and league")
        print("   Example: python scripts/investigate_waitlist_bug.py user@example.com 'League Name'")
        
    except HttpError as e:
        print(f"❌ Error fetching sheet data: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Investigation Summary")
    print("=" * 60)
    print(f"Revisions found in time window: {len(revisions)}")
    if revisions:
        for rev in revisions:
            print(f"   - {rev.get('modifiedTime')}: {rev.get('id')}")
    
    print("\n💡 Next Steps:")
    print("   1. Check Apps Script execution logs manually:")
    if script_id:
        print(f"      https://script.google.com/home/projects/{script_id}/executions")
    print("   2. Review revision history to see what changed")
    print("   3. Compare calculated position vs actual position")
    print("   4. Check if rows were incorrectly skipped or included")


if __name__ == "__main__":
    main()
