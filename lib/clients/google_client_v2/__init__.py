"""Google API unified client with service namespaces."""

from .client import GoogleClient
from .scopes import (
    DirectoryScopes,
    SheetsScopes,
    DriveScopes,
    GmailScopes,
    CalendarScopes,
    ScriptsScopes,
)

__all__ = [
    "GoogleClient",
    "DirectoryScopes",
    "SheetsScopes",
    "DriveScopes",
    "GmailScopes",
    "CalendarScopes",
    "ScriptsScopes",
]
