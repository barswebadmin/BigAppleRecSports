"""Spreadsheet data transformation and parsing helpers.

Pure functions for working with spreadsheet data (list of rows). No I/O.
"""

from dataclasses import dataclass


@dataclass
class TabInfo:
    """Metadata for a sheet tab."""

    gid: int
    title: str
    row_count: int | None


def get_cell(row: list[str], index: int, default: str = "") -> str:
    """Safely get a cell value from a row, stripped.

    Args:
        row: List of cell values.
        index: Column index (0-based).
        default: Value to return if index out of bounds or cell empty.

    Returns:
        Stripped cell value or default.

    Example:
        >>> row = ["  Alice  ", "bob@example.com", ""]
        >>> get_cell(row, 0)
        'Alice'
        >>> get_cell(row, 2, "N/A")
        'N/A'
        >>> get_cell(row, 5, "missing")
        'missing'
    """
    if index < len(row) and row[index]:
        return row[index].strip()
    return default


def rows_to_dicts(
    rows: list[list[str]],
    headers: list[str] | None = None,
    skip_header: bool = True,
) -> list[dict[str, str]]:
    """Convert rows to list of dicts using headers as keys.

    Args:
        rows: List of rows (each row is a list of cell values).
        headers: Column names. If None, uses first row as headers.
        skip_header: If True and headers is None, skip the first row in output.

    Returns:
        List of dicts mapping header names to cell values.

    Example:
        >>> rows = [["Name", "Email"], ["Alice", "a@x.com"], ["Bob", "b@x.com"]]
        >>> rows_to_dicts(rows)
        [{'Name': 'Alice', 'Email': 'a@x.com'}, {'Name': 'Bob', 'Email': 'b@x.com'}]
    """
    if headers is None:
        if not rows:
            return []
        headers = rows[0]
        data_rows = rows[1:] if skip_header else rows
    else:
        data_rows = rows

    result = []
    for row in data_rows:
        record = {}
        for i, header in enumerate(headers):
            record[header] = get_cell(row, i)
        result.append(record)
    return result


def filter_blank_rows(
    rows: list[list[str]],
    required_columns: list[int] | None = None,
) -> list[list[str]]:
    """Filter out rows where all (or specified) columns are blank.

    Args:
        rows: List of rows.
        required_columns: Column indices that must have values. If None,
            filters rows where ALL columns are blank.

    Returns:
        Filtered list of rows.

    Example:
        >>> rows = [["A", "B"], ["", ""], ["C", ""]]
        >>> filter_blank_rows(rows)
        [['A', 'B'], ['C', '']]
        >>> filter_blank_rows(rows, required_columns=[0])
        [['A', 'B'], ['C', '']]
    """
    result = []
    for row in rows:
        if required_columns is not None:
            has_value = any(get_cell(row, i) for i in required_columns)
        else:
            has_value = any(cell.strip() for cell in row if cell)
        if has_value:
            result.append(row)
    return result


def parse_tabs_metadata(api_response: dict) -> list[TabInfo]:
    """Parse tab metadata from Sheets API spreadsheets.get response.

    Args:
        api_response: Response dict from spreadsheets().get() with
            fields="sheets(properties(sheetId,title,gridProperties(rowCount)))".

    Returns:
        List of TabInfo with gid, title, and row_count for each tab.

    Example:
        >>> resp = {"sheets": [{"properties": {"sheetId": 0, "title": "Sheet1",
        ...     "gridProperties": {"rowCount": 100}}}]}
        >>> tabs = parse_tabs_metadata(resp)
        >>> tabs[0].title
        'Sheet1'
    """
    tabs = []
    for sheet in api_response.get("sheets", []):
        props = sheet.get("properties", {})
        tabs.append(
            TabInfo(
                gid=props.get("sheetId", 0),
                title=props.get("title", ""),
                row_count=props.get("gridProperties", {}).get("rowCount"),
            )
        )
    return tabs
