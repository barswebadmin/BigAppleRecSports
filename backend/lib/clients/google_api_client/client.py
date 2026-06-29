"""Google API client with credential/service caching, error diagnostics,
pagination, and batch execution."""

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
from .scopes import DEFAULT_SCOPES, SheetsScopes

if TYPE_CHECKING:
    from shared_utilities.config import Config

logger = logging.getLogger(__name__)


class GoogleApiClient:
    """Google API client with credential/service caching, error
    diagnostics, pagination, and batch support.

    Credentials are cached per (scopes, subject) combination.
    Services are cached per (api, version, scopes, subject).
    Both caches are instance-level — create one client and reuse it.
    """

    def __init__(
        self,
        sa_info: dict | None = None,
        config: "Config | None" = None,
    ) -> None:
        self._cred_cache: dict[str, service_account.Credentials] = {}
        self._service_cache: dict[str, Any] = {}
        if sa_info is not None:
            self._sa_info = dict(sa_info)
        elif config is not None:
            self._sa_info = dict(config.google.service_account)
        else:
            raw = os.environ.get("GOOGLE__SERVICE_ACCOUNT", "")
            if not raw:
                raise RuntimeError(
                    "GOOGLE__SERVICE_ACCOUNT not set in environment"
                )
            self._sa_info = json.loads(raw)
        self._sa_info.pop("subject", None)

    @staticmethod
    def _cache_key(*parts: str) -> str:
        return hashlib.sha256(
            "|".join(parts).encode()
        ).hexdigest()[:16]

    def _handle_api_errors(self, operation: Any, scopes: list[str] | None = None) -> Any:
        """Execute operation with centralized error handling."""
        try:
            return operation()
        except RefreshError as e:
            handle_refresh_error(e, scopes)
        except HttpError as e:
            handle_http_error(e, scopes)

    def _credentials(
        self, scopes: list[str], subject: str
    ) -> service_account.Credentials:
        key = self._cache_key(*sorted(scopes), subject)
        if key not in self._cred_cache:
            self._cred_cache[key] = (
                service_account.Credentials.from_service_account_info(
                    self._sa_info, scopes=scopes, subject=subject,
                )
            )
            logger.debug(
                "Built credentials for %s (%d scopes)",
                subject,
                len(scopes),
            )
        return self._cred_cache[key]

    def service(
        self,
        api: str,
        version: str,
        subject: str,
        scopes: list[str] | None = None,
    ) -> Any:
        """Return a cached Google API service resource.

        Args:
            api:     e.g. "gmail", "drive", "calendar", "admin", "sheets"
            version: e.g. "v1", "v3", "v4", "directory_v1"
            subject: workspace user email to impersonate
            scopes:  override default scopes for this API
        """
        resolved = scopes or DEFAULT_SCOPES.get(api)
        if not resolved:
            raise ValueError(
                f"No default scopes for {api!r}"
                " — pass scopes= explicitly"
            )

        key = self._cache_key(
            api, version, *sorted(resolved), subject
        )
        if key not in self._service_cache:
            creds = self._credentials(resolved, subject)
            try:
                self._service_cache[key] = build(
                    api, version, credentials=creds
                )
                logger.debug(
                    "Built service %s %s for %s",
                    api,
                    version,
                    subject,
                )
            except RefreshError as e:
                handle_refresh_error(e, resolved)
            except HttpError as e:
                handle_http_error(e, resolved)
        return self._service_cache[key]

    def execute(
        self,
        request: Any,
        scopes: list[str] | None = None,
    ) -> dict:
        """Execute a single prepared API request with error handling."""
        return self._handle_api_errors(request.execute, scopes)

    def paginate(
        self,
        api_method: Any,
        result_key: str,
        scopes: list[str] | None = None,
        **params: Any,
    ) -> list[Any]:
        """Exhaust all pages of a paginated Google API call.

        Args:
            api_method: bound method, e.g. svc.users().messages().list
            result_key: key in response containing items (e.g. "files", "groups")
            scopes: passed to error handlers for diagnostics
            **params: forwarded to api_method on every call
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
            service:  the Resource returned by self.service(...)
            requests: list of prepared request objects (any size)
            scopes:   passed to error handlers for diagnostics

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

    # ── Sheets helpers ────────────────────────────────────────────

    def sheets_get_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        subject: str,
        scopes: list[str] | None = None,
    ) -> list[list[Any]]:
        """Get values from a Google Sheets range."""
        svc = self.service(
            "sheets", "v4", subject,
            scopes or [SheetsScopes.readonly],
        )
        result = svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
        ).execute()
        return result.get("values", [])

    def sheets_append_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
        subject: str,
        scopes: list[str] | None = None,
    ) -> dict:
        """Append rows to a Google Sheets range."""
        svc = self.service(
            "sheets", "v4", subject,
            scopes or [SheetsScopes.readwrite],
        )
        return svc.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body={"values": values},
        ).execute()

    def sheets_update_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
        subject: str,
        scopes: list[str] | None = None,
    ) -> dict:
        """Update values in a Google Sheets range."""
        svc = self.service(
            "sheets", "v4", subject,
            scopes or [SheetsScopes.readwrite],
        )
        return svc.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body={"values": values},
        ).execute()
