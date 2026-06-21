#!/usr/bin/env python3
"""Example usage of GoogleClient v2."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from dotenv import load_dotenv
from shared_utilities.clients.google_client_v2 import GoogleClient, DriveScopes

load_dotenv()


def example_drive_operations():
    """Example Drive API operations."""
    client = GoogleClient()
    
    folder_id = "1pKAOY03Ta6ea3dVUNSamb4zzJEVWweSM"
    
    # List files in folder (uses default subject + readonly scope)
    print("📂 Listing folder files...")
    files = client.drive.list_folder_files(folder_id=folder_id)
    print(f"Found {len(files)} files")
    
    # Get detailed metadata for first file
    if files:
        file_id = files[0]["id"]
        print(f"\n📄 Getting details for: {files[0]['name']}")
        
        metadata = client.drive.get_file(
            file_id=file_id,
            fields="id,name,mimeType,size,owners,createdTime"
        )
        print(f"  Type: {metadata.get('mimeType')}")
        print(f"  Size: {metadata.get('size', 'N/A')} bytes")
        print(f"  Created: {metadata.get('createdTime')}")


def example_sheets_operations():
    """Example Sheets API operations."""
    client = GoogleClient()
    
    # Example spreadsheet ID (replace with real ID)
    spreadsheet_id = "your-spreadsheet-id"
    
    # Get values
    print("📊 Reading spreadsheet...")
    try:
        data = client.sheets.get_values(
            spreadsheet_id=spreadsheet_id,
            range_name="Sheet1!A1:D10"
        )
        print(f"Read {len(data)} rows")
    except Exception as e:
        print(f"(Skipping sheets example: {e})")


def example_override_subject():
    """Example of overriding subject per call."""
    client = GoogleClient()
    
    folder_id = "1pKAOY03Ta6ea3dVUNSamb4zzJEVWweSM"
    
    # Use default subject
    files_default = client.drive.list_folder_files(folder_id=folder_id)
    print(f"Default subject: {len(files_default)} files")
    
    # Override subject for specific call
    files_other = client.drive.list_folder_files(
        folder_id=folder_id,
        subject="other@bigapplerecsports.com"
    )
    print(f"Other subject: {len(files_other)} files")


def example_raw_service_access():
    """Example of using raw service for custom queries."""
    client = GoogleClient()
    
    # Get raw Drive service
    drive = client.service(
        "drive",
        "v3",
        "joe@bigapplerecsports.com",
        [DriveScopes.readonly]
    )
    
    # Custom query (search across all drives)
    print("🔍 Custom query: PDFs modified in last 7 days")
    from datetime import datetime, timedelta
    week_ago = (datetime.now() - timedelta(days=7)).isoformat() + "Z"
    
    result = drive.files().list(
        q=f"mimeType = 'application/pdf' and modifiedTime > '{week_ago}'",
        fields="files(id, name, modifiedTime)",
        pageSize=10
    ).execute()
    
    files = result.get("files", [])
    print(f"Found {len(files)} PDFs")


if __name__ == "__main__":
    print("=== GoogleClient v2 Examples ===\n")
    
    example_drive_operations()
    print("\n" + "="*50 + "\n")
    
    example_sheets_operations()
    print("\n" + "="*50 + "\n")
    
    example_raw_service_access()
