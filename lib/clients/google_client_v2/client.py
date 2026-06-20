"""Google API unified client with service namespaces."""

import hashlib
import json
import logging
import os
import time
from typing import TYPE_CHECKING, Any

from google.auth.exceptions import RefreshError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .errors import handle_http_error, handle_refresh_error
from .scopes import DirectoryScopes, DriveScopes, GmailScopes, SheetsScopes

if TYPE_CHECKING:
    from shared_utilities.config import Config

logger = logging.getLogger(__name__)


class GoogleClient:
    """Unified Google API client with service-specific namespaces.

    Provides:
    - Credential caching per (scopes, subject) combination
    - Service caching per (api, version, scopes, subject)
    - Service namespaces: client.drive.*, client.sheets.*, client.gmail.*, etc.
    - Flexible subject/scopes (default or per-call override)

    Usage:
        # Default subject from GOOGLE_DEFAULT_ADMIN_EMAIL env var
        client = GoogleClient()
        files = client.drive.list_folder_files(folder_id="abc123")

        # Gmail operations
        messages = client.gmail.list_messages(query="is:unread")
        client.gmail.send_message(message_body={"raw": "..."})

        # Override subject per call
        files = client.drive.list_folder_files(
            folder_id="abc123",
            subject="other@example.com"
        )

        # Raw service access (for custom queries)
        drive = client.service("drive", "v3", subject="joe@example.com", scopes=[DriveScopes.readonly])
        custom = drive.files().list(q="...").execute()
    """

    def __init__(
        self,
        sa_info: dict | None = None,
        config: "Config | None" = None,
    ):
        """Initialize Google API client.

        Default subject is resolved from GOOGLE_DEFAULT_ADMIN_EMAIL environment variable.

        Args:
            sa_info: Service account credentials dict (optional)
            config: Config object with google.service_account (optional)

        If neither sa_info nor config provided, loads from GOOGLE__SERVICE_ACCOUNT env var.
        """
        self._cred_cache: dict[str, service_account.Credentials] = {}
        self._service_cache: dict[str, Any] = {}

        if sa_info is not None:
            self._sa_info = dict(sa_info)
        elif config is not None:
            self._sa_info = dict(config.google.service_account)
        else:
            raw = os.environ.get("GOOGLE__SERVICE_ACCOUNT", "")
            if not raw:
                raise RuntimeError("GOOGLE__SERVICE_ACCOUNT not set in environment")
            self._sa_info = json.loads(raw)

        self.default_subject = self._resolve_default_subject()

        self._initialize_services()

    def _resolve_default_subject(self) -> str:
        """Resolve default subject email for domain-wide delegation.

        Reads from GOOGLE_DEFAULT_ADMIN_EMAIL environment variable.

        Returns:
            Email address to impersonate

        Raises:
            RuntimeError: If GOOGLE_DEFAULT_ADMIN_EMAIL not set
        """
        subject = os.environ.get("GOOGLE_DEFAULT_ADMIN_EMAIL")
        if not subject:
            raise RuntimeError(
                "GOOGLE_DEFAULT_ADMIN_EMAIL environment variable not set.\n"
                "This is required for domain-wide delegation."
            )
        return subject

    def _initialize_services(self) -> None:
        """Initialize service namespace objects."""
        from .services import Drive, Sheets, Directory, Gmail

        self.drive = Drive(self)
        self.sheets = Sheets(self)
        self.directory = Directory(self)
        self.gmail = Gmail(self)

    @staticmethod
    def _cache_key(*parts: str) -> str:
        """Generate cache key from string parts."""
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]

    def _handle_api_errors(self, operation: Any, scopes: list[str] | None = None) -> Any:
        """Execute operation with centralized error handling."""
        try:
            return operation()
        except RefreshError as e:
            handle_refresh_error(e, scopes)
        except HttpError as e:
            handle_http_error(e, scopes)

    def _credentials(
        self,
        scopes: list[str],
        subject: str,
    ) -> service_account.Credentials:
        """Get or create cached credentials for scopes + subject combination.

        Args:
            scopes: List of OAuth scopes
            subject: Email to impersonate (domain-wide delegation)

        Returns:
            Cached or newly created service account credentials
        """
        key = self._cache_key(*sorted(scopes), subject)

        if key not in self._cred_cache:
            self._cred_cache[key] = (
                service_account.Credentials.from_service_account_info(
                    self._sa_info,
                    scopes=scopes,
                    subject=subject,
                )
            )
            logger.debug("Built credentials for %s (%d scopes)", subject, len(scopes))

        return self._cred_cache[key]

    def service(
        self,
        api: str,
        version: str,
        subject: str,
        scopes: list[str] | None = None,
    ) -> Any:
        """Get or create cached Google API service.

        Args:
            api: API name (e.g., "drive", "sheets", "admin", "gmail")
            version: API version (e.g., "v3", "v4", "directory_v1")
            subject: Email to impersonate
            scopes: OAuth scopes (uses defaults if not provided)

        Returns:
            Google API Resource object
        """
        if scopes is None:
            scopes = self._default_scopes_for_api(api)

        key = self._cache_key(api, version, *sorted(scopes), subject)

        if key not in self._service_cache:
            creds = self._credentials(scopes, subject)
            try:
                self._service_cache[key] = build(api, version, credentials=creds)
                logger.debug("Built service %s %s for %s", api, version, subject)
            except RefreshError as e:
                handle_refresh_error(e, scopes)
            except HttpError as e:
                handle_http_error(e, scopes)

        return self._service_cache[key]

    def _default_scopes_for_api(self, api: str) -> list[str]:
        """Get default scopes for an API."""
        defaults = {
            "drive": [DriveScopes.readonly],
            "sheets": [SheetsScopes.readonly],
            "admin": [DirectoryScopes.groups_readonly],
            "gmail": [GmailScopes.readonly],
        }

        scopes = defaults.get(api)
        if not scopes:
            raise ValueError(f"No default scopes for {api!r} — pass scopes explicitly")

        return scopes

    def execute(
        self,
        request: Any,
        scopes: list[str] | None = None,
    ) -> dict:
        """Execute a prepared API request with error handling."""
        return self._handle_api_errors(request.execute, scopes)

    def paginate(
        self,
        api_method: Any,
        result_key: str,
        scopes: list[str] | None = None,
        **params: Any,
    ) -> list[Any]:
        """Exhaust all pages of a paginated API call.

        Args:
            api_method: Bound method (e.g., service.files().list)
            result_key: Key in response containing items (e.g., "files", "groups")
            scopes: Scopes for error diagnostics (optional)
            **params: Parameters passed to api_method on each call

        Returns:
            Combined list of all items from all pages
        """
        items: list[Any] = []
        page_token: str | None = None

        while True:
            if page_token:
                params["pageToken"] = page_token

            resp = self._handle_api_errors(
                lambda: api_method(**params).execute(), scopes
            )

            items.extend(resp.get(result_key, []))
            page_token = resp.get("nextPageToken")

            if not page_token:
                break

        return items

    def batch(
        self,
        service: Any,
        requests: list[Any],
        scopes: list[str] | None = None,
    ) -> list[dict]:
        """Execute batch requests, auto-chunking into groups of 50 with 1s delay.

        Args:
            service: Google API service Resource
            requests: List of prepared requests (any size)
            scopes: Scopes for error diagnostics (optional)

        Returns:
            All responses (callback execution order, may differ from input order)
        """
        all_results: list[dict] = []

        for batch_idx in range(0, len(requests), 50):
            if batch_idx > 0:
                time.sleep(1)

            chunk = requests[batch_idx:batch_idx + 50]
            chunk_results: list[dict] = []
            chunk_errors: list[Exception] = []

            batch_req = service.new_batch_http_request(
                callback=lambda _id, resp, exc, r=chunk_results, e=chunk_errors: (
                    e.append(exc) if exc else r.append(resp)
                )
            )
            for req in chunk:
                batch_req.add(req)

            self._handle_api_errors(batch_req.execute, scopes)

            if chunk_errors:
                exc = chunk_errors[0]
                if isinstance(exc, HttpError):
                    handle_http_error(exc, scopes)
                if isinstance(exc, RefreshError):
                    handle_refresh_error(exc, scopes)
                raise exc

            all_results.extend(chunk_results)

        return all_results
