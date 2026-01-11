"""
Google Sheets API Client.

Handles authentication and interaction with Google Sheets API, Google Drive API,
and Google Apps Script API for comprehensive sheet operations and automation.
"""

import logging
import os
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List

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


class ExecutionInfo(ApiModel):
    """Apps Script execution information."""
    name: Optional[str] = None
    execution_id: Optional[str] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    status: Optional[str] = None
    function_name: Optional[str] = None


class SheetRevision(ApiModel):
    """Google Sheets revision information."""
    id: str
    modified_time: str
    modified_user: Optional[Dict[str, Any]] = None
    published: Optional[bool] = None
    published_auto: Optional[bool] = None
    published_domain: Optional[str] = None
    published_outside_domain: Optional[bool] = None


class SheetDataWithFormatting(ApiModel):
    """Sheet data including values and formatting."""
    values: List[List[str]]
    backgrounds: List[List[Dict[str, Any]]]
    row_count: int
    column_count: int


class GoogleSheetsClient(GoogleAPIClient):
    """Client for interacting with Google Sheets API, Drive API, and Apps Script API."""
    
    def __init__(self, service_account_info: Optional[GoogleServiceAccountInfo] = None, subject: Optional[str] = None):
        """
        Initialize Google Sheets client with service account credentials.
        
        Args:
            service_account_info: Service account JSON dict.
                                If None, uses config.GOOGLE.SERVICE_ACCOUNT.
            subject: Email address of the user to impersonate (for domain-wide delegation).
                    If None, uses service account directly.
        
        Raises:
            ValueError: If credentials are missing or invalid
        """
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/script.scriptapp',
        ]
        super().__init__(service_account_info=service_account_info, subject=subject)
        self.service = self._build_service('sheets', 'v4')
        self.drive_service = self._build_service('drive', 'v3')
        self.scripts_service = self._build_service('script', 'v1')
    
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
        values_result = self.service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        sheet_data = values_result.get('values', [])
        
        # Get formatting (backgrounds)
        batch_result = self.service.spreadsheets().get(
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
    
    @handle_http_errors
    def get_sheet_revisions(
        self,
        spreadsheet_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[SheetRevision]:
        """
        Get sheet revision history, optionally filtered by time range.
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            start_time: Optional start time to filter revisions
            end_time: Optional end time to filter revisions
        
        Returns:
            List of SheetRevision objects
        
        Raises:
            HttpError: For Google API errors
        """
        logger.info(f"Fetching revisions for spreadsheet: {spreadsheet_id[:20]}...")
        
        revisions_result = self.drive_service.revisions().list(
            fileId=spreadsheet_id
        ).execute()
        
        revisions_list = revisions_result.get('revisions', [])
        
        # Filter by time if provided
        if start_time or end_time:
            filtered_revisions = []
            for rev in revisions_list:
                modified_time_str = rev.get('modifiedTime', '')
                if modified_time_str:
                    try:
                        modified_time = datetime.fromisoformat(modified_time_str.replace('Z', '+00:00'))
                        if start_time and modified_time < start_time:
                            continue
                        if end_time and modified_time > end_time:
                            continue
                        filtered_revisions.append(SheetRevision(**rev))
                    except Exception as e:
                        logger.warning(f"Could not parse revision time: {e}")
                        continue
            revisions_list = filtered_revisions
        else:
            revisions_list = [SheetRevision(**rev) for rev in revisions_list]
        
        logger.info(f"✅ Found {len(revisions_list)} revisions")
        
        return revisions_list
    
    @handle_http_errors
    def get_script_executions(
        self,
        script_id: str,
        page_size: int = 50
    ) -> List[ExecutionInfo]:
        """
        Get Apps Script execution logs.
        
        Note: The Apps Script API doesn't provide direct access to execution logs.
        Execution logs must be viewed manually in the Apps Script dashboard.
        This method returns an empty list and logs a message.
        
        Args:
            script_id: The Apps Script project ID
            page_size: Number of executions to retrieve (not used, kept for API compatibility)
        
        Returns:
            Empty list (execution logs require manual check)
        
        Note:
            Check executions manually at:
            https://script.google.com/home/projects/{script_id}/executions
        """
        logger.warning(
            f"Apps Script API does not provide execution logs via API. "
            f"Check manually at: https://script.google.com/home/projects/{script_id}/executions"
        )
        return []
    
    def filter_executions_by_time(
        self,
        executions: List[ExecutionInfo],
        start_time: datetime,
        end_time: datetime
    ) -> List[ExecutionInfo]:
        """
        Filter executions by time range.
        
        Args:
            executions: List of ExecutionInfo objects
            start_time: Start of time range
            end_time: End of time range
        
        Returns:
            Filtered list of ExecutionInfo objects
        """
        filtered = []
        for exec_info in executions:
            time_str = exec_info.update_time or exec_info.create_time
            if time_str:
                try:
                    exec_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    if start_time <= exec_time <= end_time:
                        filtered.append(exec_info)
                except Exception:
                    continue
        return filtered
    
    def send_to_waitlist_form(self, product_data: Dict[str, Any], web_app_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Send product data to Google Apps Script waitlist form web app.
        
        Args:
            product_data: Dictionary containing product information. Expected keys:
                - product_url: URL of the product
                - sport: Sport name
                - day: Day of the week
                - division: Division name
                - other_identifier: Other identifying information
                Or can contain nested 'parsed' dict with these keys
            web_app_url: Optional GAS web app URL. If not provided, uses GAS_WAITLIST_FORM_WEB_APP_URL env var.
        
        Returns:
            Dictionary with 'success' key and optional 'error' or 'response' keys
        
        Example:
            >>> client = GoogleSheetsClient()
            >>> result = client.send_to_waitlist_form({
            ...     "product_url": "https://example.com/product",
            ...     "sport": "dodgeball",
            ...     "day": "tuesday",
            ...     "division": "open"
            ... })
            >>> print(result["success"])
            True
        """
        if web_app_url is None:
            web_app_url = os.getenv("GAS_WAITLIST_FORM_WEB_APP_URL")
        
        if not web_app_url:
            logger.error("GAS_WAITLIST_FORM_WEB_APP_URL not configured")
            return {"success": False, "error": "Waitlist form URL not configured"}
        
        # Extract parsed data if nested, otherwise use product_data directly
        if "parsed" in product_data:
            parsed = product_data["parsed"]
        else:
            parsed = product_data
        
        # Convert snake_case keys to camelCase for GAS
        camel_case_data = {
            "productUrl": parsed.get("product_url"),
            "sport": parsed.get("sport"),
            "day": parsed.get("day"),
            "division": parsed.get("division"),
            "otherIdentifier": parsed.get("other_identifier")
        }
        
        logger.info(f"Sending product data to waitlist form: {camel_case_data}")
        
        try:
            response = requests.post(
                web_app_url,
                json=camel_case_data,
                timeout=30
            )
            
            if response.status_code < 400:
                # Check if GAS returned an error in the response body
                try:
                    response_data = response.json()
                    if response_data.get("status") == "error":
                        error_message = response_data.get("message", "Unknown error")
                        if "already exists" in error_message:
                            logger.info(f"Product option already exists in waitlist form: {error_message}")
                            return {"success": False, "error": error_message, "already_exists": True}
                        else:
                            logger.error(f"GAS returned error: {error_message}")
                            return {"success": False, "error": error_message}
                    else:
                        logger.info(f"Successfully sent product data to waitlist form")
                        return {"success": True, "response": response.text}
                except ValueError:
                    # Not JSON response, treat as success
                    logger.info(f"Successfully sent product data to waitlist form")
                    return {"success": True, "response": response.text}
            else:
                logger.error(f"Failed to send to waitlist form. Status: {response.status_code}, Response: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except requests.RequestException as e:
            logger.error(f"Request to waitlist form failed: {e}")
            return {"success": False, "error": str(e)}
