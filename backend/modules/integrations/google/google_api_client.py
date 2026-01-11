"""
Unified Google API Client.

Single client that provides access to all Google API services:
- Google Sheets API
- Google Drive API
- Google Apps Script API
- Google Admin SDK Directory API

All service methods are available through this single client.
"""

import logging
from typing import Optional, Any, Dict, List

from google.oauth2 import service_account
from googleapiclient.errors import HttpError

from .base_methods import (
    GoogleServiceAccountInfo,
    initialize_credentials,
    build_service,
    paginate_api_call,
    execute_batch_request,
    raise_for_status,
)
from .sheets_service import SheetsServiceMixin
from .directory_service import DirectoryServiceMixin
from .gmail_service import GmailServiceMixin

logger = logging.getLogger(__name__)


class GoogleApiClient(SheetsServiceMixin, DirectoryServiceMixin, GmailServiceMixin):
    """
    Unified client for all Google API services.
    
    Provides access to:
    - Sheets API (via sheets_service)
    - Drive API (via drive_service)
    - Apps Script API (via scripts_service)
    - Directory API (via directory_service)
    - Gmail API (via gmail_service)
    
    All service methods are available directly on this client.
    
    Example:
        >>> client = GoogleApiClient()
        >>> # Sheets methods
        >>> data = client.fetch_sheet_as_csv("spreadsheet_id")
        >>> # Directory methods
        >>> users = client.list_all_users()
        >>> # Gmail methods
        >>> emails = client.find_emails(subject="waitlist")
        >>> # All methods available on one client
    """
    
    def __init__(
        self,
        service_account_info: Optional[GoogleServiceAccountInfo] = None,
        subject: Optional[str] = None
    ):
        """
        Initialize unified Google API client with service account credentials.
        
        Args:
            service_account_info: Service account JSON dict.
                                If None, uses config.GOOGLE.SERVICE_ACCOUNT.
            subject: Email address of the user to impersonate (for domain-wide delegation).
                    If None, uses service account directly.
        
        Raises:
            ValueError: If credentials are missing or invalid
        
        Note:
            This client initializes all Google services (Sheets, Drive, Scripts, Directory, Gmail).
            All scopes are requested to enable full functionality.
        """
        # Collect all required scopes
        self.scopes = [
            # Sheets API scopes
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive',  # Full Drive access (was readonly, needed for permission management)
            'https://www.googleapis.com/auth/script.scriptapp',
            # Directory API scopes
            'https://www.googleapis.com/auth/admin.directory.group',
            'https://www.googleapis.com/auth/admin.directory.group.member',
            'https://www.googleapis.com/auth/admin.directory.user.readonly',
            # Gmail API scopes
            'https://www.googleapis.com/auth/gmail.readonly',
        ]
        
        # Initialize credentials
        self.base_credentials, self.credentials = initialize_credentials(
            service_account_info=service_account_info,
            scopes=self.scopes,
            subject=subject
        )
        
        logger.info(
            f"✅ GoogleApiClient initialized with service account: "
            f"{self.base_credentials.service_account_email}"
        )
        
        # Build all services
        self.sheets_service = build_service('sheets', 'v4', self.credentials)
        self.drive_service = build_service('drive', 'v3', self.credentials)
        self.scripts_service = build_service('script', 'v1', self.credentials)
        self.directory_service = build_service('admin', 'directory_v1', self.credentials)
        self.gmail_service = build_service('gmail', 'v1', self.credentials)
        
        logger.info("✅ All Google API services initialized")
    
    @property
    def service_account_email(self) -> str:
        """Get the service account email address."""
        return self.base_credentials.service_account_email
    
    def _paginate_api_call(
        self,
        api_method: Any,
        result_key: str,
        **params: Any
    ) -> List[Any]:
        """
        Generic pagination helper for Google API calls.
        
        Delegates to base_methods.paginate_api_call.
        
        Args:
            api_method: The API method to call (e.g., self.service.members().list)
            result_key: The key in the response containing the list of items (e.g., 'members', 'groups')
            **params: Additional parameters to pass to the API method
        
        Returns:
            list of all items from all pages
        """
        return paginate_api_call(api_method, result_key, **params)
    
    def batch_request(
        self,
        requests: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple API requests in a single batch HTTP request.
        
        Delegates to base_methods.execute_batch_request.
        Uses the first service that has new_batch_http_request (all services support it).
        
        Args:
            requests: list of prepared API request objects
        
        Returns:
            list of response dictionaries in the same order as requests
        
        Raises:
            ValueError: If more than 50 requests provided
            HttpError: If batch request fails
        """
        # All Google API services support batch requests, use sheets_service as default
        return execute_batch_request(self.sheets_service, requests)
    
    def _raise_for_status(
        self,
        error: HttpError
    ) -> None:
        """
        Centralized error handling for Google API HTTP errors.
        
        Delegates to base_methods.raise_for_status.
        
        Args:
            error: HttpError from Google API
        
        Raises:
            HttpError: Re-raises the original HttpError after logging JSON representation
        """
        raise_for_status(error)
