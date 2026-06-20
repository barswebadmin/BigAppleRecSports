#!/usr/bin/env python3
"""
Write Google service account JSON to AWS SSM Parameter Store.

Stores the minified JSON as a SecureString parameter at /google/service_account.

Usage:
    python scripts/secrets/write_google_service_account_to_ssm.py [--file path/to/google-service-account.json]

Environment variables required:
    AWS_ACCESS_KEY_ID       - AWS credentials
    AWS_SECRET_ACCESS_KEY    - AWS credentials
    AWS_DEFAULT_REGION       - AWS region (defaults to us-east-1)
"""

import os
import sys
import json
import argparse
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, BotoCoreError

import sys
from pathlib import Path

# Add shared utilities to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared_utilities"))
from paths import get_repo_root

project_root = get_repo_root()


def minify_json(json_data: dict) -> str:
    """Minify JSON by removing whitespace."""
    return json.dumps(json_data, separators=(',', ':'))


def write_service_account_to_ssm(
    json_file_path: Path,
    parameter_name: str = "/google/service_account",
    region: str = "us-east-1",
    dry_run: bool = False
) -> bool:
    """
    Write Google service account JSON to SSM Parameter Store.
    
    Args:
        json_file_path: Path to google-service-account.json file
        parameter_name: SSM parameter name (default: /google/service_account)
        region: AWS region (default: us-east-1)
        dry_run: If True, only show what would be written
    
    Returns:
        True if successful, False otherwise
    """
    if not json_file_path.exists():
        print(f"❌ File not found: {json_file_path}")
        return False
    
    # Read and parse JSON
    try:
        with open(json_file_path, 'r') as f:
            json_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {json_file_path}: {e}")
        return False
    
    # Minify JSON
    minified_json = minify_json(json_data)
    original_size = json_file_path.stat().st_size
    minified_size = len(minified_json.encode('utf-8'))
    
    print(f"📄 Original size: {original_size} bytes")
    print(f"📦 Minified size: {minified_size} bytes (saved {original_size - minified_size} bytes)")
    
    if minified_size > 4096:
        print(f"⚠️  WARNING: Minified size ({minified_size} bytes) exceeds SSM Standard parameter limit (4KB)")
        print("   Consider using SSM Advanced parameters (8KB limit) or compression")
        return False
    
    if dry_run:
        print(f"\n🔍 DRY RUN - Would write to SSM:")
        print(f"   Parameter: {parameter_name}")
        print(f"   Type: SecureString")
        print(f"   Size: {minified_size} bytes")
        print(f"   Region: {region}")
        print(f"\n   First 100 chars: {minified_json[:100]}...")
        return True
    
    # Write to SSM
    try:
        ssm = boto3.client("ssm", region_name=region)
        
        print(f"\n📤 Writing to SSM Parameter Store...")
        print(f"   Parameter: {parameter_name}")
        print(f"   Type: SecureString")
        print(f"   Region: {region}")
        
        response = ssm.put_parameter(
            Name=parameter_name,
            Value=minified_json,
            Type="SecureString",
            Overwrite=True,
            Description="Google service account credentials (minified JSON)"
        )
        
        version = response.get("Version", "unknown")
        print(f"✅ Successfully written (version: {version})")
        return True
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code == "AccessDeniedException":
            print(f"❌ Access denied. Check AWS credentials and IAM permissions.")
            print(f"   Required permission: ssm:PutParameter")
        else:
            print(f"❌ AWS error: {e}")
        return False
    except BotoCoreError as e:
        print(f"❌ AWS SDK error: {e}")
        print("   Make sure AWS credentials are configured")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Write Google service account JSON to AWS SSM Parameter Store"
    )
    parser.add_argument(
        "--file",
        type=str,
        default=str(project_root / "backend" / "google-service-account.json"),
        help="Path to google-service-account.json file"
    )
    parser.add_argument(
        "--parameter",
        type=str,
        default="/google/service_account",
        help="SSM parameter name (default: /google/service_account)"
    )
    parser.add_argument(
        "--region",
        type=str,
        default=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        help="AWS region (default: us-east-1 or AWS_DEFAULT_REGION)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be written without actually writing"
    )
    
    args = parser.parse_args()
    
    json_file = Path(args.file).resolve()
    
    success = write_service_account_to_ssm(
        json_file_path=json_file,
        parameter_name=args.parameter,
        region=args.region,
        dry_run=args.dry_run
    )
    
    if not success:
        sys.exit(1)
    
    if not args.dry_run:
        print(f"\n💡 To load this in your application, set environment variable:")
        print(f"   google.service_account_ssm={args.parameter}")
        print(f"\n   Or update config.py to load from SSM automatically.")


if __name__ == "__main__":
    main()
