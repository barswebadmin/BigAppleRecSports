#!/usr/bin/env python3
"""
Unified Render deployment script.

Handles requirements validation, secret syncing (via sync_render_secrets),
and deployment triggering. Works identically in local and CI environments.

Usage:
    # Deploy with secrets from .env file
    python scripts/deployment/deploy_backend.py

    # Deploy with secrets from AWS SSM Parameter Store
    python scripts/deployment/deploy_backend.py --from-ssm

    # Sync secrets only (no deployment)
    python scripts/deployment/deploy_backend.py --secrets-only

    # Dry run (show what would change)
    python scripts/deployment/deploy_backend.py --dry-run

Options:
    --from-ssm       Use AWS SSM Parameter Store instead of .env file
    --secrets-only   Sync secrets but don't trigger deployment
    --dry-run        Show what would change without making changes
    --wait           Wait for deployment to complete (local only, CI uses GitHub Action)
    --skip-validation Skip requirements.txt validation

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
import subprocess
import argparse
import time
import re
import json
import urllib.request
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent.parent

# Add project root to path for imports
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    import requests
except ImportError:
    print("❌ Missing required dependencies. Install with:")
    print("   pip install requests")
    sys.exit(1)


def validate_requirements() -> bool:
    """Validate backend requirements.txt can be installed."""
    requirements_file = project_root / "backend" / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"⚠️  {requirements_file} not found, skipping validation")
        return True
    
    print("🔍 Validating backend/requirements.txt...")
    try:
        result = subprocess.run(
            ["pip", "install", "--dry-run", "-r", str(requirements_file)],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print("✅ Requirements validation successful")
            return True
        else:
            print(f"❌ Requirements validation failed:")
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("❌ Requirements validation timed out")
        return False
    except Exception as e:
        print(f"❌ Requirements validation error: {e}")
        return False


def sync_secrets(from_ssm: bool = False, dry_run: bool = False) -> bool:
    """Sync secrets using the dedicated sync script."""
    sync_script = project_root / "scripts" / "secrets" / "sync_render_secrets.py"
    
    if not sync_script.exists():
        print(f"❌ Sync script not found: {sync_script}")
        return False
    
    cmd = [sys.executable, str(sync_script)]
    
    if from_ssm:
        cmd.append("--from-ssm")
    
    if dry_run:
        cmd.append("--dry-run")
    
    print("🔐 Syncing secrets...")
    print()
    
    result = subprocess.run(cmd, cwd=project_root)
    
    return result.returncode == 0


def trigger_deployment(api_key: str, service_id: str) -> Optional[str]:
    """Trigger a new deployment and return deployment ID."""
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


def get_deployment_status(api_key: str, service_id: str, deploy_id: str) -> Optional[str]:
    """Get the status of a deployment."""
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


def wait_for_deployment(api_key: str, service_id: str, deploy_id: str, timeout: int = 600) -> bool:
    """Wait for deployment to complete."""
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


def increment_backend_version() -> bool:
    """Increment backend version and commit changes.
    
    Returns:
        True if version was incremented and committed successfully, False otherwise
    """
    version_file = project_root / "backend" / "version.json"
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
    
    if not is_ci or not version_file.exists():
        return False
    
    print("\n📈 Incrementing backend version after successful deployment...")
    
    # Determine bump type from PR title (if available) or commit messages
    # Default to "build" to increment build number without changing semantic version
    # Only change semantic version if PR title or commit message explicitly indicates it
    bump_type = "build"  # Default - just increment build number
    
    pr_title = None
    # Try to get PR title from merge commit
    try:
        # Get merge commit message
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            commit_msg = result.stdout
            
            # Extract PR number from merge commit (format: "Merge pull request #123 from ...")
            pr_match = re.search(r'Merge pull request #(\d+)', commit_msg)
            if pr_match:
                pr_number = pr_match.group(1)
                # Try to get PR title using GitHub CLI
                try:
                    gh_result = subprocess.run(
                        ["gh", "pr", "view", pr_number, "--json", "title", "--jq", ".title"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if gh_result.returncode == 0 and gh_result.stdout.strip():
                        pr_title = gh_result.stdout.strip()
                        print(f"📋 Found PR title: {pr_title}")
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    # GitHub CLI not available, try GitHub API directly
                    try:
                        github_token = os.getenv("GITHUB_TOKEN")
                        if github_token:
                            repo = os.getenv("GITHUB_REPOSITORY", "bigapplerecsports/BigAppleRecSports")
                            url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
                            req = urllib.request.Request(url)
                            req.add_header("Authorization", f"token {github_token}")
                            req.add_header("Accept", "application/vnd.github.v3+json")
                            with urllib.request.urlopen(req, timeout=10) as response:
                                pr_data = json.loads(response.read())
                                pr_title = pr_data.get("title", "")
                                if pr_title:
                                    print(f"📋 Found PR title via API: {pr_title}")
                    except Exception:
                        # API call failed, fall back to commit message
                        pass
                except Exception:
                    # Other error, fall back to commit message
                    pass
            
            # Check PR title for version keywords (case-insensitive)
            # Look for "major", "minor", or "patch" as standalone words or in brackets/colons
            if pr_title:
                pr_title_lower = pr_title.lower()
                # Use word boundaries to match standalone words
                if re.search(r'\b(major|breaking)\b', pr_title_lower) or '[major]' in pr_title_lower or '[breaking]' in pr_title_lower:
                    bump_type = "major"
                elif re.search(r'\bminor\b', pr_title_lower) or '[minor]' in pr_title_lower:
                    bump_type = "minor"
                elif re.search(r'\bpatch\b', pr_title_lower) or '[patch]' in pr_title_lower:
                    bump_type = "patch"
            else:
                # Fallback: check commit message for keywords
                commit_msg_lower = commit_msg.lower()
                if any(kw in commit_msg_lower for kw in ["breaking", "major"]):
                    bump_type = "major"
                elif any(kw in commit_msg_lower for kw in ["feat:", "feature:", "add:", "new:"]):
                    bump_type = "minor"
                elif any(kw in commit_msg_lower for kw in ["fix:", "bugfix:", "patch:", "hotfix:"]):
                    bump_type = "patch"
    except Exception as e:
        print(f"⚠️  Could not determine bump type from PR/commit: {e}")
        pass  # Default to build if we can't determine
    
    # Get commit messages for changelog
    try:
        result = subprocess.run(
            ["git", "log", "-5", "--pretty=%B"],
            capture_output=True,
            text=True,
            timeout=5
        )
        commit_messages = result.stdout.strip() if result.returncode == 0 else "Deployment"
    except Exception:
        commit_messages = "Deployment"
    
    # Increment version using version_manager
    try:
        from scripts.deployment.version_manager import process_component
        
        if not process_component(
            str(version_file),
            bump_type,
            commit_messages.split('\n') if commit_messages else ["Deployment"],
            None
        ):
            print("⚠️  Version increment failed")
            return False
        
        print(f"✅ Version incremented ({bump_type} bump)")
    except Exception as e:
        print(f"⚠️  Version increment error: {e}")
        return False
    
    # Commit version increment to merge commit (amend to include in same commit)
    try:
        # Check if version.json was modified
        result = subprocess.run(
            ["git", "diff", "--quiet", str(version_file)],
            cwd=project_root
        )
        if result.returncode != 0:  # File was modified
            print("📝 Including version increment in merge commit...")
            # Stage the version file
            subprocess.run(
                ["git", "add", str(version_file)],
                cwd=project_root,
                check=True
            )
            # Amend to the current HEAD (merge commit) to include it in the same commit
            subprocess.run(
                ["git", "commit", "--amend", "--no-edit"],
                cwd=project_root,
                check=True
            )
            # Force push with lease to update the merge commit (safe in CI)
            subprocess.run(
                ["git", "push", "origin", "main", "--force-with-lease"],
                cwd=project_root,
                check=True
            )
            print("✅ Version increment included in merge commit")
            return True
    except Exception as e:
        print(f"⚠️  Failed to include version increment in commit: {e}")
        return False
    
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Deploy to Render with unified secret syncing and deployment"
    )
    parser.add_argument(
        "--from-ssm",
        action="store_true",
        help="Use AWS SSM Parameter Store instead of .env file"
    )
    parser.add_argument(
        "--secrets-only",
        action="store_true",
        help="Sync secrets but don't trigger deployment"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without making changes"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for deployment to complete (local only, CI uses GitHub Action)"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip requirements.txt validation"
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
    
    print("🚀 Render Deployment")
    print("=" * 50)
    print(f"   Service ID: {service_id}")
    if args.dry_run:
        print("   Mode: DRY RUN")
    elif args.secrets_only:
        print("   Mode: SECRETS ONLY")
    else:
        print("   Mode: FULL DEPLOYMENT")
    print()
    
    # Validate requirements (unless skipped)
    if not args.skip_validation:
        if not validate_requirements():
            print("❌ Requirements validation failed")
            sys.exit(1)
        print()
    
    # Sync secrets
    secrets_synced = sync_secrets(from_ssm=args.from_ssm, dry_run=args.dry_run)
    
    if not secrets_synced:
        print("❌ Secret sync failed")
        sys.exit(1)
    
    # Deploy if requested
    if args.secrets_only:
        print("\n✅ Secrets synced! Ready for deployment.")
        if not args.dry_run:
            print("🚀 To deploy now, run: python scripts/deployment/deploy_backend.py")
        return
    
    if args.dry_run:
        print("\n🔍 Dry run complete - no deployment triggered")
        return
    
    # Trigger deployment
    print("\n🚀 Triggering deployment...")
    deploy_id = trigger_deployment(api_key, service_id)
    
    if not deploy_id:
        print("❌ Failed to trigger deployment")
        sys.exit(1)
    
    # Wait for deployment if requested (local only)
    deployment_success = False
    if args.wait:
        deployment_success = wait_for_deployment(api_key, service_id, deploy_id)
        if not deployment_success:
            print("\n❌ Deployment failed - version will not be incremented")
            sys.exit(1)
        print("\n🎉 Deployment completed successfully!")
    else:
        print("\n✅ Deployment triggered successfully!")
        print("   (Use --wait to wait for completion, or check Render dashboard)")
        # If not waiting, assume success (deployment was triggered)
        deployment_success = True
    
    # Increment version only after successful deployment (CI/GH workflows only)
    if deployment_success and not args.dry_run and not args.secrets_only:
        increment_backend_version()


if __name__ == "__main__":
    main()
