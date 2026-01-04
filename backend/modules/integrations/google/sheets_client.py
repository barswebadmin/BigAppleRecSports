"""
Google Sheets API Client.

Handles authentication and reading/writing data from Google Sheets using Service Account credentials.
"""

import logging
from typing import List, Optional, Dict, Any
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
    
    def update_sheet_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[str]],
        value_input_option: str = "USER_ENTERED"
    ) -> Dict[str, Any]:
        """
        Update a range of cells in a Google Sheet.
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            range_name: The A1 notation range to update (e.g., "A1:C10")
            values: 2D list of values to write (rows x columns)
            value_input_option: How to interpret input values:
                - "USER_ENTERED": Parse as if typed by user (formulas, dates, etc.)
                - "RAW": Values stored as-is (strings)
        
        Returns:
            Dictionary with update metadata (updatedCells, updatedRows, etc.)
        
        Raises:
            PermissionError: If the sheet is not shared with write access
            ValueError: If the spreadsheet ID is invalid
            HttpError: For other Google API errors
        
        Example:
            >>> client = GoogleSheetsClient()
            >>> values = [
            ...     ["Name", "Email", "Phone"],
            ...     ["John Doe", "john@example.com", "555-1234"],
            ...     ["Jane Smith", "jane@example.com", "555-5678"]
            ... ]
            >>> result = client.update_sheet_values("ABC123", "A1:C3", values)
            >>> print(f"Updated {result['updatedCells']} cells")
        """
        try:
            body = {'values': values}
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body
            ).execute()
            
            logger.info(
                f"✅ Updated {result.get('updatedCells', 0)} cells in range {range_name} "
                f"(spreadsheet: {spreadsheet_id[:20]}...)"
            )
            
            return result
            
        except HttpError as e:
            error_reason = 'unknown'
            if e.error_details and isinstance(e.error_details, list) and len(e.error_details) > 0:
                if isinstance(e.error_details[0], dict):
                    error_reason = e.error_details[0].get('reason', 'unknown')
            
            if e.resp.status == 403:
                raise PermissionError(
                    f"Write access denied to spreadsheet {spreadsheet_id}. "
                    f"Please ensure the sheet is shared with EDIT permissions to: {self.service_account_email}"
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
    
    def batch_update_sheet_values(
        self,
        spreadsheet_id: str,
        updates: List[Dict[str, Any]],
        value_input_option: str = "USER_ENTERED"
    ) -> Dict[str, Any]:
        """
        Update multiple ranges in a Google Sheet in a single API call (more efficient).
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            updates: List of update dictionaries, each with 'range' and 'values' keys:
                [
                    {'range': 'A1:B2', 'values': [['Name', 'Email'], ['John', 'john@example.com']]},
                    {'range': 'D1:E2', 'values': [['Phone', 'Status'], ['555-1234', 'Active']]}
                ]
            value_input_option: How to interpret input values:
                - "USER_ENTERED": Parse as if typed by user (formulas, dates, etc.)
                - "RAW": Values stored as-is (strings)
        
        Returns:
            Dictionary with batch update metadata
        
        Raises:
            PermissionError: If the sheet is not shared with write access
            ValueError: If the spreadsheet ID is invalid or updates format is wrong
            HttpError: For other Google API errors
        
        Example:
            >>> client = GoogleSheetsClient()
            >>> updates = [
            ...     {'range': 'A1:C1', 'values': [['Name', 'Email', 'Phone']]},
            ...     {'range': 'A2:C3', 'values': [
            ...         ['John Doe', 'john@example.com', '555-1234'],
            ...         ['Jane Smith', 'jane@example.com', '555-5678']
            ...     ]}
            ... ]
            >>> result = client.batch_update_sheet_values("ABC123", updates)
            >>> print(f"Updated {result['totalUpdatedCells']} cells")
        """
        try:
            data = [
                {
                    'range': update['range'],
                    'values': update['values']
                }
                for update in updates
            ]
            
            body = {
                'valueInputOption': value_input_option,
                'data': data
            }
            
            result = self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            total_cells = result.get('totalUpdatedCells', 0)
            total_ranges = len(updates)
            
            logger.info(
                f"✅ Batch updated {total_cells} cells across {total_ranges} ranges "
                f"(spreadsheet: {spreadsheet_id[:20]}...)"
            )
            
            return result
            
        except HttpError as e:
            error_reason = 'unknown'
            if e.error_details and isinstance(e.error_details, list) and len(e.error_details) > 0:
                if isinstance(e.error_details[0], dict):
                    error_reason = e.error_details[0].get('reason', 'unknown')
            
            if e.resp.status == 403:
                raise PermissionError(
                    f"Write access denied to spreadsheet {spreadsheet_id}. "
                    f"Please ensure the sheet is shared with EDIT permissions to: {self.service_account_email}"
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

