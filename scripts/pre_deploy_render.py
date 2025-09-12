#!/usr/bin/env python3
"""
Render Pre-Deploy Script

Syncs local .env secrets with Render before deployment and optionally
triggers a deployment if secrets were updated.

Usage:
    python scripts/pre_deploy_render.py [--deploy] [--dry-run]

Options:
    --deploy    Trigger a deployment after syncing secrets
    --dry-run   Show what would change without making changes

Environment variables required:
    RENDER_API_KEY - Your Render API key
    RENDER_SERVICE_ID - Your Render service ID
"""

import os
import sys
import requests
import time
from typing import Dict, Optional


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


def trigger_deployment(api_key: str, service_id: str) -> Optional[str]:
    """Trigger a new deployment and return deployment ID"""
    url = f"https://api.render.com/v1/services/{service_id}/deploys"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, timeout=30)
        response.raise_for_status()

        deploy_data = response.json()
        deploy_id = deploy_data.get("id")
        print(f"🚀 Deployment triggered! ID: {deploy_id}")
        return deploy_id

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to trigger deployment: {e}")
        if hasattr(e, "response") and e.response:
            print(f"   Response: {e.response.status_code} - {e.response.text}")
        return None


def get_deployment_status(
    api_key: str, service_id: str, deploy_id: str
) -> Optional[str]:
    """Get the status of a deployment"""
    url = f"https://api.render.com/v1/services/{service_id}/deploys/{deploy_id}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        deploy_data = response.json()
        return deploy_data.get("status")

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get deployment status: {e}")
        return None


def wait_for_deployment(
    api_key: str, service_id: str, deploy_id: str, timeout: int = 600
) -> bool:
    """Wait for deployment to complete"""
    print(f"⏳ Waiting for deployment {deploy_id} to complete...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        status = get_deployment_status(api_key, service_id, deploy_id)

        if status == "live":
            print(f"✅ Deployment {deploy_id} completed successfully!")
            return True
        elif status in ["build_failed", "canceled", "deactivated"]:
            print(f"❌ Deployment {deploy_id} failed with status: {status}")
            return False
        elif status in ["building", "deploying"]:
            print(f"🔄 Deployment status: {status}")
            time.sleep(10)
        else:
            print(f"⚠️ Unknown deployment status: {status}")
            time.sleep(10)

    print(f"⏰ Deployment timed out after {timeout} seconds")
    return False


def sync_and_deploy(dry_run: bool = False, deploy: bool = False) -> bool:
    """Main function to sync secrets and optionally deploy"""

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

    print(f"🚀 Pre-deploy preparation {'(DRY RUN)' if dry_run else '(LIVE MODE)'}")
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

    print("\n📊 Secret Analysis:")
    print(f"   🆕 Missing in Render: {len(missing_vars)}")
    print(f"   🔄 Changed values: {len(changed_vars)}")
    print(
        f"   ✅ Already synced: {len(set(local_vars.keys()) - missing_vars - changed_vars)}"
    )

    secrets_need_update = bool(missing_vars or changed_vars)

    if not secrets_need_update:
        print("\n✅ All secrets are already in sync!")
        if deploy:
            print("🚀 No secret changes, but deployment requested...")
        else:
            return True

    # Show what will be changed
    if missing_vars:
        print(f"\n🆕 Will create: {', '.join(missing_vars)}")
    if changed_vars:
        print(f"🔄 Will update: {', '.join(changed_vars)}")

    if dry_run:
        print("\n🔍 Dry run complete - no changes made")
        if deploy:
            print("🚀 Would trigger deployment after secret sync")
        return True

    # Apply secret changes
    if secrets_need_update:
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

        print(
            f"\n📈 Secret sync results: {success_count}/{total_changes} changes successful"
        )

        if success_count != total_changes:
            print("⚠️ Some secrets failed to sync")
            if deploy:
                print("❌ Skipping deployment due to secret sync failures")
            return False
        else:
            print("🎉 All secrets synced successfully!")

    # Trigger deployment if requested
    if deploy:
        print("\n🚀 Triggering deployment...")
        deploy_id = trigger_deployment(api_key, service_id)

        if deploy_id:
            success = wait_for_deployment(api_key, service_id, deploy_id)
            if success:
                print("\n🎉 Deployment completed successfully!")
                print("🌐 Your service should be live with updated secrets")
                return True
            else:
                print("\n❌ Deployment failed")
                return False
        else:
            print("❌ Failed to trigger deployment")
            return False
    else:
        print("\n✅ Secrets synced! Ready for deployment.")
        print("🚀 To deploy now, run: python scripts/pre_deploy_render.py --deploy")
        return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Sync secrets and optionally deploy to Render"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without making changes",
    )
    parser.add_argument(
        "--deploy", action="store_true", help="Trigger deployment after syncing secrets"
    )
    args = parser.parse_args()

    success = sync_and_deploy(dry_run=args.dry_run, deploy=args.deploy)
    sys.exit(0 if success else 1)
