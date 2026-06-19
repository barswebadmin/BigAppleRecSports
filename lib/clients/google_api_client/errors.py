"""Google API error handling and diagnostics."""

import json
import sys

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError


def _print_scope_fix(
    scopes: list[str], uri: str = ""
) -> None:
    print("[ERROR] TO FIX:", file=sys.stderr)
    print(
        "[ERROR] 1. Go to Google Admin Console:"
        " https://admin.google.com",
        file=sys.stderr,
    )
    print(
        "[ERROR] 2. Navigate: Security > API Controls"
        " > Domain-wide Delegation",
        file=sys.stderr,
    )
    print(
        "[ERROR] 3. Find your service account and ensure"
        " ALL scopes below are authorized:",
        file=sys.stderr,
    )
    for scope in scopes:
        print(f"[ERROR]    {scope}", file=sys.stderr)
    if uri:
        print(
            f"[ERROR] 4. Endpoint attempted: {uri}",
            file=sys.stderr,
        )


def handle_refresh_error(
    error: RefreshError, scopes: list[str] | None = None
) -> None:
    """Diagnose and re-raise a credential refresh error."""
    msg = str(error)
    print(
        "[ERROR] ══════════ CREDENTIAL REFRESH ERROR ══════════",
        file=sys.stderr,
    )
    print(
        f"[ERROR] {type(error).__name__}: {msg}", file=sys.stderr
    )
    if "unauthorized_client" in msg.lower():
        print(
            "[ERROR] Service account not authorized"
            " for domain-wide delegation.",
            file=sys.stderr,
        )
        if scopes:
            _print_scope_fix(scopes)
    else:
        print(
            "[ERROR] Possible causes: DWD not enabled,"
            " invalid credentials, network.",
            file=sys.stderr,
        )
    print(
        "[ERROR] ═════════════════════════════════════════════",
        file=sys.stderr,
    )
    raise error


def handle_http_error(
    error: HttpError, scopes: list[str] | None = None
) -> None:
    """Diagnose and re-raise a Google API HTTP error."""
    status = error.resp.status
    content = (
        error.content.decode("utf-8") if error.content else ""
    )
    print(
        f"[ERROR] ══════════ GOOGLE API HTTP {status} ══════════",
        file=sys.stderr,
    )
    print(f"[ERROR] {error.reason}", file=sys.stderr)
    if status == 403 and scopes:
        print(
            "[ERROR] Likely a scope/permission error.",
            file=sys.stderr,
        )
        _print_scope_fix(scopes, uri=error.uri or "")
    if content:
        try:
            print(
                f"[ERROR] {json.dumps(json.loads(content), indent=2)}",
                file=sys.stderr,
            )
        except (ValueError, TypeError):
            print(
                f"[ERROR] {content[:500]}", file=sys.stderr
            )
    print(
        "[ERROR] ═════════════════════════════════════════════",
        file=sys.stderr,
    )
    raise error
