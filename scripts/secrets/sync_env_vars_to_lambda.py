#!/usr/bin/env python3
"""
Sync environment variables for Lambda functions from .env file.

Reads required env vars from Lambda's env_config.py and syncs only
those variables from .env to AWS Lambda, using size-aware batching
to stay under the 4KB limit.

Usage: ./sync_env_vars_to_lambda.py [function-name]

If no function name is provided, prompts for one interactively.
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Set


def parse_env_file(env_path: Path) -> Dict[str, str]:
    """Parse .env file into dictionary."""
    env_vars = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value.strip('\'"')
    return env_vars


def parse_required_vars(config_path: Path) -> List[str]:
    """Extract REQUIRED_ENV_VARS list from env_config.py."""
    with open(config_path) as f:
        content = f.read()
    
    match = re.search(r'REQUIRED_ENV_VARS\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find REQUIRED_ENV_VARS in {config_path}")
    
    vars_str = match.group(1)
    return re.findall(r'["\']([^"\']+)["\']', vars_str)


def get_lambda_env(function_name: str, region: str = "us-east-1") -> Dict[str, str]:
    """Get current Lambda environment variables."""
    try:
        result = subprocess.run(
            [
                "aws", "lambda", "get-function-configuration",
                "--function-name", function_name,
                "--region", region,
                "--query", "Environment.Variables",
                "--output", "json"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        env = json.loads(result.stdout)
        return env if env else {}
    except subprocess.CalledProcessError:
        return {}


def update_lambda_env(function_name: str, env_vars: Dict[str, str], region: str = "us-east-1") -> bool:
    """Update Lambda environment variables."""
    payload = json.dumps({"Variables": env_vars})
    
    try:
        subprocess.run(
            [
                "aws", "lambda", "update-function-configuration",
                "--function-name", function_name,
                "--environment", payload,
                "--region", region
            ],
            capture_output=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Update failed: {e.stderr.decode()}")
        return False


def wait_for_lambda_ready(function_name: str, region: str = "us-east-1"):
    """Wait for Lambda to be ready for next update."""
    try:
        subprocess.run(
            [
                "aws", "lambda", "wait", "function-updated",
                "--function-name", function_name,
                "--region", region
            ],
            capture_output=True,
            timeout=30
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        time.sleep(3)


def calculate_size(env_vars: Dict[str, str]) -> int:
    """Calculate size of environment variables in bytes."""
    return len(json.dumps({"Variables": env_vars}))


def sync_in_batches(
    function_name: str,
    desired_env: Dict[str, str],
    region: str = "us-east-1",
    max_size: int = 4000
) -> bool:
    """Sync environment variables in size-aware batches."""
    keys = list(desired_env.keys())
    total_keys = len(keys)
    processed = 0
    batch_num = 0
    
    print(f"\n🚀 Syncing {total_keys} variables with size-aware batching...")
    
    while processed < total_keys:
        batch_num += 1
        
        # Get current state
        current_env = get_lambda_env(function_name, region)
        current_size = calculate_size(current_env)
        
        # Build batch dynamically
        batch_keys = []
        for i in range(processed, total_keys):
            key = keys[i]
            test_env = {**current_env, **{k: desired_env[k] for k in batch_keys + [key]}}
            test_size = calculate_size(test_env)
            
            if test_size > max_size:
                if not batch_keys:
                    print(f"   ⚠️  Variable '{key}' too large ({test_size - current_size} bytes)")
                    batch_keys = [key]
                break
            
            batch_keys.append(key)
        
        if not batch_keys:
            print("   ❌ Cannot proceed - environment too large")
            return False
        
        # Apply batch
        batch_env = {**current_env, **{k: desired_env[k] for k in batch_keys}}
        batch_size = calculate_size(batch_env)
        
        print(f"📦 Batch {batch_num}: {len(batch_keys)} variables ({batch_size} bytes)")
        
        if not update_lambda_env(function_name, batch_env, region):
            return False
        
        print("   ⏳ Waiting for Lambda to be ready...")
        wait_for_lambda_ready(function_name, region)
        
        processed += len(batch_keys)
    
    return True






def main():
    if len(sys.argv) == 2:
        function_name = sys.argv[1]
    else:
        function_name = input("Enter Lambda function name: ").strip()
        if not function_name:
            print("❌ No function name provided")
            sys.exit(1)

    region = "us-east-1"

    repo_root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True
        ).stdout.strip()
    )
    env_file = repo_root / ".env"
    lambda_dir = repo_root / "aws" / "lambda" / "functions" / function_name
    config_file = lambda_dir / "env_config.py"

    if not env_file.exists():
        print(f"❌ .env file not found at {env_file}")
        sys.exit(1)

    if not config_file.exists():
        print(f"❌ env_config.py not found at {config_file}")
        print("   Create this file with REQUIRED_ENV_VARS list")
        sys.exit(1)

    print(f"📋 Reading required env vars from {config_file}...")
    try:
        required_vars = parse_required_vars(config_file)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    print(f"✅ Found {len(required_vars)} required environment variables")

    print("📖 Reading environment variables from .env...")
    all_env_vars = parse_env_file(env_file)

    desired_env = {k: all_env_vars[k] for k in required_vars if k in all_env_vars}

    if not desired_env:
        print("❌ No required variables found in .env")
        sys.exit(1)

    print(f"✅ Found {len(desired_env)}/{len(required_vars)} required variables in .env")

    missing = set(required_vars) - set(desired_env.keys())
    if missing:
        print("⚠️  Warning: Missing required variables in .env:")
        for var in sorted(missing):
            print(f"     - {var}")

    print(f"📋 Fetching current Lambda environment variables for {function_name}...")
    current_env = get_lambda_env(function_name, region)

    to_add = set(desired_env.keys()) - set(current_env.keys())
    to_update = {k for k in desired_env.keys() if k in current_env and current_env[k] != desired_env[k]}
    to_remove = set(current_env.keys()) - set(desired_env.keys())

    if not (to_add or to_update or to_remove):
        print("✅ Lambda environment is already in sync with .env")
        print(f"\n📊 Total variables: {len(desired_env)}")
        sys.exit(0)

    print("\n📊 Changes detected:")
    if to_add:
        print(f"  ➕ Adding: {len(to_add)} variable(s)")
        for var in sorted(to_add):
            print(f"     - {var}")
    if to_update:
        print(f"  🔄 Updating: {len(to_update)} variable(s)")
        for var in sorted(to_update):
            print(f"     - {var}")
    if to_remove:
        print(f"  ➖ Removing: {len(to_remove)} variable(s)")
        for var in sorted(to_remove):
            print(f"     - {var}")

    if to_remove:
        print("\n🗑️  Step 1: Removing obsolete variables to free up space...")
        cleaned_env = {k: v for k, v in current_env.items() if k in desired_env}
        print(f"   Current size: {calculate_size(current_env)} bytes")
        print(f"   After removal: {calculate_size(cleaned_env)} bytes")
        if update_lambda_env(function_name, cleaned_env, region):
            print("   ✅ Removed obsolete variables successfully")
            print("   ⏳ Waiting for Lambda to be ready...")
            wait_for_lambda_ready(function_name, region)
        else:
            print("   ❌ Failed to remove obsolete variables")
            sys.exit(1)

    if to_add or to_update:
        print("\n🔄 Step 2: Adding/updating required variables...")
        if not sync_in_batches(function_name, desired_env, region):
            sys.exit(1)

    final_env = get_lambda_env(function_name, region)

    print("\n✅ Environment variables synced successfully!")
    print(f"\n📊 Total variables on Lambda: {len(final_env)}")


if __name__ == "__main__":
    main()
