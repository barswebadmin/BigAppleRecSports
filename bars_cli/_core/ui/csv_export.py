"""CSV export utilities for CLI commands."""

import csv
import html
from datetime import datetime
from typing import Any, Dict, List, Optional

import click


def get_console() -> Any:
    """Get Rich Console instance for output."""
    from rich.console import Console
    return Console()


def format_date_for_csv(dt_str: Optional[str]) -> str:
    """Format ISO datetime string to CSV date format (M/D/YYYY).
    
    Args:
        dt_str: ISO datetime string (e.g., "2025-01-15T10:30:00Z")
        
    Returns:
        Formatted date string (e.g., "1/15/2025") or empty string if invalid
    """
    if not dt_str:
        return ''
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return f"{dt.month}/{dt.day}/{dt.year}"
    except (ValueError, AttributeError):
        return dt_str if dt_str else ''


def get_custom_attribute_value(line_item: Dict[str, Any], key: str) -> str:
    """Get custom attribute value from line item by key.
    
    Handles HTML entity decoding for key matching.
    
    Args:
        line_item: Line item dictionary with customAttributes
        key: Attribute key to search for
        
    Returns:
        Attribute value or empty string if not found
    """
    attrs = line_item.get('customAttributes', [])
    if not attrs:
        return ''
    
    key_decoded = html.unescape(key)
    for attr in attrs:
        attr_key = attr.get('key', '')
        attr_key_decoded = html.unescape(attr_key)
        if attr_key_decoded == key_decoded:
            return attr.get('value', '')
    return ''


def write_csv_to_file(
    headers: List[str],
    rows: List[List[str]],
    file_path: str
) -> None:
    """Write CSV data to a file.
    
    Args:
        headers: List of column header names
        rows: List of row data (each row is a list of strings)
        file_path: Path to output file
    """
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def write_csv_to_stdout(
    headers: List[str],
    rows: List[List[str]]
) -> None:
    """Write CSV data to stdout.
    
    Args:
        headers: List of column header names
        rows: List of row data (each row is a list of strings)
    """
    writer = csv.writer(click.get_text_stream("stdout"))
    writer.writerow(headers)
    writer.writerows(rows)

