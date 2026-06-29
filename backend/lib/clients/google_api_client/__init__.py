"""Google API client package."""

import json
import os

from google.oauth2 import service_account
from googleapiclient.discovery import Resource, build

from .client import GoogleApiClient
from .errors import handle_http_error, handle_refresh_error
from .scopes import (
    DEFAULT_SCOPES,
    CalendarScopes,
    DirectoryScopes,
    DriveScopes,
    GmailScopes,
    ScriptsScopes,
    SheetsScopes,
)


def build_service(
    api: str,
    version: str,
    subject: str,
    scopes: list[str] | None = None,
) -> Resource:
    """Build a one-shot Google API service using httplib2 transport.

    Intended for standalone uv run scripts that already depend on httplib2.
    For long-running processes, prefer GoogleApiClient.service() which caches.
    """
    import google_auth_httplib2
    import httplib2

    resolved = scopes or DEFAULT_SCOPES.get(api)
    if not resolved:
        raise ValueError(
            f"No default scopes for {api!r} — pass scopes= explicitly"
        )

    info = json.loads(os.environ["GOOGLE__SERVICE_ACCOUNT"])
    info.pop("subject", None)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=resolved, subject=subject,
    )
    authed_http = google_auth_httplib2.AuthorizedHttp(
        creds, http=httplib2.Http(timeout=120)
    )
    return build(api, version, http=authed_http)


__all__ = [
    "GoogleApiClient",
    "build_service",
    "handle_http_error",
    "handle_refresh_error",
    "CalendarScopes",
    "DirectoryScopes",
    "DriveScopes",
    "GmailScopes",
    "ScriptsScopes",
    "SheetsScopes",
    "DEFAULT_SCOPES",
]
