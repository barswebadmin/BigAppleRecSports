"""
Convert zero-based column indices to Excel-style letter notation.

Examples:
    0 → 'A'
    25 → 'Z'
    26 → 'AA'
    701 → 'ZZ'
    702 → 'AAA'
"""


def column_index_to_letter(col_idx: int) -> str:
    """
    Convert 0-based column index to Excel-style letter.
    
    Handles single letters (A-Z), double letters (AA-ZZ), triple letters (AAA+).
    Uses Excel's column naming convention.
    
    Examples:
        >>> column_index_to_letter(0)
        'A'
        >>> column_index_to_letter(25)
        'Z'
        >>> column_index_to_letter(26)
        'AA'
        >>> column_index_to_letter(701)
        'ZZ'
        >>> column_index_to_letter(702)
        'AAA'
    
    Args:
        col_idx: Zero-based column index
    
    Returns:
        Excel-style column letter(s)
    """
    result = ""
    col_idx += 1
    while col_idx > 0:
        col_idx -= 1
        result = chr(col_idx % 26 + ord('A')) + result
        col_idx //= 26
    return result

