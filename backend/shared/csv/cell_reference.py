"""
Generate Excel-style cell references for error reporting and validation.

Combines column letters and row numbers to create references like "A5", "AA10", "ZZ100".
"""
from shared.csv.column_index_to_letter import column_index_to_letter


def cell_reference(row: int, col_idx: int) -> str:
    """
    Create Excel-style cell reference.
    
    Combines column letter and row number to create a cell reference
    like "A5", "B10", or "AA100".
    
    Examples:
        >>> cell_reference(5, 0)
        'A5'
        >>> cell_reference(10, 26)
        'AA10'
        >>> cell_reference(100, 701)
        'ZZ100'
    
    Args:
        row: Row number (1-based, as shown in spreadsheets)
        col_idx: Zero-based column index
    
    Returns:
        Excel-style cell reference (e.g., "A5", "AA10")
    """
    return f"{column_index_to_letter(col_idx)}{row}"

