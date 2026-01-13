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
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent.parent

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
    if args.wait:
        success = wait_for_deployment(api_key, service_id, deploy_id)
        if not success:
            sys.exit(1)
        print("\n🎉 Deployment completed successfully!")
    else:
        print("\n✅ Deployment triggered successfully!")
        print("   (Use --wait to wait for completion, or check Render dashboard)")


if __name__ == "__main__":
    main()
