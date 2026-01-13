#!/usr/bin/env python3
"""
GitHub Secrets Manager
Sync environment variables to GitHub repository secrets using the GitHub API
"""

import os
import sys
import subprocess
from typing import Dict, List


def run_command(cmd: List[str]) -> str:
    """Run a command and return its output"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd)}")
        print(f"Error: {e.stderr}")
        sys.exit(1)


def check_gh_cli():
    """Check if GitHub CLI is installed and authenticated"""
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ GitHub CLI (gh) is not installed.")
        print("📥 Install with: brew install gh")
        sys.exit(1)

    try:
        subprocess.run(["gh", "auth", "status"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("❌ Not authenticated with GitHub CLI.")
        print("🔐 Run: gh auth login")
        sys.exit(1)

    print("✅ GitHub CLI is ready")


def load_env_file(env_file: str) -> Dict[str, str]:
    """Load environment variables from a .env file"""
    env_vars = {}

    if not os.path.exists(env_file):
        print(f"❌ Environment file not found: {env_file}")
        return env_vars

    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                # Remove quotes if present
                value = value.strip("\"'")
                env_vars[key] = value

    return env_vars


def sync_secret(
    secret_name: str, secret_value: str, repo: str, environment: str
) -> bool:
    """Sync a single secret to GitHub"""
    if not secret_value:
        print(f"⚠️  Skipping {secret_name} (empty value)")
        return False

    try:
        cmd = ["gh", "secret", "set", secret_name, "--repo", repo, "--env", environment]
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
        process.communicate(input=secret_value)

        if process.returncode == 0:
            print(f"🔐 Synced: {secret_name}")
            return True
        else:
            print(f"❌ Failed to sync: {secret_name}")
            return False
    except Exception as e:
        print(f"❌ Error syncing {secret_name}: {e}")
        return False


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Sync secrets to GitHub repository")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument(
        "--environment", default="production", help="GitHub environment"
    )
    parser.add_argument(
        "--repo", default="barswebadmin/BigAppleRecSports", help="GitHub repository"
    )
    parser.add_argument("--secrets", nargs="+", help="Specific secrets to sync")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without doing it",
    )

    args = parser.parse_args()

    print("🔑 GitHub Secrets Manager")
    print(f"📂 Repository: {args.repo}")
    print(f"🌍 Environment: {args.environment}")
    print(f"📄 Env file: {args.env_file}")
    print()

    # Check prerequisites
    check_gh_cli()

    # Default secrets to sync (only secrets needed for GitHub workflows)
    default_secrets = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "RENDER_API_KEY",
        "RENDER_SERVICE_ID",
    ]

    secrets_to_sync = args.secrets if args.secrets else default_secrets

    # Load environment variables
    env_vars = load_env_file(args.env_file)
    if not env_vars:
        print(f"❌ No environment variables found in {args.env_file}")
        sys.exit(1)

    print(f"📋 Found {len(env_vars)} environment variables")
    print()

    # Sync secrets
    synced = 0
    skipped = 0

    for secret in secrets_to_sync:
        if secret in env_vars:
            if args.dry_run:
                print(f"🔍 Would sync: {secret}")
                synced += 1
            else:
                if sync_secret(secret, env_vars[secret], args.repo, args.environment):
                    synced += 1
                else:
                    skipped += 1
        else:
            print(f"⚠️  Skipping {secret} (not found in {args.env_file})")
            skipped += 1

    print()
    print("📊 Summary:")
    print(f"   ✅ {'Would sync' if args.dry_run else 'Synced'}: {synced} secrets")
    print(f"   ⚠️  Skipped: {skipped} secrets")
    print()
    print(
        f"🔍 View in GitHub: https://github.com/{args.repo}/settings/environments/{args.environment}"
    )


if __name__ == "__main__":
    main()
