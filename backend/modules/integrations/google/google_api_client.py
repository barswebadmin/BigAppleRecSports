"""
Unified Google API Client.

This client provides a generic interface for Google API services with centralized
credential management, error handling, and request execution.
"""

import logging
import hashlib
from typing import Optional, Dict, Any, List

from googleapiclient.discovery import build, Resource
from google.oauth2.service_account import Credentials
from shared_utilities.api_clients.http_client import AsyncHTTPClient, RetryPolicy

from .services import (
    GoogleSheetsService,
    GoogleDriveService,
    GoogleMailService,
    GoogleScriptsService,
)
from .scopes import DirectoryScopes, SheetsScopes, DriveScopes, GmailScopes, ScriptsScopes

logger = logging.getLogger(__name__)


class GoogleApiClient(AsyncHTTPClient):
    """
    Unified client for Google API services with HTTP client capabilities.

    This client provides both:
    - Generic Google API service execution with credential management
    - HTTP client functionality (from AsyncHTTPClient)
    - Legacy service delegation for backward compatibility

    The client caches credentials per scope combination and rebuilds when different
    scopes are requested.

    Example:
        >>> client = GoogleApiClient()
        >>> # Generic Google API call
        >>> response = client.execute_request(
        ...     service_name="admin",
        ...     version="directory_v1",
        ...     scopes=[DirectoryScopes.groups_readonly],
        ...     resource="groups",
        ...     method="list",
        ...     params={"customer": "my_customer"}
        ... )
        >>> # HTTP client methods
        >>> response = await client.get("/some-endpoint")
    """

    def __init__(self, retry_policy: Optional[RetryPolicy] = None, **kwargs):
        """
        Initialize unified Google API client.

        Args:
            retry_policy: Optional retry policy for HTTP requests
            **kwargs: Additional arguments passed to AsyncHTTPClient
        """
        # Initialize the HTTP client
        super().__init__(retry_policy=retry_policy, **kwargs)

        # Credential caching
        self._cached_credentials: Dict[str, Credentials] = {}
        self._cached_services: Dict[str, Resource] = {}

        # Legacy service delegation - keep for backward compatibility
        self.sheets_service = GoogleSheetsService()
        self.drive_service = GoogleDriveService()
        self.gmail_service = GoogleMailService()
        self.scripts_service = GoogleScriptsService()

        # Scope classes for easy access
        self.directory_scopes = DirectoryScopes()
        self.sheets_scopes = SheetsScopes()
        self.drive_scopes = DriveScopes()
        self.gmail_scopes = GmailScopes()
        self.scripts_scopes = ScriptsScopes()

        logger.info("Google API client initialized with generic service execution and HTTP capabilities")

    def _get_scope_key(self, scopes: List[str]) -> str:
        """Generate a cache key for the given scopes."""
        return hashlib.md5("|".join(sorted(scopes)).encode()).hexdigest()

    def _get_service_key(self, service_name: str, version: str, scopes: List[str]) -> str:
        """Generate a cache key for the service."""
        scope_key = self._get_scope_key(scopes)
        return f"{service_name}:{version}:{scope_key}"

    def _build_credentials(self, scopes: List[str]) -> Credentials:
        """Build credentials for the given scopes."""
        scope_key = self._get_scope_key(scopes)
        
        if scope_key in self._cached_credentials:
            return self._cached_credentials[scope_key]

        # Load service account credentials
        # This should be configured to load from your service account file
        credentials_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH', 'google-service-account.json')
        
        try:
            credentials = Credentials.from_service_account_file(
                credentials_path,
                scopes=scopes
            )
            self._cached_credentials[scope_key] = credentials
            logger.info("Built credentials for scopes: %s", scopes)
            return credentials
        except Exception as e:
            logger.error("Failed to build credentials: %s", e)
            raise

    def _build_service(self, service_name: str, version: str, scopes: List[str]) -> Resource:
        """Build Google API service for the given parameters."""
        service_key = self._get_service_key(service_name, version, scopes)
        
        if service_key in self._cached_services:
            return self._cached_services[service_key]

        credentials = self._build_credentials(scopes)
        
        try:
            service = build(service_name, version, credentials=credentials)
            self._cached_services[service_key] = service
            logger.info("Built service: %s %s", service_name, version)
            return service
        except Exception as e:
            logger.error("Failed to build service %s %s: %s", service_name, version, e)
            raise

    def execute_request(
        self,
        service_name: str,
        version: str,
        scopes: List[str],
        resource: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a Google API request with centralized error handling.

        Args:
            service_name: Google service name (e.g., "admin", "sheets")
            version: API version (e.g., "directory_v1", "v4")
            scopes: Required OAuth scopes
            resource: API resource (e.g., "groups", "users")
            method: API method (e.g., "list", "get", "insert")
            params: Query parameters
            body: Request body for POST/PUT requests

        Returns:
            API response data

        Raises:
            Exception: For Google API errors (4xx, 5xx, timeouts handled centrally)
        """
        service = self._build_service(service_name, version, scopes)
        
        try:
            # Build the API call
            resource_obj = getattr(service, resource)()
            method_obj = getattr(resource_obj, method)
            
            # Prepare arguments
            kwargs = {}
            if params:
                kwargs.update(params)
            if body:
                kwargs['body'] = body
            
            # Execute the request
            request = method_obj(**kwargs)
            response = request.execute()
            
            logger.debug("Executed %s.%s.%s", service_name, resource, method)
            return response

        except Exception as e:
            logger.error("Google API request failed: %s.%s.%s - %s", service_name, resource, method, e)
            # Central error handling for 4xx, timeouts, etc. would go here
            # For now, re-raise to let services handle specific cases
            raise

    # Legacy delegation methods for backward compatibility
    def fetch_sheet_as_csv(self, spreadsheet_id: str, range_name: str = "A:Z"):
        """Fetch sheet data as CSV format. Delegates to sheets_service."""
        return self.sheets_service.fetch_sheet_as_csv(spreadsheet_id, range_name)

    def get_sheet_data_with_formatting(self, spreadsheet_id: str, range_name: str = "A:Z"):
        """Get sheet data with formatting information. Delegates to sheets_service."""
        return self.sheets_service.get_sheet_data_with_formatting(spreadsheet_id, range_name)

    def extract_sheet_id_from_url(self, url: str):
        """Extract spreadsheet ID from Google Sheets URL. Delegates to sheets_service."""
        return self.sheets_service.extract_sheet_id_from_url(url)

    def update_sheet_values(self, spreadsheet_id: str, range_name: str, values: list,
                           value_input_option: str = "RAW"):
        """Update sheet values. Delegates to sheets_service."""
        return self.sheets_service.update_sheet_values(
            spreadsheet_id, range_name, values, value_input_option
        )

    def batch_update_sheet_values(self, spreadsheet_id: str, updates: list):
        """Batch update sheet values. Delegates to sheets_service."""
        return self.sheets_service.batch_update_sheet_values(spreadsheet_id, updates)

    def find_emails(self, subject: Optional[str] = None, sender: Optional[str] = None,
                   days_ago: int = 7):
        """Find emails with specified criteria. Delegates to gmail_service."""
        return self.gmail_service.find_emails(subject, sender, days_ago)

    def send_to_waitlist_form(self, data: dict):
        """Send data to waitlist form via Apps Script. Delegates to scripts_service."""
        return self.scripts_service.send_to_waitlist_form(data)

    def get_sheet_revisions(self, spreadsheet_id: str):
        """Get sheet revisions from Google Drive. Delegates to drive_service."""
        return self.drive_service.get_sheet_revisions(spreadsheet_id)