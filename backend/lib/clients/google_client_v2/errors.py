"""Error handling for Google API operations."""

import logging
import sys
from typing import NoReturn

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


def handle_refresh_error(error: RefreshError, scopes: list[str] | None = None) -> NoReturn:
    """Handle credential refresh errors with diagnostic output."""
    logger.error(f"Credential refresh failed: {error}", exc_info=True)
    
    print(f"\n❌ CREDENTIAL REFRESH ERROR", file=sys.stderr)
    print(f"Error: {error}", file=sys.stderr)
    
    if scopes:
        print(f"\nRequested scopes ({len(scopes)}):", file=sys.stderr)
        for scope in scopes:
            print(f"  • {scope}", file=sys.stderr)
        print(f"\n💡 Verify these scopes are authorized in Google Admin Console:", file=sys.stderr)
        print(f"   Security > API Controls > Domain-wide Delegation", file=sys.stderr)
    
    raise


def handle_http_error(error: HttpError, scopes: list[str] | None = None) -> NoReturn:
    """Handle HTTP errors from Google API with diagnostic output."""
    status = error.resp.status
    reason = error.reason
    
    logger.error(f"Google API HTTP error {status}: {reason}", exc_info=True)
    
    print(f"\n❌ GOOGLE API ERROR", file=sys.stderr)
    print(f"Status: {status}", file=sys.stderr)
    print(f"Reason: {reason}", file=sys.stderr)
    
    if status == 403 and scopes:
        print(f"\n💡 This may be a scope authorization issue.", file=sys.stderr)
        print(f"Required scopes:", file=sys.stderr)
        for scope in scopes:
            print(f"  • {scope}", file=sys.stderr)
    
    if hasattr(error, 'error_details') and error.error_details:
        print(f"\nDetails: {error.error_details}", file=sys.stderr)
    
    raise
