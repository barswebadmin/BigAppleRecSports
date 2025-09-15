"""
Google Sheets Helper Functions (Adapted for Python)
Note: These functions provide structure for sheet operations but would need
a Google Sheets API client to be fully functional
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from .api_utils import normalize_order_number

logger = logging.getLogger(__name__)


class SheetDataProcessor:
    """
    Process sheet data in a way similar to Google Apps Script
    This class provides utilities for working with 2D array data structures
    that mimic Google Sheets data format
    """

    def __init__(self, data: List[List[Any]]):
        """
        Initialize with sheet data

        Args:
            data: 2D array representing sheet data (first row = headers)
        """
        self.data = data
        self.headers = data[0] if data else []
        self.rows = data[1:] if len(data) > 1 else []

    def get_headers(self) -> List[str]:
        """Get headers from the sheet (first row)"""
        return self.headers

    def get_rows(self) -> List[List[Any]]:
        """Get all data rows (excluding headers)"""
        return self.rows

    def get_column_index(self, column_name: str) -> int:
        """
        Get column index by header name (case-insensitive partial match)

        Args:
            column_name: Column name to search for

        Returns:
            Column index or -1 if not found
        """
        column_name_lower = column_name.lower()
        for i, header in enumerate(self.headers):
            if column_name_lower in str(header).lower():
                return i
        return -1

    def find_row_by_column_value(
        self,
        column_name: str,
        search_value: Any,
        normalize_func: Optional[Callable] = None,
    ) -> Optional[List[Any]]:
        """
        Find a row by column value

        Args:
            column_name: Column header to search in
            search_value: Value to search for
            normalize_func: Optional normalization function

        Returns:
            Row data or None if not found
        """
        column_index = self.get_column_index(column_name)
        if column_index == -1:
            logger.error(f"Column '{column_name}' not found in headers")
            return None

        normalized_search = (
            normalize_func(search_value) if normalize_func else search_value
        )

        for row in self.rows:
            if column_index < len(row):
                cell_value = row[column_index]
                normalized_cell = (
                    normalize_func(cell_value) if normalize_func else cell_value
                )
                if normalized_cell == normalized_search:
                    return row

        return None

    def find_all_rows_by_column_value(
        self,
        column_name: str,
        search_value: Any,
        normalize_func: Optional[Callable] = None,
    ) -> List[List[Any]]:
        """
        Find all rows matching a column value

        Args:
            column_name: Column header to search in
            search_value: Value to search for
            normalize_func: Optional normalization function

        Returns:
            List of matching rows
        """
        column_index = self.get_column_index(column_name)
        if column_index == -1:
            logger.error(f"Column '{column_name}' not found in headers")
            return []

        normalized_search = (
            normalize_func(search_value) if normalize_func else search_value
        )
        matching_rows = []

        for row in self.rows:
            if column_index < len(row):
                cell_value = row[column_index]
                normalized_cell = (
                    normalize_func(cell_value) if normalize_func else cell_value
                )
                if normalized_cell == normalized_search:
                    matching_rows.append(row)

        return matching_rows

    def parse_row_to_dict(self, row_data: List[Any]) -> Dict[str, Any]:
        """
        Parse a row into a dictionary using headers as keys

        Args:
            row_data: Row data array

        Returns:
            Dictionary with header names as keys
        """
        result = {}
        for i, value in enumerate(row_data):
            if i < len(self.headers):
                header_key = str(self.headers[i]).strip().lower().replace(" ", "_")
                result[header_key] = value
        return result

    def get_cell_value(self, row_index: int, column_name: str) -> Any:
        """
        Get a specific cell value

        Args:
            row_index: Row index (0-based, excluding headers)
            column_name: Column name

        Returns:
            Cell value or None if not found
        """
        column_index = self.get_column_index(column_name)
        if column_index == -1 or row_index >= len(self.rows):
            return None

        row = self.rows[row_index]
        return row[column_index] if column_index < len(row) else None


def parse_refund_row_data(
    row_object: List[Any], sheet_headers: List[str]
) -> Dict[str, Any]:
    """
    Parse row data based on headers (for refunds/orders)

    Args:
        row_object: Row data array
        sheet_headers: Headers array

    Returns:
        Parsed row data object
    """
    row_data = {}

    for i, header in enumerate(sheet_headers):
        if i >= len(row_object):
            break

        header_lower = str(header).lower().strip()
        value = row_object[i]

        if "timestamp" in header_lower:
            row_data["request_submitted_at"] = value
        elif "email address" in header_lower:
            row_data["requestor_email"] = value
        elif "order number" in header_lower:
            row_data["raw_order_number"] = value
        elif "do you want a refund" in header_lower:
            row_data["refund_or_credit"] = (
                "refund" if "refund" in str(value).lower() else "credit"
            )
        elif "anything else to note" in header_lower:
            row_data["request_notes"] = value
        elif "first name" in header_lower:
            row_data["requestor_first_name"] = value
        elif "last name" in header_lower:
            row_data["requestor_last_name"] = value

    return row_data


def get_request_details_from_order_number(
    sheet_data: List[List[Any]], raw_order_number: str
) -> Optional[Dict[str, Any]]:
    """
    Get request details from order number

    Args:
        sheet_data: 2D array of sheet data
        raw_order_number: Order number to search for

    Returns:
        Parsed request data or None if not found
    """
    if not sheet_data:
        return None

    processor = SheetDataProcessor(sheet_data)

    order_id_col_index = processor.get_column_index("order number")
    timestamp_col_index = processor.get_column_index("timestamp")

    if order_id_col_index == -1:
        logger.error("Order column header not found")
        return None

    # Find all matching rows
    matching_rows = processor.find_all_rows_by_column_value(
        "order number", raw_order_number, normalize_order_number
    )

    if not matching_rows:
        logger.error(f"No matching order found for {raw_order_number}")
        return None

    # Return the row with the most recent timestamp
    if timestamp_col_index != -1:
        try:
            most_recent_row = max(
                matching_rows,
                key=lambda row: row[timestamp_col_index]
                if timestamp_col_index < len(row)
                else "",
            )
        except (ValueError, TypeError):
            most_recent_row = matching_rows[0]
    else:
        most_recent_row = matching_rows[0]

    return parse_refund_row_data(most_recent_row, processor.headers)


def generate_sheet_row_link(sheet_id: str, sheet_gid: str, row_number: int) -> str:
    """
    Generate a link to a specific row in a Google Sheet

    Args:
        sheet_id: Google Sheets ID
        sheet_gid: Sheet GID (tab identifier)
        row_number: Row number (1-based)

    Returns:
        Direct link to the row
    """
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit#gid={sheet_gid}&range=A{row_number}"


def get_row_link_for_order(
    sheet_data: List[List[Any]], order_number: str, sheet_id: str, sheet_gid: str
) -> str:
    """
    Get row link for a specific order number

    Args:
        sheet_data: 2D array of sheet data
        order_number: Order number to find
        sheet_id: Google Sheets ID
        sheet_gid: Sheet GID

    Returns:
        Link to the row or empty string if not found
    """
    if not sheet_data:
        return ""

    processor = SheetDataProcessor(sheet_data)
    order_id_col_index = processor.get_column_index("order number")

    if order_id_col_index == -1:
        logger.warning("Order number column not found")
        return ""

    for i, row in enumerate(processor.rows):
        if order_id_col_index < len(row):
            cell_value = row[order_id_col_index]
            if cell_value and normalize_order_number(
                str(cell_value)
            ) == normalize_order_number(str(order_number)):
                # Convert to 1-based row index for Google Sheets link (add 2: 1 for headers, 1 for 1-based)
                row_number = i + 2
                return generate_sheet_row_link(sheet_id, sheet_gid, row_number)

    logger.warning(f"Order number {order_number} not found in sheet")
    return ""


def mark_order_as_processed_in_data(
    sheet_data: List[List[Any]], raw_order_number: str
) -> Dict[str, Any]:
    """
    Mark an order as processed in sheet data (returns update information)

    Args:
        sheet_data: 2D array of sheet data
        raw_order_number: Order number to mark as processed

    Returns:
        Dictionary with update information
    """
    try:
        if not sheet_data:
            raise ValueError("No sheet data provided")

        processor = SheetDataProcessor(sheet_data)

        order_col_index = processor.get_column_index("order number")
        processed_col_index = processor.get_column_index("processed")

        if order_col_index == -1 or processed_col_index == -1:
            raise ValueError(
                f"Missing required columns. "
                f"Order column index: {order_col_index}, "
                f"Processed column index: {processed_col_index}"
            )

        normalized_target = normalize_order_number(raw_order_number)

        for i, row in enumerate(processor.rows):
            if order_col_index < len(row):
                cell_value = row[order_col_index]
                normalized_cell = normalize_order_number(
                    str(cell_value).strip() if cell_value else ""
                )

                if normalized_cell == normalized_target:
                    # Return update information (for external sheet API calls)
                    actual_row_number = i + 2  # +1 for headers, +1 for 1-based indexing
                    actual_col_number = processed_col_index + 1  # 1-based indexing

                    return {
                        "success": True,
                        "row_number": actual_row_number,
                        "column_number": actual_col_number,
                        "value": True,
                        "message": f"Order {raw_order_number} marked as processed",
                    }

        raise ValueError(f"Order number {raw_order_number} not found in sheet data")

    except Exception as e:
        logger.error(f"Error marking order as processed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to mark order {raw_order_number} as processed",
        }


def create_update_cell_info(row: int, col: int, value: Any) -> Dict[str, Any]:
    """
    Create cell update information for external sheet API calls

    Args:
        row: Row number (1-based)
        col: Column number (1-based)
        value: Value to set

    Returns:
        Update information dictionary
    """
    return {
        "row": row,
        "column": col,
        "value": value,
        "range": f"R{row}C{col}",  # R1C1 notation
    }


def create_append_row_info(row_data: List[Any]) -> Dict[str, Any]:
    """
    Create append row information for external sheet API calls

    Args:
        row_data: Array of values to append

    Returns:
        Append information dictionary
    """
    return {
        "values": [row_data],
        "operation": "append",
        "message": f"Appending {len(row_data)} values to sheet",
    }


def validate_sheet_structure(
    sheet_data: List[List[Any]], required_columns: List[str]
) -> Dict[str, Any]:
    """
    Validate that a sheet has required columns

    Args:
        sheet_data: 2D array of sheet data
        required_columns: List of required column names

    Returns:
        Validation result
    """
    if not sheet_data:
        return {
            "valid": False,
            "error": "No sheet data provided",
            "missing_columns": required_columns,
        }

    processor = SheetDataProcessor(sheet_data)
    missing_columns = []

    for column in required_columns:
        if processor.get_column_index(column) == -1:
            missing_columns.append(column)

    return {
        "valid": len(missing_columns) == 0,
        "missing_columns": missing_columns,
        "found_headers": processor.headers,
        "message": "Sheet structure is valid"
        if len(missing_columns) == 0
        else f"Missing columns: {missing_columns}",
    }


def extract_column_data(
    sheet_data: List[List[Any]], column_name: str, skip_empty: bool = True
) -> List[Any]:
    """
    Extract all data from a specific column

    Args:
        sheet_data: 2D array of sheet data
        column_name: Column name to extract
        skip_empty: Whether to skip empty cells

    Returns:
        List of column values
    """
    if not sheet_data:
        return []

    processor = SheetDataProcessor(sheet_data)
    column_index = processor.get_column_index(column_name)

    if column_index == -1:
        return []

    column_data = []
    for row in processor.rows:
        if column_index < len(row):
            value = row[column_index]
            if not skip_empty or (value is not None and str(value).strip()):
                column_data.append(value)

    return column_data
