"""
Column finding utilities for CSV processing.

Provides utilities to find columns by keyword matching in headers.
"""
from typing import List, Optional


def find_column(header_row: List[str], keywords: List[str]) -> Optional[int]:
    """
    Find column index matching any keyword in the header row.
    
    Performs case-insensitive substring matching against all keywords.
    Returns the index of the first matching column.
    
    Args:
        header_row: List of header cell values
        keywords: List of keywords to search for (case-insensitive)
        
    Returns:
        Zero-based column index if found, None otherwise
        
    Examples:
        >>> find_column(["Name", "Email", "Phone"], ["email", "e-mail"])
        1
        >>> find_column(["Position", "BARS Email"], ["bars email"])
        1
        >>> find_column(["Name", "Title"], ["email"])
        None
    """
    for idx, cell in enumerate(header_row):
        cell_lower = cell.strip().lower()
        for keyword in keywords:
            if keyword.lower() in cell_lower:
                return idx
    return None

