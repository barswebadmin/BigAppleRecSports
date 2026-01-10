"""
Google Sheets API Client.

Handles authentication and reading/writing data from Google Sheets using Service Account credentials.
"""

import logging
from typing import Optional, Dict, Any

from pydantic import Field

from backend.shared.model_config import ApiModel
from .base_client import GoogleAPIClient, GoogleServiceAccountInfo, handle_http_errors

logger = logging.getLogger(__name__)


class ValueRange(ApiModel):
    """Google Sheets API ValueRange response structure."""
    range_: Optional[str] = Field(None, alias='range')  # 'range' is a Python keyword
    major_dimension: Optional[str] = None  # 'ROWS' or 'COLUMNS'
    values: Optional[list[list[str]]] = None


class UpdateValuesResponse(ApiModel):
    """Google Sheets API UpdateValuesResponse structure."""
    spreadsheet_id: Optional[str] = None
    updated_cells: Optional[int] = None
    updated_columns: Optional[int] = None
    updated_rows: Optional[int] = None
    updated_range: Optional[str] = None


class BatchUpdateValuesResponse(ApiModel):
    """Google Sheets API BatchUpdateValuesResponse structure."""
    total_updated_cells: int
    total_updated_columns: int
    total_updated_rows: int
    total_updated_sheets: int
    responses: list[UpdateValuesResponse]


class GoogleSheetsClient(GoogleAPIClient):
    """Client for interacting with Google Sheets API."""
    
    def __init__(self, service_account_info: Optional[GoogleServiceAccountInfo] = None):
        """
        Initialize Google Sheets client with service account credentials.
        
        Args:
            service_account_info: Service account JSON dict.
                                If None, uses config.GOOGLE.SERVICE_ACCOUNT.
        
        Raises:
            ValueError: If credentials are missing or invalid
        """
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.readonly',
        ]
        super().__init__(service_account_info=service_account_info)
        self.service = self._build_service('sheets', 'v4')
    
    @handle_http_errors
    def fetch_sheet_as_csv(
        self,
        spreadsheet_id: str,
        range_name: str = "A:Z"
    ) -> list[list[str]]:
        """
        Fetch data from a Google Sheet and return as CSV-like list of lists.
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            range_name: The A1 notation range to fetch (default: "A:Z" - all columns)
        
        Returns:
            list of rows, where each row is a list of cell values (strings)
        
        Raises:
            HttpError: For Google API errors
        
        Example:
            >>> client = GoogleSheetsClient()
            >>> data = client.fetch_sheet_as_csv("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
            >>> print(data[0])  # Header row
            ['Name', 'Email', 'Phone']
        """
        result_dict = self.service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        result = ValueRange(**result_dict)
        values = result.values or []
        
        if not values:
            logger.warning(f"No data found in sheet: {spreadsheet_id}")
            return []
        
        logger.info(
            f"✅ Fetched {len(values)} rows from Google Sheet "
            f"(ID: {spreadsheet_id[:20]}...)"
        )
        
        return values
    
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
    
    def _build_update_request(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[str]],
        value_input_option: str = "USER_ENTERED"
    ) -> Any:
        """
        Build an update request object without executing it.
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            range_name: The A1 notation range to update (e.g., "A1:C10")
            values: 2D list of values to write (rows x columns)
            value_input_option: How to interpret input values
        
        Returns:
            Request object ready to be executed or added to a batch
        """
        body = {'values': values}
        return self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body=body
        )
    
    @handle_http_errors
    def update_sheet_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[str]],
        value_input_option: str = "USER_ENTERED"
    ) -> UpdateValuesResponse:
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
            HttpError: For Google API errors
        
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
        request = self._build_update_request(
            spreadsheet_id, range_name, values, value_input_option
        )
        result_dict = request.execute()
        result = UpdateValuesResponse(**result_dict)
        
        logger.info(
            f"✅ Updated {result.updated_cells or 0} cells in range {range_name} "
            f"(spreadsheet: {spreadsheet_id[:20]}...)"
        )
        
        return result
    
    @handle_http_errors
    def batch_update_sheet_values(
        self,
        spreadsheet_id: str,
        updates: list[Dict[str, Any]],
        value_input_option: str = "USER_ENTERED"
    ) -> BatchUpdateValuesResponse:
        """
        Update multiple ranges in a Google Sheet using batched API requests.
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            updates: list of update dictionaries, each with 'range' and 'values' keys
            value_input_option: How to interpret input values:
                - "USER_ENTERED": Parse as if typed by user (formulas, dates, etc.)
                - "RAW": Values stored as-is (strings)
        
        Returns:
            Dictionary with batch update metadata
        
        Raises:
            HttpError: For Google API errors
        
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
        requests = [
            self._build_update_request(
                spreadsheet_id,
                update['range'],
                update['values'],
                value_input_option
            )
            for update in updates
        ]
        
        batch_responses = self.batch_request(requests)
        responses: list[UpdateValuesResponse] = [
            UpdateValuesResponse(**response) for response in batch_responses
        ]
        
        total_cells = sum(response.updated_cells or 0 for response in responses)
        total_ranges = len(updates)
        
        result = BatchUpdateValuesResponse(
            total_updated_cells=total_cells,
            total_updated_columns=sum(response.updated_columns or 0 for response in responses),
            total_updated_rows=sum(response.updated_rows or 0 for response in responses),
            total_updated_sheets=len(set(
                (response.updated_range or '').split('!')[0] 
                for response in responses 
                if response.updated_range and '!' in response.updated_range
            )),
            responses=responses
        )
        
        logger.info(
            f"✅ Batch updated {total_cells} cells across {total_ranges} ranges "
            f"(spreadsheet: {spreadsheet_id[:20]}...)"
        )
        
        return result

