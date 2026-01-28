"""
Google Sheets API service methods and models.

Contains Sheets-specific functionality: models, methods, and helper functions.
"""

import logging


from typing import Optional, Dict, Any, List, TYPE_CHECKING

from google.oauth2.service_account import Credentials

from backend.modules.integrations.google.services._google_api_service_builder import build_google_api_service
from backend.modules.integrations.google.base_methods import handle_http_errors
from backend.modules.integrations.google.models.google_sheets_resources import ValueRange, SheetDataWithFormatting, UpdateValuesResponse, BatchUpdateValuesResponse

logger = logging.getLogger(__name__)

class GoogleSheetsService():
    """Mixin class containing Google Sheets API methods.
    
    This mixin expects to be used with GoogleApiClient, which provides:
    - sheets_service: Google Sheets API service instance
    - drive_service: Google Drive API service instance  
    - batch_request(): Method to execute batch requests
    """

    if TYPE_CHECKING:
        def batch_request(self, requests: List[Any]) -> List[Dict[str, Any]]: ...
    
    def __init__(self):
        
        required_scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/script.scriptapp',
        ]

        self.service = build_google_api_service('sheets', 'v4', required_scopes)
        self.required_scopes = required_scopes  # Store for error diagnostics
        self.spreadsheets = self.service.spreadsheets()  # type: ignore[attr-defined]

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
            >>> client = GoogleApiClient()
            >>> data = client.fetch_sheet_as_csv("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
            >>> print(data[0])  # Header row
            ['Name', 'Email', 'Phone']
        """
        result_dict = self.spreadsheets().values().get(
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
    
    @handle_http_errors
    def get_sheet_data_with_formatting(
        self,
        spreadsheet_id: str,
        range_name: str = "A:Z"
    ) -> SheetDataWithFormatting:
        """
        Fetch sheet data including values and background colors.
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            range_name: The A1 notation range to fetch (default: "A:Z")
        
        Returns:
            SheetDataWithFormatting with values and backgrounds
        
        Raises:
            HttpError: For Google API errors
        """
        logger.info(f"Fetching sheet data with formatting for spreadsheet: {spreadsheet_id[:20]}...")
        
        # Get values
        values_result = self.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        sheet_data = values_result.get('values', [])
        
        # Get formatting (backgrounds)
        batch_result = self.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            ranges=[range_name],
            includeGridData=True
        ).execute()
        
        backgrounds_data = []
        if batch_result.get('sheets'):
            sheet = batch_result['sheets'][0]
            if 'data' in sheet and sheet['data']:
                grid_data = sheet['data'][0]
                if 'rowData' in grid_data:
                    for row_data in grid_data['rowData']:
                        row_bg = []
                        if 'values' in row_data:
                            for cell in row_data['values']:
                                bg = cell.get('effectiveFormat', {}).get('backgroundColor', {})
                                row_bg.append(bg)
                        backgrounds_data.append(row_bg)
        
        # Pad backgrounds to match data length
        while len(backgrounds_data) < len(sheet_data):
            backgrounds_data.append([])
        
        result = SheetDataWithFormatting(
            values=sheet_data,
            backgrounds=backgrounds_data,
            row_count=len(sheet_data),
            column_count=len(sheet_data[0]) if sheet_data else 0
        )
        
        logger.info(f"✅ Fetched {result.row_count} rows with formatting data")
        
        return result
    
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
            >>> client = GoogleApiClient()
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
        return self.spreadsheets().values().update(
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
            >>> client = GoogleApiClient()
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
            >>> client = GoogleApiClient()
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
