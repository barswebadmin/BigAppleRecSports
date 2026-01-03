"""
Google Sheets API Client.

Handles authentication and fetching data from Google Sheets using Service Account credentials.
"""

import logging
from typing import List, Optional
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import config

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    """Client for interacting with Google Sheets API."""
    
    def __init__(self, credentials_path: Optional[Path] = None):
        """
        Initialize Google Sheets client with service account credentials.
        
        Args:
            credentials_path: Path to service account JSON file.
                            If None, uses path from config.
        
        Raises:
            FileNotFoundError: If credentials file doesn't exist
            ValueError: If credentials are invalid
        """
        self.credentials_path = credentials_path or config.Google.service_account_path
        
        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"Google service account credentials not found at: {self.credentials_path}. "
                f"Please follow the setup guide in GOOGLE_SHEETS_SETUP_GUIDE.md"
            )
        
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                str(self.credentials_path),
                scopes=config.Google.scopes
            )
            
            self.service = build('sheets', 'v4', credentials=self.credentials)
            
            logger.info(
                f"✅ Google Sheets client initialized with service account: "
                f"{self.credentials.service_account_email}"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            raise ValueError(f"Invalid Google service account credentials: {e}")
    
    @property
    def service_account_email(self) -> str:
        """Get the service account email address."""
        return self.credentials.service_account_email
    
    def fetch_sheet_as_csv(
        self,
        spreadsheet_id: str,
        range_name: str = "A:Z"
    ) -> List[List[str]]:
        """
        Fetch data from a Google Sheet and return as CSV-like list of lists.
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            range_name: The A1 notation range to fetch (default: "A:Z" - all columns)
        
        Returns:
            List of rows, where each row is a list of cell values (strings)
        
        Raises:
            PermissionError: If the sheet is not shared with the service account
            ValueError: If the spreadsheet ID is invalid
            HttpError: For other Google API errors
        
        Example:
            >>> client = GoogleSheetsClient()
            >>> data = client.fetch_sheet_as_csv("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
            >>> print(data[0])  # Header row
            ['Name', 'Email', 'Phone']
        """
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.warning(f"No data found in sheet: {spreadsheet_id}")
                return []
            
            logger.info(
                f"✅ Fetched {len(values)} rows from Google Sheet "
                f"(ID: {spreadsheet_id[:20]}...)"
            )
            
            return values
            
        except HttpError as e:
            error_reason = 'unknown'
            if e.error_details and isinstance(e.error_details, list) and len(e.error_details) > 0:
                if isinstance(e.error_details[0], dict):
                    error_reason = e.error_details[0].get('reason', 'unknown')
            
            if e.resp.status == 403:
                raise PermissionError(
                    f"Access denied to spreadsheet {spreadsheet_id}. "
                    f"Please share the sheet with: {self.service_account_email}"
                ) from e
            
            elif e.resp.status == 404:
                raise ValueError(
                    f"Spreadsheet not found: {spreadsheet_id}. "
                    f"Please check the spreadsheet ID is correct."
                ) from e
            
            else:
                logger.error(
                    f"Google Sheets API error ({e.resp.status}): {error_reason}"
                )
                raise
    
    def extract_sheet_id_from_url(self, url: str) -> str:
        """
        Extract spreadsheet ID from a Google Sheets URL.
        
        Args:
            url: Full Google Sheets URL or just the spreadsheet ID
        
        Returns:
            The spreadsheet ID
        
        Raises:
            ValueError: If URL format is invalid
        
        Example:
            >>> client = GoogleSheetsClient()
            >>> url = "https://docs.google.com/spreadsheets/d/ABC123/edit#gid=0"
            >>> client.extract_sheet_id_from_url(url)
            'ABC123'
        """
        if "/spreadsheets/d/" in url:
            try:
                sheet_id = url.split("/spreadsheets/d/")[1].split("/")[0]
                return sheet_id
            except IndexError:
                raise ValueError(f"Invalid Google Sheets URL format: {url}")
        else:
            return url.strip()

