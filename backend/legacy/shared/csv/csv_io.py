"""CSV file I/O utilities (read and write operations).

Provides unified CSV reading and writing with Dict format as standard.
"""

import csv
import sys
from typing import Any, Dict, List, Optional, TextIO, Tuple, cast


def _open_csv_file(file_path: str, mode: str = 'r') -> TextIO:
    """
    Open CSV file with proper encoding and newline handling.
    
    Args:
        file_path: Path to CSV file
        mode: File mode ('r' for read, 'w' for write)
    
    Returns:
        File handle
    """
    if mode == 'w':
        return cast(TextIO, open(file_path, mode, newline='', encoding='utf-8'))
    else:
        return cast(TextIO, open(file_path, mode, encoding='utf-8'))


def read_csv_file(file_path: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Read CSV file and return headers and rows as dictionaries.
    
    Args:
        file_path: Path to CSV file
    
    Returns:
        Tuple of (headers, rows) where rows are Dict[str, str] keyed by original header names
    """
    with _open_csv_file(file_path, 'r') as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    
    return headers, rows


def write_csv_file(
    data: List[Dict[str, Any]],
    file_path: Optional[str] = None,
    output_stream: Optional[TextIO] = None
) -> None:
    """
    Write CSV data to file or stream (Dict-only format).
    
    Auto-detects fieldnames from dict keys. All dicts should have the same keys
    (missing keys will be written as empty strings).
    
    Args:
        data: List of dictionaries to write (each dict represents a row)
        file_path: Path to output file (if None and output_stream is None, writes to stdout)
        output_stream: Custom output stream (optional, for testing or custom streams)
    
    Examples:
        # To file
        write_csv_file([{'name': 'John', 'age': '30'}], file_path='output.csv')
        
        # To stdout
        write_csv_file([{'name': 'John', 'age': '30'}])
        
        # To custom stream
        with open('output.csv', 'w') as f:
            write_csv_file([{'name': 'John'}], output_stream=f)
    """
    if not data:
        return
    
    # Get all unique keys from all dicts
    fieldnames = set()
    for row in data:
        fieldnames.update(row.keys())
    
    fieldnames = sorted(fieldnames)
    
    # Determine output destination
    if output_stream:
        stream = output_stream
        should_close = False
    elif file_path:
        stream = _open_csv_file(file_path, 'w')
        should_close = True
    else:
        stream = sys.stdout
        should_close = False
    
    try:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    finally:
        if should_close:
            stream.close()
