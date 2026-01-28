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

from backend.config import config

from googleapiclient.errors import HttpError

from .base_methods import (
    paginate_api_call,
    execute_batch_request,
    raise_for_status,
)

from .services import (
    GoogleSheetsService,
    GoogleDriveService,
    GoogleDirectoryService,
    GoogleMailService,
    GoogleScriptsService,
)

logger = logging.getLogger(__name__)


class GoogleApiClient():
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
    
    def __init__(self):
        """
        Initialize unified Google API client with service account credentials.
        
        Args:
            service_account_info: Service account JSON dict.
                                If None, uses config.google.service_account.
            subject: Email address of the user to impersonate (for domain-wide delegation).
                    If None, uses service account directly.
        
        Raises:
            ValueError: If credentials are missing or invalid
        
        Note:
            This client initializes all Google services (Sheets, Drive, Scripts, Directory, Gmail).
            All scopes are requested to enable full functionality.
        """
        
        # logger.info(
        #     f"✅ GoogleApiClient initialized with service account: "
        #     f"{self.credentials.service_account_email}"
        # )
        
        # Build all services
        self.sheets_service = GoogleSheetsService()
        self.drive_service = GoogleDriveService()
        self.directory_service = GoogleDirectoryService()
        self.gmail_service = GoogleMailService()
        self.scripts_service = GoogleScriptsService()
        
        logger.info("✅ All Google API services initialized")
    
    # @property
    # def service_account_email(self) -> str:
    #     """Get the service account email address."""
    #     return self.credentials.service_account_email
    

    def _paginate_api_call(
        self,
        api_method: Any,
        result_key: str,
        **params: Any
    ) -> List[Any]:

        return paginate_api_call(api_method, result_key, **params)
    

    def batch_request(
        self,
        requests: List[Any]
    ) -> List[Dict[str, Any]]:

        return execute_batch_request(self.sheets_service, requests)
    

    def _raise_for_status(
        self,
        error: HttpError,
        required_scopes: Optional[list[str]] = None
    ) -> None:
        # Collect scopes from all services if not provided
        if required_scopes is None:
            all_scopes = set()
            for service_name in ['directory_service', 'sheets_service', 'drive_service', 'gmail_service', 'scripts_service']:
                service = getattr(self, service_name, None)
                if service and hasattr(service, 'required_scopes'):
                    all_scopes.update(service.required_scopes)
            required_scopes = list(all_scopes) if all_scopes else None
        
        raise_for_status(error, required_scopes=required_scopes)
    
    # Directory service delegation methods
    def get_user(self, user_email: str):
        """Get a Google Workspace user by email address. Delegates to directory_service."""
        return self.directory_service.get_user(user_email)
    
    def create_user(self, primary_email: str, given_name: str, family_name: str, recovery_email: Optional[str] = None, password: Optional[str] = None, change_password_at_next_login: bool = True, org_unit_path: Optional[str] = None):
        """Create a new Google Workspace user. Delegates to directory_service."""
        return self.directory_service.create_user(primary_email, given_name, family_name, recovery_email, password, change_password_at_next_login, org_unit_path)
    
    def list_all_users(self):
        """List all Google Workspace users. Delegates to directory_service."""
        return self.directory_service.list_all_users()
    
    def get_group(self, group_email: str):
        """Get a Google Workspace group by email address. Delegates to directory_service."""
        return self.directory_service.get_group(group_email)
    
    def list_all_groups(self):
        """List all Google Workspace groups. Delegates to directory_service."""
        return self.directory_service.list_all_groups()
    
    def list_group_members(self, group_email: str):
        """List members of a Google Workspace group. Delegates to directory_service."""
        return self.directory_service.list_group_members(group_email)
