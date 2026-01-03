"""
Parse CSV text into a list of rows.

Generic utility for converting CSV strings into structured data.
"""
import csv
import io
from typing import List


def parse_csv_text(csv_text: str) -> List[List[str]]:
    """
    Parse CSV text into a list of rows.
    
    Args:
        csv_text: CSV content as a string
    
    Returns:
        List of rows, where each row is a list of cell values
    
    Examples:
        >>> csv_text = "Name,Email\\nJohn,john@example.com\\nJane,jane@example.com"
        >>> parse_csv_text(csv_text)
        [['Name', 'Email'], ['John', 'john@example.com'], ['Jane', 'jane@example.com']]
    """
    reader = csv.reader(io.StringIO(csv_text))
    return list(reader)

