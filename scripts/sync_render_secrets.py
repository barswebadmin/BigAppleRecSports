#!/usr/bin/env python3
"""
Render Environment Variables Sync Script

Compares local .env file with Render service environment variables
and adds/updates any missing or changed variables.

Usage:
    python scripts/sync_render_secrets.py

Environment variables required:
    RENDER_API_KEY - Your Render API key
    RENDER_SERVICE_ID - Your Render service ID
"""

import os
import sys
import requests
from typing import Dict


def load_env_file(env_path: str = ".env") -> Dict[str, str]:
    """Load environment variables from .env file"""
    env_vars = {}

    if not os.path.exists(env_path):
        print(f"❌ {env_path} file not found!")
        return env_vars

    with open(env_path, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Parse KEY=VALUE format
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")  # Remove quotes
                env_vars[key] = value
            else:
                print(f"⚠️ Skipping malformed line {line_num}: {line}")

    print(f"📁 Loaded {len(env_vars)} variables from {env_path}")
    return env_vars


def get_render_env_vars(api_key: str, service_id: str) -> Dict[str, str]:
    """Fetch current environment variables from Render"""
    url = f"https://api.render.com/v1/services/{service_id}/env-vars"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        env_vars = {}
        for var in response.json():
            if "key" in var and "value" in var:
                env_vars[var["key"]] = var["value"]

        print(f"☁️ Fetched {len(env_vars)} variables from Render")
        return env_vars

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch Render environment variables: {e}")
        if hasattr(e, "response") and e.response:
            print(f"   Response: {e.response.status_code} - {e.response.text}")
        sys.exit(1)


def update_render_env_var(api_key: str, service_id: str, key: str, value: str) -> bool:
    """Update a single environment variable in Render"""
    url = f"https://api.render.com/v1/services/{service_id}/env-vars/{key}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"value": value}

    try:
        response = requests.put(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to update {key}: {e}")
        return False


def create_render_env_var(api_key: str, service_id: str, key: str, value: str) -> bool:
    """Create a new environment variable in Render"""
    url = f"https://api.render.com/v1/services/{service_id}/env-vars"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"key": key, "value": value}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create {key}: {e}")
        return False


def sync_secrets(dry_run: bool = False) -> bool:
    """Main function to sync local .env with Render"""

    # Get API credentials
    api_key = os.getenv("RENDER_API_KEY")
    service_id = os.getenv("RENDER_SERVICE_ID")

    if not api_key:
        print("❌ RENDER_API_KEY environment variable not set")
        print("   Get your API key from: https://dashboard.render.com/account")
        return False

    if not service_id:
        print("❌ RENDER_SERVICE_ID environment variable not set")
        print("   Find your service ID in the Render dashboard URL")
        return False

    print(f"🔄 Syncing secrets {'(DRY RUN)' if dry_run else '(LIVE MODE)'}")
    print(f"   Service ID: {service_id}")

    # Load local environment variables
    local_vars = load_env_file()
    if not local_vars:
        print("❌ No local environment variables found")
        return False

    # Get current Render environment variables
    render_vars = get_render_env_vars(api_key, service_id)

    # Find differences
    missing_vars = set(local_vars.keys()) - set(render_vars.keys())
    changed_vars = {
        key
        for key in local_vars.keys()
        if key in render_vars and render_vars[key] != local_vars[key]
    }

    print("\n📊 Analysis:")
    print(f"   🆕 Missing in Render: {len(missing_vars)}")
    print(f"   🔄 Changed values: {len(changed_vars)}")
    print(
        f"   ✅ Already synced: {len(set(local_vars.keys()) - missing_vars - changed_vars)}"
    )

    if not missing_vars and not changed_vars:
        print("\n✅ All secrets are already in sync!")
        return True

    # Show what will be changed
    if missing_vars:
        print(f"\n🆕 Will create: {', '.join(missing_vars)}")
    if changed_vars:
        print(f"🔄 Will update: {', '.join(changed_vars)}")

    if dry_run:
        print("\n🔍 Dry run complete - no changes made")
        return True

    # Apply changes
    success_count = 0
    total_changes = len(missing_vars) + len(changed_vars)

    # Create missing variables
    for key in missing_vars:
        if create_render_env_var(api_key, service_id, key, local_vars[key]):
            print(f"✅ Created: {key}")
            success_count += 1
        else:
            print(f"❌ Failed to create: {key}")

    # Update changed variables
    for key in changed_vars:
        if update_render_env_var(api_key, service_id, key, local_vars[key]):
            print(f"✅ Updated: {key}")
            success_count += 1
        else:
            print(f"❌ Failed to update: {key}")

    print(f"\n📈 Results: {success_count}/{total_changes} changes successful")

    if success_count == total_changes:
        print("🎉 All secrets synced successfully!")
        return True
    else:
        print("⚠️ Some secrets failed to sync")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Sync local .env with Render environment variables"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without making changes",
    )
    args = parser.parse_args()

    success = sync_secrets(dry_run=args.dry_run)
    sys.exit(0 if success else 1)
