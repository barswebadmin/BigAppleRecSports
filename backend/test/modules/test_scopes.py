"""
Utility to test which Google API scopes are authorized for a service account.

This script attempts to get an access token for each scope individually
to determine which scopes are actually authorized in Google Admin Console.
"""

import sys
import json
from pathlib import Path
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

def test_scope(credentials_file: Path, subject: str, scope: str) -> tuple[bool, str]:
    """
    Test if a single scope is authorized.
    
    Returns:
        (success: bool, message: str)
    """
    try:
        creds = Credentials.from_service_account_file(
            filename=str(credentials_file),
            subject=subject,
            scopes=[scope]
        )
        
        # Try to refresh to get a token (this will fail if scope not authorized)
        # Use explicit timeout to avoid httplib2 timeout issues
        request_obj = Request(timeout=60)
        creds.refresh(request_obj)
        
        return True, f"✅ {scope} - AUTHORIZED"
    except RefreshError as e:
        error_msg = str(e)
        if 'unauthorized_client' in error_msg.lower():
            return False, f"❌ {scope} - NOT AUTHORIZED"
        else:
            return False, f"⚠️ {scope} - ERROR: {error_msg[:100]}"
    except Exception as e:
        return False, f"⚠️ {scope} - ERROR: {type(e).__name__}: {str(e)[:100]}"


def test_all_scopes(credentials_file: Path, subject: str, scopes: list[str]) -> dict[str, tuple[bool, str]]:
    """
    Test all scopes and return results.
    
    Returns:
        dict mapping scope to (success, message) tuple
    """
    results = {}
    
    print(f"[INFO] Testing {len(scopes)} scopes...", file=sys.stderr)
    print(f"[INFO] Service Account: {subject}", file=sys.stderr)
    print(f"[INFO] ", file=sys.stderr)
    
    for i, scope in enumerate(scopes, 1):
        print(f"[INFO] [{i}/{len(scopes)}] Testing: {scope}...", file=sys.stderr, end=' ')
        success, message = test_scope(credentials_file, subject, scope)
        results[scope] = (success, message)
        print(message, file=sys.stderr)
    
    return results


def main():
    """Main entry point for scope testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Google API scope authorization")
    parser.add_argument(
        '--credentials-file',
        type=Path,
        default=Path(__file__).parent.parent.parent.parent / "google-service-account.json",
        help="Path to service account JSON file"
    )
    parser.add_argument(
        '--subject',
        help="Subject (user email) for domain-wide delegation. If not provided, will read from credentials file."
    )
    parser.add_argument(
        '--scopes',
        nargs='+',
        help="Scopes to test. If not provided, will test common scopes."
    )
    
    args = parser.parse_args()
    
    # Load credentials file
    if not args.credentials_file.exists():
        print(f"[ERROR] Credentials file not found: {args.credentials_file}", file=sys.stderr)
        sys.exit(1)
    
    with open(args.credentials_file) as f:
        creds_data = json.load(f)
    
    # Get subject
    subject = args.subject or creds_data.get('subject')
    if not subject:
        print(f"[ERROR] No subject provided and not found in credentials file", file=sys.stderr)
        sys.exit(1)
    
    # Get scopes to test
    if args.scopes:
        scopes = args.scopes
    else:
        # Default: test all scopes used by the application
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/script.scriptapp',
            'https://www.googleapis.com/auth/admin.directory.group',
            'https://www.googleapis.com/auth/admin.directory.group.member',
            'https://www.googleapis.com/auth/admin.directory.user',
            'https://www.googleapis.com/auth/gmail.readonly',
        ]
    
    # Test all scopes
    results = test_all_scopes(args.credentials_file, subject, scopes)
    
    # Print summary
    print(f"[INFO] ", file=sys.stderr)
    print(f"[INFO] ========== SUMMARY ==========", file=sys.stderr)
    
    authorized = [scope for scope, (success, _) in results.items() if success]
    unauthorized = [scope for scope, (success, _) in results.items() if not success]
    
    print(f"[INFO] Authorized: {len(authorized)}/{len(scopes)}", file=sys.stderr)
    if authorized:
        print(f"[INFO] ", file=sys.stderr)
        print(f"[INFO] ✅ AUTHORIZED SCOPES:", file=sys.stderr)
        for scope in authorized:
            print(f"[INFO]   {scope}", file=sys.stderr)
    
    if unauthorized:
        print(f"[INFO] ", file=sys.stderr)
        print(f"[INFO] ❌ NOT AUTHORIZED SCOPES:", file=sys.stderr)
        for scope in unauthorized:
            print(f"[INFO]   {scope}", file=sys.stderr)
        print(f"[INFO] ", file=sys.stderr)
        print(f"[INFO] TO FIX:", file=sys.stderr)
        print(f"[INFO] 1. Go to Google Admin Console: https://admin.google.com", file=sys.stderr)
        print(f"[INFO] 2. Navigate: Security > API Controls > Domain-wide Delegation", file=sys.stderr)
        print(f"[INFO] 3. Find service account: {creds_data.get('client_email')}", file=sys.stderr)
        print(f"[INFO] 4. Add the following scopes (one per line):", file=sys.stderr)
        for scope in unauthorized:
            print(f"[INFO]    {scope}", file=sys.stderr)
    
    print(f"[INFO] =============================", file=sys.stderr)
    
    # Return exit code based on results
    sys.exit(0 if len(unauthorized) == 0 else 1)


if __name__ == '__main__':
    main()
