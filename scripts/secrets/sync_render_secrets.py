#!/usr/bin/env python3
"""
Sync secrets to Render environment variables.

Supports syncing from either .env file or AWS SSM Parameter Store.
Does NOT trigger deployments - only syncs secrets.

Usage:
    # Sync from .env file
    python scripts/secrets/sync_render_secrets.py

    # Sync from AWS SSM Parameter Store
    python scripts/secrets/sync_render_secrets.py --from-ssm

    # Dry run (show what would change)
    python scripts/secrets/sync_render_secrets.py --dry-run

Options:
    --from-ssm       Use AWS SSM Parameter Store instead of .env file
    --dry-run        Show what would change without making changes

Environment variables required:
    RENDER_API_KEY      - Your Render API key
    RENDER_SERVICE_ID   - Your Render service ID
    
    For --from-ssm:
    AWS_ACCESS_KEY_ID   - AWS credentials
    AWS_SECRET_ACCESS_KEY - AWS credentials
    AWS_DEFAULT_REGION   - AWS region (defaults to us-east-1)
    PARAMETER_PREFIX     - SSM parameter prefix (defaults to /bars/)
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import requests
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
except ImportError:
    print("❌ Missing required dependencies. Install with:")
    print("   pip install requests boto3")
    sys.exit(1)


def load_env_file(env_path: Path = None) -> Dict[str, str]:
    """Load environment variables from .env file."""
    if env_path is None:
        env_path = project_root / ".env"
    
    env_vars = {}
    
    if not env_path.exists():
        print(f"⚠️  {env_path} file not found")
        return env_vars
    
    with open(env_path, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            if not line or line.startswith("#"):
                continue
            
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                env_vars[key] = value
    
    print(f"📁 Loaded {len(env_vars)} variables from {env_path}")
    return env_vars


def _parameter_name_to_env_var(param_name: str, prefix: str) -> str:
    """Convert SSM parameter name to environment variable name."""
    if param_name.startswith(prefix):
        name = param_name[len(prefix):]
    else:
        name = param_name
    
    name = name.lstrip("/")
    env_key = name.replace("/", "_").replace("-", "_").upper()
    return env_key


def get_ssm_parameters(prefix: str = "/bars/", region: str = "us-east-1") -> Dict[str, str]:
    """Fetch all parameters from AWS SSM Parameter Store with the given prefix."""
    try:
        ssm = boto3.client("ssm", region_name=region)
        
        paginator = ssm.get_paginator("describe_parameters")
        parameters = []
        
        for page in paginator.paginate(
            ParameterFilters=[
                {"Key": "Name", "Option": "BeginsWith", "Values": [prefix]}
            ]
        ):
            parameters.extend(page["Parameters"])
        
        if not parameters:
            print(f"⚠️  No parameters found with prefix: {prefix}")
            return {}
        
        print(f"📡 Found {len(parameters)} parameters in SSM with prefix: {prefix}")
        
        env_vars = {}
        for param in parameters:
            param_name = param["Name"]
            try:
                response = ssm.get_parameter(Name=param_name, WithDecryption=True)
                value = response["Parameter"]["Value"]
                env_key = _parameter_name_to_env_var(param_name, prefix)
                env_vars[env_key] = value
            except ClientError as e:
                print(f"   ❌ Failed to fetch {param_name}: {e}")
        
        return env_vars
        
    except BotoCoreError as e:
        print(f"❌ AWS SDK error: {e}")
        print("   Make sure AWS credentials are configured")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error fetching SSM parameters: {e}")
        sys.exit(1)


def get_render_env_vars(api_key: str, service_id: str) -> Dict[str, str]:
    """Fetch current environment variables from Render."""
    url = f"https://api.render.com/v1/services/{service_id}/env-vars"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        env_vars = {}
        for var in response.json():
            if "key" in var and "value" in var:
                env_vars[var["key"]] = var["value"]
        
        return env_vars
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch Render environment variables: {e}")
        if hasattr(e, "response") and e.response:
            print(f"   Response: {e.response.status_code} - {e.response.text}")
        sys.exit(1)


def update_render_env_var(api_key: str, service_id: str, key: str, value: str) -> bool:
    """Update a single environment variable in Render."""
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
    """Create a new environment variable in Render."""
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


def sync_secrets(
    api_key: str,
    service_id: str,
    source_vars: Dict[str, str],
    dry_run: bool = False
) -> bool:
    """Sync secrets from source to Render."""
    render_vars = get_render_env_vars(api_key, service_id)
    
    missing_vars = set(source_vars.keys()) - set(render_vars.keys())
    changed_vars = {
        key
        for key in source_vars.keys()
        if key in render_vars and render_vars[key] != source_vars[key]
    }
    
    print("\n📊 Secret Analysis:")
    print(f"   🆕 Missing in Render: {len(missing_vars)}")
    print(f"   🔄 Changed values: {len(changed_vars)}")
    print(f"   ✅ Already synced: {len(set(source_vars.keys()) - missing_vars - changed_vars)}")
    
    if not missing_vars and not changed_vars:
        print("\n✅ All secrets are already in sync!")
        return True
    
    if missing_vars:
        print(f"\n🆕 Will create: {', '.join(sorted(missing_vars))}")
    if changed_vars:
        print(f"🔄 Will update: {', '.join(sorted(changed_vars))}")
    
    if dry_run:
        print("\n🔍 Dry run complete - no changes made")
        return True
    
    # Apply changes
    success_count = 0
    total_changes = len(missing_vars) + len(changed_vars)
    
    for key in sorted(missing_vars):
        if create_render_env_var(api_key, service_id, key, source_vars[key]):
            print(f"✅ Created: {key}")
            success_count += 1
        else:
            print(f"❌ Failed to create: {key}")
    
    for key in sorted(changed_vars):
        if update_render_env_var(api_key, service_id, key, source_vars[key]):
            print(f"✅ Updated: {key}")
            success_count += 1
        else:
            print(f"❌ Failed to update: {key}")
    
    print(f"\n📈 Results: {success_count}/{total_changes} changes successful")
    
    if success_count != total_changes:
        print("⚠️  Some secrets failed to sync")
        return False
    
    print("🎉 All secrets synced successfully!")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Sync secrets to Render environment variables"
    )
    parser.add_argument(
        "--from-ssm",
        action="store_true",
        help="Use AWS SSM Parameter Store instead of .env file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without making changes"
    )
    args = parser.parse_args()
    
    # Get API credentials
    api_key = os.getenv("RENDER_API_KEY")
    service_id = os.getenv("RENDER_SERVICE_ID")
    
    if not api_key:
        print("❌ RENDER_API_KEY environment variable not set")
        print("   Get your API key from: https://dashboard.render.com/account")
        sys.exit(1)
    
    if not service_id:
        print("❌ RENDER_SERVICE_ID environment variable not set")
        print("   Find your service ID in the Render dashboard URL")
        sys.exit(1)
    
    print("🔐 Render Secret Sync")
    print("=" * 50)
    print(f"   Service ID: {service_id}")
    if args.dry_run:
        print("   Mode: DRY RUN")
    print()
    
    # Load secrets from source
    if args.from_ssm:
        param_prefix = os.getenv("PARAMETER_PREFIX", "/bars/")
        aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        
        print(f"📡 Fetching secrets from AWS SSM Parameter Store...")
        print(f"   Prefix: {param_prefix}")
        print(f"   Region: {aws_region}")
        print()
        
        source_vars = get_ssm_parameters(prefix=param_prefix, region=aws_region)
        
        if not source_vars:
            print("❌ No parameters found to sync")
            sys.exit(1)
    else:
        print("📁 Loading secrets from .env file...")
        print()
        
        source_vars = load_env_file()
        
        if not source_vars:
            print("❌ No environment variables found in .env file")
            sys.exit(1)
    
    # Sync secrets
    print("☁️  Syncing secrets to Render...")
    success = sync_secrets(api_key, service_id, source_vars, dry_run=args.dry_run)
    
    if not success:
        print("❌ Secret sync failed")
        sys.exit(1)
    
    print("\n✅ Secret sync complete!")


if __name__ == "__main__":
    main()
