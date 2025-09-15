#!/usr/bin/env python3
"""
Update NGROK_URL in Google Apps Scripts files

This script fetches the current ngrok URL and updates all hardcoded NGROK_URL
constants in Google Apps Scripts files.

Usage:
    python scripts/update_ngrok_urls.py [new_url]

If new_url is not provided, it will attempt to fetch it from ngrok API.
"""

import re
import sys
import requests
from pathlib import Path


def get_ngrok_url():
    """Fetch the current ngrok URL from local API"""
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        if response.status_code == 200:
            data = response.json()
            tunnels = data.get("tunnels", [])
            if tunnels:
                public_url = tunnels[0]["public_url"]
                print(f"✅ Found ngrok URL: {public_url}")
                return public_url
            else:
                print("❌ No active ngrok tunnels found")
                return None
        else:
            print(f"❌ Failed to fetch ngrok URL: HTTP {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not connect to ngrok API: {e}")
        print("💡 Make sure ngrok is running: make tunnel")
        return None


def update_file_ngrok_url(file_path: Path, new_url: str) -> bool:
    """Update NGROK_URL in a single file"""
    try:
        with open(file_path, "r") as f:
            content = f.read()

        # Pattern to match NGROK_URL = 'any_url';
        pattern = r"(const\s+NGROK_URL\s*=\s*['\"])([^'\"]+)(['\"];)"

        def replacement(match):
            return f"{match.group(1)}{new_url}{match.group(3)}"

        new_content, count = re.subn(pattern, replacement, content)

        if count > 0:
            with open(file_path, "w") as f:
                f.write(new_content)
            print(f"✅ Updated {count} NGROK_URL(s) in {file_path}")
            return True
        else:
            print(f"⚠️  No NGROK_URL found in {file_path}")
            return False
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False


def find_gas_files_with_ngrok():
    """Find all Google Apps Scripts files that contain NGROK_URL"""
    gas_dir = Path("GoogleAppsScripts")
    if not gas_dir.exists():
        print("❌ GoogleAppsScripts directory not found")
        return []

    files_with_ngrok = []
    for file_path in gas_dir.rglob("*.gs"):
        try:
            with open(file_path, "r") as f:
                content = f.read()
                if "NGROK_URL" in content:
                    files_with_ngrok.append(file_path)
        except Exception as e:
            print(f"⚠️  Could not read {file_path}: {e}")

    return files_with_ngrok


def main():
    """Main function"""
    # Get new URL from command line argument or ngrok API
    if len(sys.argv) > 1:
        new_url = sys.argv[1]
        print(f"📝 Using provided URL: {new_url}")
    else:
        print("🔍 Fetching current ngrok URL...")
        new_url = get_ngrok_url()
        if not new_url:
            print("❌ Could not get ngrok URL. Please provide one manually:")
            print(
                "   python scripts/update_ngrok_urls.py https://your-ngrok-url.ngrok-free.app"
            )
            sys.exit(1)

    # Validate URL format
    if not (new_url.startswith("http://") or new_url.startswith("https://")):
        print(f"❌ Invalid URL format: {new_url}")
        print("   URL should start with http:// or https://")
        sys.exit(1)

    # Find and update files
    print("🔍 Searching for Google Apps Scripts files with NGROK_URL...")
    files_to_update = find_gas_files_with_ngrok()

    if not files_to_update:
        print("⚠️  No files found with NGROK_URL")
        return

    print(f"📁 Found {len(files_to_update)} file(s) with NGROK_URL:")
    for file_path in files_to_update:
        print(f"   {file_path}")

    print(f"\n🔄 Updating NGROK_URL to: {new_url}")
    updated_count = 0
    for file_path in files_to_update:
        if update_file_ngrok_url(file_path, new_url):
            updated_count += 1

    print(f"\n🎉 Updated {updated_count} of {len(files_to_update)} files")

    if updated_count > 0:
        print("\n💡 Next steps:")
        print("   1. Review the changes: git diff")
        print("   2. Deploy updated scripts if needed")
        print("   3. Test your Google Apps Scripts with the new URL")


if __name__ == "__main__":
    main()
